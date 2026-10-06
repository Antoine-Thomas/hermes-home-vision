---
name: ragas-local-evaluation
description: Use when scoring a local RAG with RAGAS.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [rag, ragas, evaluation, ollama, retrieval, metrics]
    category: mlops
prerequisites:
  commands: [python]
---

# RAGAS on a local RAG

## When to Use

- Measuring or re-measuring a local RAG (FAISS/BM25, HTTP search endpoint) with RAGAS metrics.
- A baseline number is needed before/after a retrieval or routing change, with a local Ollama judge.
- A RAGAS run fails with OutputParserException, TimeoutError, or null context_precision.

Procedure to score a local retrieval pipeline (hybrid FAISS+BM25 behind an HTTP search endpoint) with RAGAS
(faithfulness, answer_relevancy, context_precision, context_recall) and a local Ollama judge, without
touching the production stack.

## 1. Isolation (non-negotiable)

- Create a DEDICATED venv for the measurement (e.g. `data/rag/ragas_env`); never install ragas into the venv
  that serves the RAG. A measurement install pulls pandas/pyarrow/datasets/langchain and silently upgrades
  dependencies (see `python-dependency-guard` for the failure mode).
- Before any install in an existing venv, save the rollback reference:
  `python -m pip freeze > .freeze_avant_<date>.txt`.
- Back up the production venv (or at least the files you may touch) and verify the copy file for file.
- Query the RAG over HTTP only (`/search`, `/v1/embeddings`). Never reindex, restart or edit its files.

## 2. Install the right combination (ragas 0.4.3, verified)

```bash
<python3.11> -m venv data/rag/ragas_env
./ragas_env/Scripts/python.exe -m pip install ragas langchain-ollama langchain-huggingface
# ragas 0.4.3 does `from langchain_community.chat_models.vertexai import ChatVertexAI` at import time:
./ragas_env/Scripts/python.exe -m pip install "langchain-community<0.4" google-cloud-aiplatform
```

- `pip install ragas` alone installs langchain-community 0.4.x, which REMOVED `chat_models.vertexai` ->
  `ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'`. Pinning `<0.4` is not
  enough by itself: that module imports `google.cloud`, so `google-cloud-aiplatform` is required too.
- Older ragas (0.2.x, 0.3.x) import the same vertexai path: downgrading does not work around it.

## 3. Judge model: the JSON contract

RAGAS metrics parse strict JSON; small instruct models echo the prompt instead of answering:

- `llama3.2:3b` as judge -> `OutputParserException(Invalid json output: <the prompt>)`, several
  `TimeoutError()`, `context_precision` = None. Unusable.
- `qwen2.5:7b` (or larger) with `format="json"` on `ChatOllama` -> zero exceptions, all four metrics.
- Freeze the judge for the whole campaign: baseline and after-runs MUST use the same judge and the same answer
  generator, otherwise deltas are meaningless. Record the judge name inside the result JSON.
- Answer generation (the pipeline under test) is a separate LLM call: `temperature=0` plus a fixed `seed`
  for reproducibility.

## 4. RunConfig: never leave max_workers at its default

`ragas.RunConfig()` defaults to `max_workers=16`, `timeout=180`, which saturates a single local Ollama and
produces TimeoutError storms on long prompts. Use `max_workers=1` (or 2 on a big GPU), `timeout=600`,
`max_retries=2`, and pass it as `evaluate(..., run_config=RunConfig(...))`.

## 5. Embeddings without installing torch

`answer_relevancy` needs embeddings. Reuse the target RAG's OpenAI-compatible endpoint:

```python
from langchain_core.embeddings import Embeddings

class EmbeddingsRAG(Embeddings):
    def __init__(self, url, lot=16): self.url, self.lot = url.rstrip('/'), lot
    def _appel(self, textes):
        out = []
        for i in range(0, len(textes), self.lot):
            d = post(f"{self.url}/v1/embeddings", {"input": textes[i:i+self.lot]})
            out += [x["embedding"] for x in d["data"]]
        return out
    def embed_documents(self, textes): return self._appel(list(textes))
    def embed_query(self, texte): return self._appel([texte])[0]
```

Wrap it with `LangchainEmbeddingsWrapper` from `ragas.embeddings`: same model and same vector space as the
RAG, zero download.

## 6. Split the run in two stages

Separate collection (retrieval + answer generation) from scoring, and write the intermediate JSON:
`--etape collecte` then `--etape ragas`. A judge failure then never costs the retrieval work, and the same
collected answers can be re-scored by another judge.

## 7. Build the question set with verifiable ground truth

- 10 factual / 10 synthesis / 10 cross-cutting, each with: question, expected answer AND the source fragment
  (document title + part index).
- Validate that every cited source exists in the index (`chunks.jsonl`) BEFORE running: a source that does not
  exist turns the recall metric into a lie.
- Report the retrieval hit rate separately (gold document present in the injected fragments): that is the
  honest measure of a routing/retrieval change, independent of the LLM judge.

## 8. Interpret the numbers: the judge noise floor

Identical contexts and identical generated answers still score differently between runs (measured: -0.12 on
the 4-metric average for the same question) because the judge samples. Therefore:

- a single-digit aggregate delta is NOT evidence;
- compare per metric and per question type, and read the retrieval hit rate for a judge-independent signal;
- for any delta you intend to act on, restrict the analysis to questions whose contexts actually changed, and
  repeat the run before deciding.

## 9. Environment hygiene when launching the venv

When a venv python is launched from a Hermes `execute_code`/subprocess, the parent `PYTHONPATH` points at the
Hermes runtime venv and shadows the target venv's packages (wrong `fastapi`, wrong `numpy`, bogus
tracebacks). Strip it:
`env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}`,
or run through the `terminal` tool, which starts clean.
