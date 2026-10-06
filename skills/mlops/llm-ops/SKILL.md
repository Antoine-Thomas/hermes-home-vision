---
name: llm-ops
description: "Run/eval LLMs: GGUF, vLLM, lm-eval, OBLITERATUS."
version: 1.0.0
author: Hermes Agent (consolidated from llama-cpp, serving-llms-vllm, evaluating-llms-harness, obliteratus)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [llama.cpp, GGUF, vLLM, serving, lm-eval, benchmarking, abliteration, uncensoring, quantization, inference, evaluation]
    related_skills: [huggingface-hub, nvidia-nim]
---

# LLM Ops — Inference, Serving, Evaluation, Model Surgery

One umbrella for running, serving, benchmarking, and modifying open-weight LLMs.
Pick the tool for the job, then open the matching reference below.

## Tool selection

| Need | Tool | Reference |
|------|------|-----------|
| llama.cpp (local GGUF) | `llama-cpp` | references/llama-cpp-when-to-use.md |
| vLLM (production serving) | `serving-llms-vllm` | references/serving-llms-vllm-when-to-use.md |
| lm-eval-harness (benchmarks) | `evaluating-llms-harness` | references/evaluating-llms-harness-whats-inside.md |
| OBLITERATUS (abliteration) | `obliteratus` | references/obliteratus-whats-inside.md |

## References

### llama-cpp
# llama.cpp + GGUF
- [When to use](references/llama-cpp-when-to-use.md)
- [Model Discovery workflow](references/llama-cpp-model-discovery-workflow.md)
- [Quick start](references/llama-cpp-quick-start.md)
- [Python bindings (llama-cpp-python)](references/llama-cpp-python-bindings-llama-cpp-python.md)
- [Choosing a quant](references/llama-cpp-choosing-a-quant.md)
- [Extracting available GGUFs from a repo](references/llama-cpp-extracting-available-ggufs-from-a-repo.md)
- [Search patterns](references/llama-cpp-search-patterns.md)
- [Output format](references/llama-cpp-output-format.md)
- [References](references/llama-cpp-references.md)
- [Resources](references/llama-cpp-resources.md)

### serving-llms-vllm
# vLLM - High-Performance LLM Serving
- [When to use](references/serving-llms-vllm-when-to-use.md)
- [Quick start](references/serving-llms-vllm-quick-start.md)
- [Common workflows](references/serving-llms-vllm-common-workflows.md)
- [When to use vs alternatives](references/serving-llms-vllm-when-to-use-vs-alternatives.md)
- [Common issues](references/serving-llms-vllm-common-issues.md)
- [Advanced topics](references/serving-llms-vllm-advanced-topics.md)
- [Hardware requirements](references/serving-llms-vllm-hardware-requirements.md)
- [Resources](references/serving-llms-vllm-resources.md)

### evaluating-llms-harness
# lm-evaluation-harness - LLM Benchmarking
- [What's inside](references/evaluating-llms-harness-whats-inside.md)
- [Quick start](references/evaluating-llms-harness-quick-start.md)
- [Common workflows](references/evaluating-llms-harness-common-workflows.md)
- [When to use vs alternatives](references/evaluating-llms-harness-when-to-use-vs-alternatives.md)
- [Common issues](references/evaluating-llms-harness-common-issues.md)
- [Advanced topics](references/evaluating-llms-harness-advanced-topics.md)
- [Hardware requirements](references/evaluating-llms-harness-hardware-requirements.md)
- [Resources](references/evaluating-llms-harness-resources.md)

### obliteratus
# OBLITERATUS Skill
- [What's inside](references/obliteratus-whats-inside.md)
- [Video Guide](references/obliteratus-video-guide.md)
- [When to Use This Skill](references/obliteratus-when-to-use-this-skill.md)
- [Step 1: Installation](references/obliteratus-step-1-installation.md)
- [Step 2: Check Hardware](references/obliteratus-step-2-check-hardware.md)
- [Step 3: Browse Available Models & Get Recommendations](references/obliteratus-step-3-browse-available-models-get-recommenda.md)
- [Step 4: Choose a Method](references/obliteratus-step-4-choose-a-method.md)
- [Step 5: Run Abliteration](references/obliteratus-step-5-run-abliteration.md)
- [Step 6: Verify Results](references/obliteratus-step-6-verify-results.md)
- [Step 7: Use the Abliterated Model](references/obliteratus-step-7-use-the-abliterated-model.md)
- [CLI Command Reference](references/obliteratus-cli-command-reference.md)
- [Analysis Modules](references/obliteratus-analysis-modules.md)
- [Ablation Strategies](references/obliteratus-ablation-strategies.md)
- [Evaluation](references/obliteratus-evaluation.md)
- [Platform Support](references/obliteratus-platform-support.md)
- [YAML Config Templates](references/obliteratus-yaml-config-templates.md)
- [Telemetry](references/obliteratus-telemetry.md)
- [Common Pitfalls](references/obliteratus-common-pitfalls.md)
- [Complementary Skills](references/obliteratus-complementary-skills.md)

## Regle transversale — epingler transformers sur cette machine

**Sur ce poste, `transformers` doit etre epingle < 5 pour toute pile qui touche diffusers, peft,
LTX ou SDXL LoRA.** Ne jamais le laisser se mettre a jour tout seul.

Pourquoi : transformers 5.x fait tomber les imports de diffusers et de peft avec des messages
trompeurs (`name 'nn' is not defined` dans `diffusers.loaders.lora_pipeline`, puis
`cannot import name 'disable_input_dtype_casting' from 'peft.helpers'`). L'erreur designe peft,
alors que la cause est transformers.

Deux pannes payees, une seule cause : le noeud LTX-2.3 de ComfyUI (resolu en epinglant 4.57.6) et
l'installation SDXL LoRA (resolue de la meme facon).

Couple eprouve sur cette machine : `transformers==4.57.6` + `diffusers==0.36.0` + `peft>=0.17`
+ `accelerate>=1.4`. Copie-le tel quel plutot que de resoudre les versions une par une.

Piece jointe : les scripts d'exemple diffusers (`train_dreambooth_lora_sdxl.py`) refusent la
version publiee avec `This example requires a source install from HuggingFace diffusers` et un
`check_min_version("X.dev0")`. Non, il n'y a pas besoin d'installer depuis les sources : neutraliser
cette ligne suffit, le script tourne tres bien sur la version PyPI epinglee.

## Ollama — API de decision `/v1/systemone` (modeles a capacite `decision`)

Un modele dont le manifeste declare `CAPABILITY decision` (ex. `clef-flash`, base qwen3.5
post-entrainee) ne se sert NI sur `/api/generate` NI sur `/v1/chat/completions` : Ollama rend 400
`"<modele>" does not support generate`. La route est `POST /v1/systemone {model, state,
questions}` ; un `GET` sur la meme URL rend 405 (la route existe), et le code du POST tranche la
cause :

- **400 = forme de la requete** (repond en < 10 ms) : `type must be choice, noul, or score` (le type
  `boolean` est refuse), `questions must contain 1-64 fields`, `unknown noul criterion "<x>"` (les
  `criteria` d'un `noul` doivent etre des libelles connus, pas du texte libre).
- **500 = cote modele** (voir ci-dessous).

Reponse : `{model, answers:{<id>:{type, noul | choice+probabilities | score+legend}},
usage:{input_tokens, output_tokens}}`. `output_tokens` vaut **0** — c'est une tete de decision, il
n'y a aucune generation : le debit en tokens/s n'existe pas, la seule metrique utile est la latence
PAR DECISION (mesure sur un 9B : 1,3-1,5 s a chaud, 59,8 s au premier appel qui charge les poids).

**`500 "Clef: non-finite logit"` : comparer les OFFSETS des tenseurs de tete, pas la taille du
fichier.** Mesure : `clef-flash` (9,1B, 10,01 GB) echoue sur 100 % des requetes, `clef` (27B,
17,06 GB) repond juste — la difference n'est donc pas la taille. Le parseur GGUF montre que les 122
tenseurs `clef.*` (la tete de decision) sont a **9,53-10,01 GB dans clef-flash** (au-dela de 4 GiB)
mais a **0,01-0,52 GB dans clef** (sous 2 GiB) : un `seekg` tronque a 32 bits lit le mauvais octet
-> NaN -> logit non fini. Compter les tenseurs au-dela de 4 GiB ne discrimine rien (739/973 pour le
27B qui marche, 418/549 pour le 9B qui echoue) : c'est l'emplaCEMENT DU BLOC DE TETE qui decide.
Verification : lire l'en-tete du blob `model` du manifeste
(`~/.ollama/models/blobs/sha256-<digest>`, celui liste par `manifests/registry.ollama.ai/library/<m>/latest`).
La table des tenseurs suit les KV : pour chaque tenseur (nom, n_dims u32, dims u64 x n_dims, type
u32, offset u64) ; l'offset est relatif au debut des donnees, aligne sur `general.alignment`
(32 par defaut) — donc `offset absolu = data_start + offset`.

**Une sonde de decision FAIT tourner le modele : ce n'est jamais gratuit.** Un POST charge les poids
(`llama-server started in 30,6 s` mesure pour le 27B) et occupe la memoire jusqu'a `OLLAMA_KEEP_ALIVE`
(15 min mesures) : 7,6 Go / 8,2 Go de VRAM et 19,5 Go de WorkingSet pour `llama-server`. Sur 8 Go de
VRAM le 27B est scinde (`offloaded 16/65 layers`, `CUDA0 4405 MiB` + `CUDA_Host 11365 MiB` avec
`OLLAMA_GPU_LAYERS=35`), d'ou ~1,4 s par decision. Ne pas sonder un modele local juste avant un run
video/GPU : la memoire n'est rendue qu'a l'unload.

**Les messages d'Ollama ne disent pas si la ressource existe encore.** `ollama stop <m>` ->
`couldn't find model "<m>" to stop` et `ollama rm <m>` -> `model "<m>" not found` s'affichent aussi
quand le modele a DEJA ete decharge/supprime : ne pas conclure a un echec d'appel. L'etat reel se lit
sur `GET /api/ps` (vide) et `GET /api/tags` ; l'heure d'une suppression se lit dans le log serveur
(`%LOCALAPPDATA%\Ollama\server.log`) sur les lignes `[GIN] <date> | 200 | ... DELETE "/api/delete"`
— c'est ce qui a date la suppression de `clef`/`clef-flash` a 13:09:06-07, soit AVANT toute
commande de nettoyage.
