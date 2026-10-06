# -*- coding: utf-8 -*-
"""Tests hors-ligne du plugin auto-context-reset (aucun reseau, aucun GPU, aucune session vivante).

Couverture :
  T1  regles de detection d'un echec de compression (erreur / sortie vide / etouffement / fin anormale / cas sain)
  T2  detection d'une saturation dure (erreur de fenetre cote fournisseur)
  T3  fail-open : une exception interne ne casse jamais un tour
  T4  chaine complete : incidents -> journal JSONL + handoff markdown + avis injecte UNE seule fois
  T5  contenu du handoff et de l'avis (chemin, session, procedure, commande de reprise)

Usage :  <python> tests/test_hook.py     (sortie 0 = tout passe)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUG = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("auto_context_reset", os.path.join(PLUG, "__init__.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

PASS = 0
FAIL = 0


def check(nom, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK ] %s %s" % (nom, detail))
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (nom, detail))


class Ctx:
    """Ctx minimal : reglages fixes, journal et handoff dans un dossier temporaire."""

    def __init__(self, tmp, **over):
        self.tmp = tmp
        self.cfg = {"mode": "on", "seuil_echecs": 2, "duree_suspecte_s": 120.0,
                    "notify_every_s": 600.0, "dernieres_messages": 5, "message_chars": 120,
                    "ecrire_handoff": True,
                    "handoff_dir": os.path.join(tmp, "handoffs"),
                    "log_path": os.path.join(tmp, "auto-reset.log")}
        self.cfg.update(over)
        self.hooks = {}

    def get_config(self, cle, defaut=None):
        return self.cfg.get(cle, defaut)

    def set_config(self, cle, val):
        self.cfg[cle] = val

    def register_hook(self, nom, cb):
        self.hooks[nom] = cb
        return None

    def register_cli_command(self, *a, **k):
        return None


def test_t1_detection():
    print("T1 — regles de detection :")
    sain = {"aux_task": "compression", "error": None, "error_type": None,
            "api_duration": 12.0, "assistant_content_chars": 900, "finish_reason": "stop"}
    inc, _g, _d = A._est_echec_compression(sain, 120.0)
    check("appel sain -> pas d'incident", inc is False)

    err = dict(sain, error="Connection error", api_duration=0.4)
    inc, g, _d = A._est_echec_compression(err, 120.0)
    check("erreur provider -> incident", inc and g == "erreur", "genre=%s" % g)

    vide = dict(sain, assistant_content_chars=0, api_duration=1.0)
    inc, g, _d = A._est_echec_compression(vide, 120.0)
    check("sortie vide -> incident", inc and g == "sortie_vide", "genre=%s" % g)

    etouf = dict(sain, assistant_content_chars=0, api_duration=300.0)
    inc, g, _d = A._est_echec_compression(etouf, 120.0)
    check("300 s sans texte -> incident", inc and g in ("sortie_vide", "etouffement"), "genre=%s" % g)

    long_ok = dict(sain, assistant_content_chars=500, api_duration=180.0)
    inc, g, _d = A._est_echec_compression(long_ok, 120.0)
    check("180 s AVEC texte -> etouffement (depassement seuil)", inc and g == "etouffement", "genre=%s" % g)

    fin = dict(sain, finish_reason="length")
    inc, g, _d = A._est_echec_compression(fin, 120.0)
    check("finish_reason=length -> incident", inc and g == "fin_anormale", "genre=%s" % g)

    # Champs reels du payload Hermes (agent/auxiliary_hooks.py:140-176) : une reponse
    # en flux arrive NON consommee -> chars=0 + finish_reason=None sont normaux.
    flux = {"aux_task": "compression", "error": None, "error_type": None, "streaming": True,
            "assistant_content_chars": 0, "finish_reason": None, "api_duration": 900.0,
            "model": "deepseek-flash"}
    inc, g, _d = A._est_echec_compression(flux, 120.0)
    check("reponse en flux (chars=0 par conception) -> PAS d'incident", inc is False, "genre=%s" % g)
    err_flux = dict(flux, error="APIConnectionError: boom", error_type="APIConnectionError")
    inc, g, _d = A._est_echec_compression(err_flux, 120.0)
    check("flux EN ERREUR -> incident", inc and g == "erreur", "genre=%s" % g)


def test_t2_saturation_dure():
    print("T2 — saturation dure (fenetre depassee) :")
    inc, g, _d = A._est_saturation_dure({
        "status_code": 400, "error_type": "invalid_request_error",
        "error_message": "This model's maximum context length is 128000 tokens"})
    check("400 + 'maximum context length' -> incident", inc and g == "fenetre_depassee", "genre=%s" % g)

    inc, _g, _d = A._est_saturation_dure({"status_code": 429,
                                          "error_message": "rate limit exceeded, retry later"})
    check("429 rate limit -> pas un incident de saturation", inc is False)

    inc, _g, _d = A._est_saturation_dure({})
    check("payload vide -> pas d'incident", inc is False)


def test_t3_fail_open():
    print("T3 — fail-open :")

    class CtxCasse(Ctx):
        def get_config(self, cle, defaut=None):
            raise RuntimeError("config illisible")

    tmp = tempfile.mkdtemp(prefix="acr_t3_")
    try:
        a, b, c = A.make_hooks(CtxCasse(tmp))
        check("post_auxiliary_call ne leve pas", a(aux_task="compression",
                                                   session_id="s", api_duration=999) is None)
        check("api_request_error ne leve pas", b(error_message="maximum context length") is None)
        check("pre_llm_call ne leve pas", c(session_id="s", user_message="bonjour") is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t4_chaine_complete():
    print("T4 — chaine complete (seuil 2) :")
    tmp = tempfile.mkdtemp(prefix="acr_t4_")
    try:
        ctx = Ctx(tmp)
        post, err_h, pre = A.make_hooks(ctx)
        SID = "20261005_999999_test01"
        echec = {"aux_task": "compression", "session_id": SID, "error": None, "error_type": None,
                 "api_duration": 300.0, "assistant_content_chars": 0, "finish_reason": "stop",
                 "model": "deepseek-flash"}
        # 1er incident : sous le seuil -> journal seul, pas de handoff
        post(**echec)
        check("1er incident sous seuil -> pas de handoff",
              not os.path.isdir(ctx.cfg["handoff_dir"])
              or not os.listdir(ctx.cfg["handoff_dir"]))
        # appel sain : ignore
        post(**dict(echec, assistant_content_chars=1200, api_duration=8.0))
        # 2e incident : seuil atteint -> handoff + avis
        post(**echec)
        fichiers = (os.listdir(ctx.cfg["handoff_dir"])
                    if os.path.isdir(ctx.cfg["handoff_dir"]) else [])
        check("2e incident -> handoff ecrit", len(fichiers) == 1, "fichiers=%s" % fichiers)
        chemin = os.path.join(ctx.cfg["handoff_dir"], fichiers[0]) if fichiers else ""
        texte = open(chemin, encoding="utf-8").read() if chemin else ""
        check("handoff cite la session", SID in texte)
        check("handoff contient la section « Etat du travail »", "Etat du travail" in texte)
        check("handoff contient la commande de reprise", "hermes -c" in texte)

        lignes = [json.loads(l) for l in open(ctx.cfg["log_path"], encoding="utf-8") if l.strip()]
        check("journal : 2 incidents + 1 handoff",
              sum(1 for l in lignes if l.get("outcome") == "incident") == 2
              and sum(1 for l in lignes if l.get("outcome") == "handoff") == 1,
              "lignes=%s" % [l.get("outcome") for l in lignes])

        r1 = pre(session_id=SID, user_message="on continue ?")
        check("avis injecte au tour suivant", isinstance(r1, dict) and "context" in r1)
        check("avis nomme le plugin", "<auto_context_reset>" in (r1 or {}).get("context", ""))
        check("avis pointe le handoff", chemin in (r1 or {}).get("context", ""))
        check("avis cite le skill", "auto-context-reset" in (r1 or {}).get("context", ""))
        r2 = pre(session_id=SID, user_message="encore ?")
        check("avis injecte UNE seule fois", r2 is None)
        r3 = pre(session_id=SID, user_message="/new")
        check("commande slash -> aucune injection", r3 is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t5_mode_off():
    print("T5 — mode off :")
    tmp = tempfile.mkdtemp(prefix="acr_t5_")
    try:
        ctx = Ctx(tmp, mode="off", seuil_echecs=1)
        post, _e, pre = A.make_hooks(ctx)
        post(aux_task="compression", session_id="s1", api_duration=500.0,
             assistant_content_chars=0, finish_reason="stop")
        check("mode off -> aucun handoff",
              not os.path.isdir(ctx.cfg["handoff_dir"]) or not os.listdir(ctx.cfg["handoff_dir"]))
        check("mode off -> aucun avis", pre(session_id="s1", user_message="x") is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t6_normalisation_mode():
    print("T6 — normalisation du mode (YAML 1.1 ecrit on -> true) :")
    check("True -> on", A._norm_mode(True) == "on")
    check("False -> off", A._norm_mode(False) == "off")
    check("'on' -> on", A._norm_mode("on") == "on")
    check("'ON' -> on", A._norm_mode("ON") == "on")
    check("'' -> on (defaut actif)", A._norm_mode("") == "on")
    check("'off' -> off", A._norm_mode("off") == "off")
    tmp = tempfile.mkdtemp(prefix="acr_t6_")
    try:
        ctx = Ctx(tmp, mode=True, seuil_echecs=1)   # graphie ecrite par `hermes config set`
        post, _e, _p = A.make_hooks(ctx)
        post(aux_task="compression", session_id="s2", api_duration=300.0,
             assistant_content_chars=0, finish_reason="stop")
        ok = os.path.isdir(ctx.cfg["handoff_dir"]) and bool(os.listdir(ctx.cfg["handoff_dir"]))
        check("mode=True (YAML) -> surveillance ACTIVE", ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_t1_detection()
    test_t2_saturation_dure()
    test_t3_fail_open()
    test_t4_chaine_complete()
    test_t5_mode_off()
    test_t6_normalisation_mode()
    print("\n== %d PASS / %d FAIL ==" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
