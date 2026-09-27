"""Runtime Laya en ONNX pur (onnxruntime + tokenizers), sans PyTorch.

Replique laya/common.py::build_sequence et laya/agent.py::_decode_answers.

Usage :
    python laya_onnx.py --onnx-dir ./laya-onnx/english --self-test
    python laya_onnx.py --onnx-dir ./laya-onnx/english --state state.json --questions q.json

En bibliotheque :
    from laya_onnx import LayaOnnx
    laya = LayaOnnx("laya-onnx/english")
    r = laya.predict(state, {"refund": {"type": "noul",
                                        "instructions": "Does the customer request a refund?"}})
    print(r["answers"]["refund"]["noul"], r["latency_ms"])
"""
import argparse
import json
import os
import time

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

QTYPES = {"choice": 0, "score": 1, "noul": 2}
QTYPE_NAMES = {v: k for k, v in QTYPES.items()}
TEMP_MIN, TEMP_MAX = 0.5, 5.0


# --------------------------------------------------------------------------- #
# Tokenizer (tokenizers.Tokenizer nu, aucun transformers)
# --------------------------------------------------------------------------- #
class Tok:
    def __init__(self, tok_json, tok_cfg_json):
        self.t = Tokenizer.from_file(tok_json)
        cfg = json.load(open(tok_cfg_json, encoding="utf-8"))
        self.cls_token, self.sep_token = cfg["cls_token"], cfg["sep_token"]
        self.mask_token = cfg["mask_token"]
        self.pad_token = cfg.get("pad_token", cfg["mask_token"])
        self.cls_token_id = self.t.token_to_id(self.cls_token)
        self.sep_token_id = self.t.token_to_id(self.sep_token)
        self.mask_token_id = self.t.token_to_id(self.mask_token)
        self.pad_token_id = self.t.token_to_id(self.pad_token)

    def encode(self, text, max_length=None):
        # add_special_tokens=False : le post-processeur du tokenizer.json ne doit rien ajouter,
        # CLS/SEP sont poses a la main par build_sequence.
        ids = self.t.encode(text, add_special_tokens=False).ids
        return ids[:max_length] if max_length else ids

    def decode(self, ids):
        return self.t.decode(ids)


# --------------------------------------------------------------------------- #
# Prompt (copie fidele de laya/common.py)
# --------------------------------------------------------------------------- #
def serialize_state(state):
    return state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)


def render_criterion(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "), default=str)


def render_options(q):
    t, crit = q["t"], q.get("crit")
    if t == "choice":
        return [str(k) if v is None or v == "" else "%s: %s" % (k, render_criterion(v))
                for k, v in crit.items()]
    if t == "score":
        return ["level %d: %s" % (i, render_criterion(c)) for i, c in enumerate(crit)]
    crit = crit or {}
    labels = q.get("labels") or {"false": "false", "true": "true"}
    fc, tc = crit.get("false"), crit.get("true")
    return [
        labels["false"] + ": " + (render_criterion(fc) if fc not in (None, "")
                                   else "no, the statement does not hold"),
        labels["true"] + ": " + (render_criterion(tc) if tc not in (None, "")
                                  else "yes, the statement holds"),
    ]


def build_sequence(tok, state, q, max_len=512, head_max_len=192, truncate_left=False):
    """[CLS] <type> question: <ins> [SEP] [MASK] opt0 [MASK] opt1 ... [SEP] <state> [SEP]."""
    mask_tok = tok.mask_token
    opts = render_options(q)
    ins = str(q["ins"]).replace(mask_tok, " ")
    head_ids = tok.encode("%s question: %s" % (q["t"], ins))
    opt_ids = []
    for o in opts:
        opt_tokens = tok.encode(" " + o.replace(mask_tok, " "), max_length=48)
        opt_ids.append([tok.mask_token_id] + opt_tokens)
    opt_budget = head_max_len - sum(len(o) for o in opt_ids)
    if opt_budget < 16:
        per = max(4, (head_max_len - 16) // max(1, len(opt_ids)))
        opt_ids = [o[:per] for o in opt_ids]
        opt_budget = head_max_len - sum(len(o) for o in opt_ids)
    head_ids = head_ids[: max(8, opt_budget)]
    ids = [tok.cls_token_id] + head_ids + [tok.sep_token_id]
    markers = []
    for o in opt_ids:
        markers.append(len(ids))
        ids.extend(o)
    ids.append(tok.sep_token_id)
    room = max(0, max_len - len(ids) - 1)
    state_ids = tok.encode(serialize_state(state).replace(mask_tok, " "))
    st = state_ids[max(0, len(state_ids) - room):] if truncate_left else state_ids[:room]
    ids = ids + st + [tok.sep_token_id]
    return ids[:max_len], [m for m in markers if m < max_len]


def collate(seqs):
    """Meme role que laya/common.py::collate_items, en numpy."""
    n, L = len(seqs), max(len(it["ids"]) for it in seqs)
    kmax = max(len(it["markers"]) for it in seqs)
    ids = np.zeros((n, L), dtype=np.int64)
    att = np.zeros((n, L), dtype=np.int64)
    mpos = np.zeros((n, kmax), dtype=np.int64)
    mmask = np.zeros((n, kmax), dtype=bool)
    for i, it in enumerate(seqs):
        ids[i, : len(it["ids"])] = it["ids"]
        att[i, : len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = it["markers"]
        mmask[i, :k] = True
    return ids, att, mpos, mmask


# --------------------------------------------------------------------------- #
# Questions + post-traitement (copie fidele de laya/agent.py)
# --------------------------------------------------------------------------- #
def to_internal(qdef):
    t = qdef["type"]
    crit = qdef.get("criteria")
    if t == "choice" and isinstance(crit, list):
        crit = {c: None for c in crit}
    elif t == "noul" and isinstance(crit, dict):
        crit = {str(k).lower(): v for k, v in crit.items()}
    ins = qdef["instructions"]
    if not isinstance(ins, str):
        ins = json.dumps(ins, ensure_ascii=False)
    q = {"t": t, "ins": ins, "crit": crit}
    if "labels" in qdef:
        q["labels"] = qdef["labels"]
    return q


def temp_bucket(qtype, k):
    size = "2" if k <= 2 else "3-5" if k <= 5 else "6-10" if k <= 10 else "11+"
    return "%s:%s" % (QTYPE_NAMES[int(qtype)], size)


def clamp_temperature(t):
    try:
        t = float(t)
    except (TypeError, ValueError):
        return 1.0
    if t != t or t in (float("inf"), float("-inf")):
        return 1.0
    return min(TEMP_MAX, max(TEMP_MIN, t))


def softmax(z):
    z = np.asarray(z, dtype=np.float64) - np.max(z)
    e = np.exp(z)
    return e / e.sum()


def confidence_from_probs(p, k):
    if k < 2:
        return 1.0
    p = p[:k]
    ent = -(p * np.log(np.clip(p, 1e-12, 1.0))).sum()
    return float(np.clip(1.0 - ent / np.log(k), 0.0, 1.0))


# --------------------------------------------------------------------------- #
class LayaOnnx:
    """Laya sous ONNX Runtime. `model_dir` contient laya*.onnx + tokenizer*.json
    + rl_agent_config.json."""

    def __init__(self, model_dir, threads=None):
        self.dir = model_dir
        graph = next(f for f in sorted(os.listdir(model_dir)) if f.endswith(".onnx"))
        cfg = json.load(open(os.path.join(model_dir, "rl_agent_config.json"), encoding="utf-8"))
        self.cfg = cfg
        self.tok = Tok(os.path.join(model_dir, "tokenizer.json"),
                       os.path.join(model_dir, "tokenizer_config.json"))
        self.temperature = [clamp_temperature(t) for t in cfg["temperature"]]
        self.temperature_by_options = {k: clamp_temperature(v)
                                       for k, v in cfg.get("temperature_by_options", {}).items()}
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads:  # optimal 6-10 ; au-dela des threads logiques la latence s'effondre
            so.intra_op_num_threads = threads
            so.inter_op_num_threads = threads
        t0 = time.perf_counter()
        self.sess = ort.InferenceSession(os.path.join(model_dir, graph), sess_options=so,
                                         providers=["CPUExecutionProvider"])
        self.load_s = time.perf_counter() - t0
        self.graph = graph

    def predict(self, state, questions):
        """Retourne {answers, latency_ms, n_questions, seq_len} dans la forme du SDK Laya."""
        truncate_left = isinstance(state, list)
        seqs = []
        for qid, qdef in questions.items():
            q = to_internal(qdef)
            ids, markers = build_sequence(self.tok, state, q, self.cfg["max_len"],
                                          self.cfg["head_max_len"], truncate_left)
            seqs.append({"qid": qid, "ids": ids, "markers": markers,
                         "qtype": QTYPES[q["t"]], "q": q})
        if not seqs:
            return {"answers": {}, "latency_ms": 0.0, "n_questions": 0, "seq_len": 0}
        ids, att, mpos, mmask = collate(seqs)
        feed = {"input_ids": ids, "attention_mask": att, "marker_pos": mpos,
                "marker_mask": mmask,
                "qtype": np.array([s["qtype"] for s in seqs], dtype=np.int64)}
        t0 = time.perf_counter()
        logits, act = self.sess.run(None, feed)
        ms = (time.perf_counter() - t0) * 1000.0
        answers = {}
        for j, s in enumerate(seqs):
            k = len(s["markers"])
            qt = s["qtype"]
            t_scale = self.temperature_by_options.get(temp_bucket(qt, k), self.temperature[qt])
            p = softmax(logits[j][:k].astype(np.float64) / t_scale)
            q = s["q"]
            if q["t"] == "choice":
                keys = list(q["crit"].keys())
                answers[s["qid"]] = {
                    "type": "choice", "choice": keys[int(p.argmax())],
                    "probabilities": {kk: round(float(v), 4) for kk, v in zip(keys, p)},
                    "confidence": round(confidence_from_probs(p, k), 4),
                    "answer_confidence": round(float(np.max(p)), 4),
                    "temperature": t_scale}
            elif q["t"] == "score":
                answers[s["qid"]] = {
                    "type": "score", "score": round(float((np.arange(k) * p).sum()), 4),
                    "probabilities": {str(i): round(float(v), 4) for i, v in enumerate(p)},
                    "confidence": round(confidence_from_probs(p, k), 4),
                    "answer_confidence": round(float(np.max(p)), 4),
                    "temperature": t_scale}
            else:
                answers[s["qid"]] = {
                    "type": "noul", "noul": round(float(p[1]), 4),
                    "confidence": round(max(float(p[1]), 1.0 - float(p[1])), 4),
                    "answer_confidence": round(float(np.max(p)), 4),
                    "temperature": t_scale}
        return {"answers": answers, "latency_ms": ms, "n_questions": len(seqs),
                "seq_len": int(ids.shape[1])}


# --------------------------------------------------------------------------- #
SELF_TEST_STATE = {
    "from": "user@acme.com", "subject": "Duplicate charge on invoice #4411",
    "body": "Hi, we were billed twice for March. Please refund the duplicate today "
            "or we will cancel our plan.",
}
SELF_TEST_QUESTIONS = {
    "refund_requested": {"type": "noul", "instructions": "Does the customer request a refund?"},
    "churn_risk": {"type": "noul",
                   "instructions": "Does the customer threaten to cancel or leave?"},
    "department": {"type": "choice", "instructions": "Which department should handle this request?",
                   "criteria": {"billing": "invoices, payments, refunds",
                                "technical": "bugs, outages, system errors",
                                "sales": "pricing, new contracts",
                                "other": "everything else"}},
    "urgency": {"type": "score", "instructions": "How urgent is this request?",
                "criteria": ["not urgent", "soon", "critical deadline or blocking issue"]},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx-dir", required=True)
    ap.add_argument("--state", help="texte, ou chemin d'un .json")
    ap.add_argument("--questions", help="chemin d'un .json {id: {type, instructions, criteria}}")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    laya = LayaOnnx(a.onnx_dir, threads=a.threads)
    print("graph %s | chargement %.1f s" % (laya.graph, laya.load_s))
    if a.self_test or not a.state:
        state, questions = SELF_TEST_STATE, SELF_TEST_QUESTIONS
    else:
        state = a.state
        if os.path.isfile(state):
            state = json.load(open(state, encoding="utf-8"))
        questions = json.load(open(a.questions, encoding="utf-8"))
    laya.predict(state, questions)  # warmup
    r = min((laya.predict(state, questions) for _ in range(3)),
            key=lambda x: x["latency_ms"])
    for qid, ans in r["answers"].items():
        print("%-18s %s" % (qid, json.dumps(ans, ensure_ascii=False)))
    print("%d questions, L=%d -> %.0f ms (meilleur de 3)"
          % (r["n_questions"], r["seq_len"], r["latency_ms"]))


if __name__ == "__main__":
    main()
