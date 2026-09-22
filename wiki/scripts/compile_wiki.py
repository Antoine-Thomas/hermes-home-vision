"""Compilation one-shot du wiki L1 — non-agentique, UN SEUL appel LLM.

Pourquoi ce script existe : la compilation via un agent Hermes (`hermes -z`)
envoie ~16 K tokens de prompt systeme a CHAQUE tour (index des skills, schemas
d'outils, historique). Les paliers gratuits plafonnent en debit/minute : le run
meurt en boucle (`OmniRoute 504 requestQueue.maxWaitMs`, `429 cooling down`) ou
part dans le payant. Ici :

    1. Python lit SCHEMA.md + index.md + log.md + les sources de raw/
    2. UN SEUL appel HTTP au modele gratuit (burst unique, pas de boucle d'outils)
    3. Python ecrit les pages + met a jour index.md et log.md

Rien n'invente de contenu : le modele produit du JSON, le script ecrit les
fichiers. En cas d'echec, l'erreur brute du provider est affichee telle quelle.

Les routes gratuites saturent par FENETRES COURTES (mesure 2026-09-22 :
`gemini` 429 reset 56 s, NIM `Worker local total request limit reached`, OpenRouter
429 au niveau du COMPTE « pausing for 60s »). Un echec n'est donc pas terminal :
le script fait `--rounds` tours espaces de `--gap` secondes. Un tour n'appelle
qu'UNE fois chaque candidat, et le premier succes arrete tout : la contrainte
« un seul appel LLM » porte sur l'appel qui sert, pas sur les tentatives qui
n'ont rien produit (un 429 ne consomme pas de quota).

Usage :
    python compile_wiki.py                 # compile les sources non compilees
    python compile_wiki.py --dry-run       # affiche sans ecrire
    python compile_wiki.py --model eco     # impose le premier candidat
    python compile_wiki.py --rounds 6 --gap 90
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERMES = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
ENV_FILES = (HERMES / ".env", HERMES / "data" / "nvidia" / ".env")


def env_value(name: str) -> str:
    """Lit une cle dans l'environnement puis dans les .env connus (jamais affichee)."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    for env_file in ENV_FILES:
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if line.startswith(name + "="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    return ""


WIKI = Path(env_value("WIKI_PATH") or (HERMES / "wiki"))
TODAY = date.today().isoformat()
OMNIROUTE = "http://127.0.0.1:20128/v1/chat/completions"
NIM_DIRECT = "https://integrate.api.nvidia.com/v1/chat/completions"

# Candidats GRATUITS, essayes dans l'ordre. Dicts, pas tuples : chaque route a
# ses options (flux SSE, prefill) et une option de plus ne doit pas casser
# l'unpacking de la boucle.
#
# Ordre = du chemin le plus capacitaire au plus contraint, mesure le 2026-09-22 :
#  1-2. NIM en AMONT DIRECT (cle du poste) : ni le plafond local d'OmniRoute
#       (`requestQueue.maxWaitMs=15000` -> 504 des que la generation depasse 15 s)
#       ni le timeout 120 s du proxy local. Mesure : 16 a 35 tok/s, donc une
#       compilation de 5 000 tokens sort en 2-5 min. Seule route qui tienne un
#       prompt de ~12 K tokens avec une sortie longue.
#       `prefill` ouvre l'objet JSON cote assistant : sans lui, un modele de
#       raisonnement derive et noie le JSON dans 120 K car. de raisonnement.
#  3. free-openrouter : modeles `:free` d'OpenRouter, quota distinct du poste,
#       contexte 256 K a 1 M. 429 de COMPTE quand le palier gratuit du jour est
#       consomme (mesure : 429 persistant sur 15:57-17:05Z).
#  4. eco             : gemini-3-flash-preview + 2 cibles NIM (1 M ctx).
#  5. nvidia-stack    : repli NIM via OmniRoute.
#  6. gemini direct   : pool gemini hors combo (1 compte : cooldown d'1 min).
CANDIDATES = [
    # super-120b en tete : seul candidat qui a rendu du francais correct sans
    # alerte de langue, et rapide (~35 s). nano-omni produit plus de pages mais
    # les a rendues en ANGLAIS et derive en raisonnement libre.
    {"label": "NIM direct super-120b", "endpoint": NIM_DIRECT,
     "model": "nvidia/nemotron-3-super-120b-a12b",
     "key": "NVIDIA_API_KEY_GEMMA4", "stream": True, "prefill": "{"},
    {"label": "NIM direct nano-omni", "endpoint": NIM_DIRECT,
     "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
     "key": "NVIDIA_API_KEY_GEMMA4", "stream": True, "prefill": "{"},
    {"label": "free-openrouter", "endpoint": OMNIROUTE, "model": "free-openrouter",
     "key": "OMNIROUTE_API_KEY", "stream": False, "prefill": ""},
    {"label": "eco", "endpoint": OMNIROUTE, "model": "eco",
     "key": "OMNIROUTE_API_KEY", "stream": False, "prefill": ""},
    {"label": "nvidia-stack", "endpoint": OMNIROUTE, "model": "nvidia-stack",
     "key": "OMNIROUTE_API_KEY", "stream": False, "prefill": ""},
    {"label": "gemini direct", "endpoint": OMNIROUTE,
     "model": "gemini/gemini-3-flash-preview",
     "key": "OMNIROUTE_API_KEY", "stream": False, "prefill": ""},
    # Dernier recours : ce 30B non-raisonnement a rendu un gabarit tronque a
    # chaque essai (jamais de JSON exploitable). Garde en bout de chaine pour ne
    # pas consommer 6 min avant que les routes fiables soient tentees.
    {"label": "NIM direct lightning", "endpoint": NIM_DIRECT,
     "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
     "key": "NVIDIA_API_KEY_GEMMA4", "stream": True, "prefill": "{"},
]

SECTION_OF_TYPE = {
    "entity": "Entities",
    "concept": "Concepts",
    "comparison": "Comparisons",
    "query": "Queries",
    "summary": "Syntheses",
}
SECTIONS = list(SECTION_OF_TYPE.values())
SECTIONS_OF_PAGES = ("concepts", "entities", "comparisons", "queries", "syntheses")

# Un modele faible recopie parfois le GABARIT du prompt au lieu de compiler. Ces
# marqueurs viennent de l'exemple de `build_prompt` : les rejeter evite de creer
# une page `nom-en-kebab-case.md` vide de sens dans le wiki.
PLACEHOLDER_SLUGS = {"nom-du-concept", "nom-en-kebab-case", "slug", "xxx", "titre-de-la-page", "a-remplacer"}
PLACEHOLDER_TEXT = "premier etage gratuit de la chaine de repli"
PLACEHOLDER_COMMENT = re.compile(r"^<!--\s*ordre\s+alphab[ée]tique\s*-->$", re.I)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def taxonomy(schema: str) -> set:
    """Tags autorises : tous les `backticks` de la section taxonomie du SCHEMA."""
    m = re.search(r"^## Taxonomie des tags(.*?)^## ", schema, re.S | re.M)
    if not m:
        return set()
    return set(re.findall(r"`([a-z0-9][a-z0-9._-]*)`", m.group(1)))


def cited_sources() -> set:
    """Fichiers de raw/ deja cites dans le frontmatter `sources:` d'une page."""
    cited = set()
    for d in SECTIONS_OF_PAGES:
        for f in (WIKI / d).rglob("*.md"):
            for line in read(f).splitlines()[:25]:
                if line.startswith("sources:"):
                    cited.update(re.findall(r"raw/[\w./-]+\.md", line))
    return cited


def collect_sources(only_cited: bool = False) -> list:
    cited = cited_sources() if not only_cited else set()
    out = []
    for f in sorted((WIKI / "raw").rglob("*.md")):
        rel = f.relative_to(WIKI).as_posix()
        if rel in cited:
            continue
        out.append((rel, read(f)))
    return out


def build_prompt(schema: str, index: str, log_tail: str, sources: list) -> str:
    src = "\n\n".join("=== %s ===\n%s" % (rel, txt) for rel, txt in sources)
    return f"""Tu compiles un wiki EN FRANCAIS (motif Karpathy) a partir de sources brutes.
Reponds UNIQUEMENT par un objet JSON, sans texte avant ni apres, sans ```.
La langue de sortie est le FRANCAIS : `title`, `summary` et `body` sont rediges
en francais. Les sources sont des notes francaises — ne traduis RIEN en anglais,
pas meme un titre.

=== SCHEMA.md (conventions a respecter) ===
{schema}

=== index.md (pages existantes) ===
{index}

=== log.md (20 dernieres lignes) ===
{log_tail}

=== SOURCES A COMPILER ({len(sources)}) ===
{src}

Format de sortie EXACT (exemple en francais — c'est la langue attendue) :
{{
  "pages": [
    {{
      "path": "concepts/nom-du-concept.md",
      "summary": "Resume d'une ligne, en francais, pour index.md.",
      "frontmatter": {{
        "title": "Nom du concept",
        "created": "{TODAY}",
        "updated": "{TODAY}",
        "type": "concept",
        "tags": ["hermes"],
        "sources": ["raw/notes/xxx.md"],
        "confidence": "high"
      }},
      "body": "# Nom du concept\\n\\nLe combo `eco` est le premier etage gratuit de la chaine de repli ; il est servi par Gemini puis par le proxy NIM local. Voir [[fallback-chain]] et [[omniroute]]."
    }}
  ]
}}

Regles :
- REDIGE EN FRANCAIS : titres, resumes et corps. Une page anglaise est un
  defaut, meme si le nom du modele ou de l'outil est anglais.
- 6 a 10 pages MAXIMUM, une page par concept/entite qui apparait dans 2+ sources
  ou qui est central a une seule source. Ne pas creer de page pour une mention de passage.
- Un lot de 5 sources riches en donne 8 a 10 : viser 6 pages au MINIMUM. Les
  pages listees dans index.md existent deja : les completer ou les citer au lieu
  de les recreer, et creer les pages manquantes qu'elles referencent.
- `type` : entity, concept, comparison, query ou summary. `path` : concepts/,
  entities/, comparisons/, queries/ ou syntheses/ selon le type.
- Chaque page : au moins 2 liens [[wikilinks]] vers d'autres pages du wiki.
- Un [[lien]] est le SLUG KEBAB-CASE EXACT de la page visee, sans espace ni
  accent, tel que `concepts/eco.md` -> `[[eco]]` (jamais `[[Eco]]` ni
  `[[fallback chain]]` pour `concepts/fallback-chain.md`). Un lien vers une page
  inexistante est un lien mort : n'en emets que vers les pages listees dans
  index.md ou vers celles que tu crees dans ce lot.
- `tags` : uniquement des tags presents dans la taxonomie du SCHEMA.md.
- `sources` : chemins reels des fichiers de raw/ utilises, en relatif au wiki.
- Synthetise, ne recopie pas la source. Pas de frontmatter dans `body`.
"""


def call_llm(label: str, endpoint: str, model: str, key_name: str, prompt: str,
             timeout: int, max_tokens: int, stream: bool = False, prefill: str = "") -> dict:
    """UN appel HTTP. En `stream=True`, la reponse SSE est reassemblee en clair.

    Le streaming n'est pas un confort : la passerelle NVIDIA renvoie `504` (corps
    vide) sur une generation longue en mode bloque, alors que le meme travail
    passe en flux (les octets arrivent en continu, plus de coupure a l'echeance).

    `prefill` amorce le tour de l'assistant (`{`) et est recolle a la reponse :
    sur un modele de raisonnement, c'est ce qui garantit que la sortie commence
    par le JSON au lieu de deriver en raisonnement libre.
    """
    key = env_value(key_name)
    if not key:
        raise RuntimeError("%s : cle %s absente" % (label, key_name))
    messages = [{"role": "user", "content": prompt}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    if stream:
        payload["stream"] = True
    body = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if stream:
        headers["Accept"] = "text/event-stream"
    req = urllib.request.Request(endpoint, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8")) if not stream else _read_sse(resp, model)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400].strip()
        raise RuntimeError("%s HTTP %s:%s" % (label, exc.code, " " + detail if detail else " (corps vide)")) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("%s injoignable: %s" % (label, exc.reason)) from None
    if prefill:
        try:
            cur = out["choices"][0]["message"].get("content") or ""
            # Le modele re-emet parfois sa propre accolade malgre le prefill :
            # ne pas coller `{{` (JSON invalide).
            out["choices"][0]["message"]["content"] = cur if cur.lstrip().startswith(prefill) else prefill + cur
        except (KeyError, IndexError, TypeError):
            pass
    return out


def _read_sse(resp, fallback_model: str) -> dict:
    """Assemble un flux SSE OpenAI-compatible en une reponse unique.

    Un flux peut aussi porter une ERREUR dans un chunk (`{"error": {...}}`) avec
    un statut HTTP 200 : la remonter telle quelle, sinon l'echec se lit
    « reponse vide » et la cause reelle est perdue.
    """
    parts, reasoning, finish, usage, seen, errors = [], [], None, {}, fallback_model, []
    for raw in resp:
        line = raw.decode("utf-8", "replace").strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            break
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue
        if chunk.get("error"):
            err = chunk["error"]
            errors.append(err if isinstance(err, str) else json.dumps(err, ensure_ascii=False)[:300])
            continue
        seen = chunk.get("model") or seen
        if chunk.get("usage"):
            usage = chunk["usage"]
        for ch in chunk.get("choices") or []:
            delta = ch.get("delta") or {}
            if delta.get("content"):
                parts.append(delta["content"])
            if delta.get("reasoning_content"):
                reasoning.append(delta["reasoning_content"])
            if ch.get("finish_reason"):
                finish = ch["finish_reason"]
    if errors and not parts:
        raise RuntimeError("erreur dans le flux SSE : %s" % " | ".join(errors[:3]))
    if usage:
        usage = dict(usage)
        usage.setdefault("streamed_chars", len("".join(parts)))
    else:
        usage = {"streamed_chars": len("".join(parts)), "reasoning_chars": len("".join(reasoning))}
    msg = {"content": "".join(parts), "reasoning_content": "".join(reasoning)}
    return {"model": seen, "usage": usage,
            "choices": [{"message": msg, "finish_reason": finish}]}


def extract_json(content: str) -> dict:
    """Tolere les ```json, le texte avant/apres, les virgules finales et les
    caracteres de controle bruts (retours a la ligne non echappes dans les
    chaines) : cas courant des sorties LLM, rejete par `strict=True`."""
    c = content.strip()
    if c.startswith("```"):
        c = re.sub(r"^```[a-zA-Z]*\s*", "", c)
        c = re.sub(r"```\s*$", "", c).strip()
    try:
        return json.loads(c, strict=False)
    except json.JSONDecodeError:
        pass
    start, end = c.find("{"), c.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("aucun objet JSON dans la reponse (%d car.) : %s" % (len(c), c[:200]))
    frag = c[start:end + 1]
    try:
        return json.loads(frag, strict=False)
    except json.JSONDecodeError:
        fixed = re.sub(r",(\s*[}\]]])", r"\1", frag)
        return json.loads(fixed, strict=False)


def salvage_pages(content: str) -> list:
    """Recupere les objets de page COMPLETS d'un tableau `pages` tronque.

    Une reponse coupee par `finish_reason=length` n'est pas reparable par
    `json.loads` : on rescanne le tableau en suivant la profondeur des accolades
    (les accolades dans les chaines JSON sont ignores) et on garde les pages
    parseables une par une.
    """
    out = []
    i = content.find('"pages"')
    if i == -1:
        return out
    depth, start, instr, esc = 0, None, False, False
    for j in range(i, len(content)):
        ch = content[j]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = j
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    out.append(json.loads(content[start:j + 1], strict=False))
                except json.JSONDecodeError:
                    pass
                start = None
            if depth < 0:
                depth = 0
    return out


def parse_pages(content: str) -> tuple:
    """Retourne (pages, note). Tente le JSON strict, puis sauve les pages entieres."""
    try:
        return (extract_json(content).get("pages") or []), ""
    except Exception as exc:
        pages = salvage_pages(content)
        if not pages:
            raise
        return pages, ("reponse tronquee/invalide : %d page(s) complete(s) recuperee(s) (%s)"
                       % (len(pages), exc))


def yaml_val(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(yaml_val(x) for x in v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    return s if re.fullmatch(r"[\w./@+-]+", s) else json.dumps(s, ensure_ascii=False)


FR_HINTS = re.compile(r"\b(le|la|les|des|une?|est|sont|pour|avec|dans|sur|par|pas|plus|qui|que|au|aux|du|ce|cette|ces|etre|selon|entre|ainsi|mais|donc|car)\b", re.I)
EN_HINTS = re.compile(r"\b(the|and|with|for|from|that|this|which|are|is|was|were|of|to|in|on|by|as|it|its|when|while|but|not)\b", re.I)


def looks_english(text: str) -> bool:
    """Heuristique de langue : plus de mots-outils anglais que francais.

    Sert a alerter sur une regle « redige en francais » non respectee par le
    modele gratuit, sans bloquer l'ecriture (l'operateur arbitre).
    """
    return len(EN_HINTS.findall(text)) > len(FR_HINTS.findall(text))


def write_pages(pages: list, allowed_tags: set, dry: bool) -> tuple:
    written, warned = [], []
    # Slugs connus = pages deja sur disque + celles prevues dans ce lot : sert a
    # detecter les liens morts au moment de l'ecriture, pas dans un lint ulterieur.
    planned = {Path(str(p.get("path", "")).replace("\\", "/")).stem
               for p in pages if isinstance(p, dict)}
    known = {f.stem for d in SECTIONS_OF_PAGES for f in (WIKI / d).rglob("*.md")} | planned
    for p in pages:
        if not isinstance(p, dict):
            warned.append("entree ignoree (pas un objet JSON) : %r" % (p,))
            continue
        if Path(str(p.get("path", "")).replace("\\", "/")).stem in PLACEHOLDER_SLUGS \
                or PLACEHOLDER_TEXT in str(p.get("body") or ""):
            warned.append("page refusee (echo du gabarit du prompt) : %r" % (p.get("path"),))
            continue
        rel = str(p.get("path", "")).replace("\\", "/").lstrip("/")
        target = (WIKI / rel).resolve()
        if not str(target).startswith(str(WIKI.resolve())) or target.suffix != ".md":
            warned.append("chemin refuse (hors wiki ou non .md) : %r" % rel)
            continue
        fm = dict(p.get("frontmatter") or {})
        # Type : celui du modele s'il est valide, sinon deduit du dossier de destination.
        ptype = str(fm.get("type") or "").strip().lower()
        if ptype not in SECTION_OF_TYPE:
            ptype = next((t for t, s in SECTION_OF_TYPE.items()
                          if s.lower() == target.parent.name.lower()), "concept")
        # Coherence chemin <-> type : le dossier nomme la section, index.md s'y fie.
        want_dir = SECTION_OF_TYPE[ptype].lower()
        if target.parent.name.lower() != want_dir:
            warned.append("chemin recale sur le type : %s -> %s/%s" % (rel, want_dir, target.name))
            rel = want_dir + "/" + target.name
            target = WIKI / rel
        fm["type"] = ptype
        # Champs obligatoires, completes si le modele les a oublies.
        fm.setdefault("title", target.stem.replace("-", " ").capitalize())
        fm.setdefault("created", TODAY)
        fm["updated"] = TODAY
        tags = [t for t in (fm.get("tags") or []) if t]
        if allowed_tags:
            kept = [t for t in tags if t in allowed_tags]
            for t in tags:
                if t not in allowed_tags:
                    warned.append("tag hors taxonomie retire : %s" % t)
            tags = kept
        fm["tags"] = tags
        fm.setdefault("sources", [])
        order = ["title", "created", "updated", "type", "tags", "sources", "confidence", "contested", "contradictions"]
        keys = [k for k in order if k in fm] + [k for k in fm if k not in order]
        body = str(p.get("body") or "").strip()
        if body.startswith("---"):
            body = re.sub(r"^---.*?---\s*", "", body, flags=re.S)
        links = len(re.findall(r"\[\[[^\]]+\]\]", body))
        if links < 2:
            warned.append("%s : %d lien(s) [[wikilink]] (minimum 2)" % (rel, links))
        for link in sorted(set(re.findall(r"\[\[([^\]]+)\]\]", body))):
            slug = link.split("|")[0].strip()
            if slug and slug not in known:
                warned.append("%s : lien mort [[%s]] (aucune page de ce slug)" % (rel, link))
        if looks_english(body):
            warned.append("%s : page apparemment en ANGLAIS (regle de langue non respectee)" % rel)
        text = "---\n" + "\n".join("%s: %s" % (k, yaml_val(fm[k])) for k in keys) + "\n---\n\n" + body + "\n"
        if not dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        written.append((rel, fm, str(p.get("summary") or "").strip()))
    return written, warned


def first_sentence(path: Path, limit: int = 150) -> str:
    """Premiere phrase du corps d'une page, pour un resume d'index.

    Repli lorsqu'une page n'a pas de `summary` (modele qui omet le champ) : un
    index qui affiche `- [[eco]] — eco` n'informe pas.
    """
    try:
        txt = read(path)
    except OSError:
        return ""
    body = txt.split("---", 2)[2] if txt.startswith("---") else txt
    para = []
    for line in body.splitlines():
        if not line.strip():
            if para:
                break  # fin du premier paragraphe
            continue
        if line.lstrip().startswith("#"):
            continue  # un titre n'est pas un resume
        para.append(line.strip())
    if not para:
        return ""
    # Un paragraphe peut etre coupe sur plusieurs lignes : joindre avant de
    # decouper la premiere phrase, sinon le resume s'arrete en milieu de phrase.
    flat = " ".join(para)
    flat = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", flat)
    flat = re.sub(r"[*`_]", "", flat).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", flat)
    s = (m.group(1) if m else flat).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def update_index(written: list, dry: bool) -> str:
    """Reconstruit le catalogue.

    Les entrees viennent de TOUTES les pages du wiki, pas du seul lot courant :
    avec un lot partiel, une page non retouchee ne doit pas disparaitre de
    l'index. Les pages du lot prennent leur nouveau resume ; les autres gardent
    la ligne deja ecrite (a defaut : le titre du frontmatter).
    """
    index = read(WIKI / "index.md")
    existing = {}
    for line in index.splitlines():
        m = re.match(r"^- \[\[([^\]]+)\]\]", line)
        if m:
            existing[m.group(1).strip()] = line.rstrip()
    on_disk = {f.relative_to(WIKI).as_posix() for d in SECTIONS_OF_PAGES for f in (WIKI / d).rglob("*.md")}
    planned = {rel for rel, _fm, _s in written}
    batch = {rel: (fm, summary) for rel, fm, summary in written}
    entries = {s: [] for s in SECTIONS}
    for rel in sorted(on_disk | planned, key=str.lower):
        slug = Path(rel).stem
        section = next((s for s in SECTIONS if s.lower() == Path(rel).parent.name.lower()), "Concepts")
        fm, summary = batch.get(rel, ({}, ""))
        if summary:
            line = "- [[%s]] — %s" % (slug, summary)
        else:
            old = existing.get(slug) or ""
            label = re.sub(r"^- \[\[[^\]]+\]\]\s*(—|-)?\s*", "", old).strip()
            # Un libelle vide ou qui ne fait que repeter le slug / le titre
            # n'informe pas : reprendre la premiere phrase du corps.
            if not label or label.lower() in (slug.lower(), str(fm.get("title") or "").lower()):
                label = first_sentence(WIKI / rel) or fm.get("title") or slug
            line = "- [[%s]] — %s" % (slug, label)
        entries[section].append(line)
    lines = index.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        if line.startswith("## ") and line[3:].strip() in entries:
            section = line[3:].strip()
            # Les commentaires de section sont conserves SANS doublon : sans ce
            # garde-fou, chaque passage empile un `<!-- ordre alphabetique -->`.
            comments = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("<!--") or lines[i].startswith("- [[")):
                if lines[i].startswith("<!--") and lines[i].strip() not in comments:
                    comments.append(lines[i].strip())
                i += 1
            new = sorted(entries[section], key=str.lower)
            # Un placeholder « ordre alphabetique » n'a de sens que sur une
            # section vide ; les notes locales (« Ajout local : ... ») sont
            # toujours conservees.
            notes = [c for c in comments if not PLACEHOLDER_COMMENT.match(c)]
            holes = [c for c in comments if PLACEHOLDER_COMMENT.match(c)]
            out.extend(notes)
            if new:
                out.extend(new)
            else:
                out.extend(holes[:1] or ["<!-- ordre alphabetique -->"])
    total = len(on_disk | planned)
    text = "\n".join(out) + "\n"
    text = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", "Last updated: " + TODAY, text)
    text = re.sub(r"Total pages: \d+", "Total pages: %d" % total, text)
    if not dry:
        (WIKI / "index.md").write_text(text, encoding="utf-8")
    return text


def append_log(written: list, served: str, dry: bool) -> None:
    entry = "\n## [%s] ingest | compilation one-shot (%d pages)\n\n" % (TODAY, len(written))
    entry += "- Serveur : %s\n" % (served or "?")
    entry += "\n".join("- %s" % rel for rel, _fm, _s in written) + "\n"
    if not dry:
        with open(WIKI / "log.md", "a", encoding="utf-8") as fh:
            fh.write(entry)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", help="impose le modele du premier candidat (ex. eco)")
    ap.add_argument("--all", action="store_true", help="recompile aussi les sources deja citees")
    ap.add_argument("--rounds", type=int, default=4, help="tours de tentative (defaut 4)")
    ap.add_argument("--gap", type=int, default=75, help="secondes entre deux tours (defaut 75)")
    ap.add_argument("--max-tokens", type=int, default=16000,
                    help="budget de sortie (defaut 16000 ; les modeles de raisonnement consomment ce budget avant d'ecrire le JSON)")
    ap.add_argument("--save-raw", help="ecrit la reponse brute du modele dans ce fichier (post-mortem)")
    ap.add_argument("--timeout", type=int, default=600, help="timeout HTTP par candidat (defaut 600 s)")
    args = ap.parse_args(argv)

    if not (WIKI / "SCHEMA.md").is_file():
        print("ERREUR : wiki introuvable (%s)" % WIKI, file=sys.stderr)
        return 2

    sources = collect_sources(only_cited=args.all)
    if not sources:
        print("Rien a compiler : toutes les sources de raw/ sont deja citees par une page.")
        return 0
    print("Wiki       : %s" % WIKI)
    print("Sources    : %d non compilee(s), %d car."
          % (len(sources), sum(len(t) for _r, t in sources)))

    schema = read(WIKI / "SCHEMA.md")
    prompt = build_prompt(schema, read(WIKI / "index.md"),
                          "\n".join(read(WIKI / "log.md").splitlines()[-20:]), sources)
    print("Prompt     : %d car. (~%d tokens, 1 seul appel)" % (len(prompt), len(prompt) // 4))

    candidates = list(CANDIDATES)
    if args.model:
        candidates.sort(key=lambda c: c["model"] != args.model)

    result, served, last_err, note = None, None, None, ""
    for rnd in range(1, max(1, args.rounds) + 1):
        if rnd > 1:
            print("\n--- tour %d/%d : attente %d s (quotas gratuits en fenetre courte) ---"
                  % (rnd, args.rounds, args.gap))
            time.sleep(args.gap)
        for cand in candidates:
            label, key_name = cand["label"], cand["key"]
            if not env_value(key_name):
                print("-> %s : ignore (cle %s absente)" % (label, key_name))
                continue
            print("-> %s (%s)%s%s…" % (label, cand["model"], " [flux]" if cand["stream"] else "",
                                       " [prefill]" if cand["prefill"] else ""))
            started = time.time()
            try:
                out = call_llm(label, cand["endpoint"], cand["model"], key_name, prompt,
                               args.timeout, args.max_tokens, cand["stream"], cand["prefill"])
                choice = (out.get("choices") or [{}])[0]
                msg = choice.get("message", {}) or {}
                content = msg.get("content") or ""
                if not content.strip():
                    # Un modele de raisonnement peut avoir tout brule en
                    # `reasoning_content` : le dire, au lieu de conclure "vide".
                    r = (msg.get("reasoning_content") or "").strip()
                    raise ValueError("reponse vide" + (" (raisonnement seul : %d car. de reasoning_content)" % len(r) if r else ""))
                if not result:
                    if args.save_raw:
                        Path(args.save_raw).write_text(content, encoding="utf-8")
                    try:
                        pages, note = parse_pages(content)
                    except Exception as pexc:
                        raise ValueError("sortie inexploitable (%s) | debut : %r"
                                         % (pexc, content[:200])) from None
                    if not pages:
                        raise ValueError("JSON valide mais aucune page (cle 'pages' vide)")
                    result = pages
                served = "%s [%s]" % (label, out.get("model") or cand["model"])
                print("   servi par %s en %.0f s | usage=%s" % (served, time.time() - started, out.get("usage", {})))
                if choice.get("finish_reason") == "length":
                    print("   ATTENTION : reponse tronquee (finish_reason=length)", file=sys.stderr)
                break
            except Exception as exc:
                last_err = "%s: %s" % (type(exc).__name__, exc)
                print("   ECHEC apres %.0f s -> %s" % (time.time() - started, last_err), file=sys.stderr)
        if result is not None:
            break

    if not result:
        print("ERREUR : aucun candidat gratuit n'a repondu en %d tour(s). Derniere erreur brute :\n%s"
              % (args.rounds, last_err), file=sys.stderr)
        return 3

    if note:
        print("   NOTE : %s" % note, file=sys.stderr)

    written, warned = write_pages(result, taxonomy(schema), args.dry_run)
    if not written:
        print("ERREUR : aucune page exploitable apres controle (%d avertissement(s)) — rien ecrit,"
              " index.md et log.md intacts." % len(warned), file=sys.stderr)
        for w in warned:
            print("  ! %s" % w, file=sys.stderr)
        return 5
    update_index(written, args.dry_run)
    append_log(written, served, args.dry_run)

    print("\n%s %d page(s) %s :" % ("[dry-run]" if args.dry_run else "OK",
                                    len(written), "preparee(s)" if args.dry_run else "ecrite(s)"))
    for rel, fm, _s in written:
        print("  %-52s type=%-10s tags=%s" % (rel, fm.get("type"), ",".join(fm.get("tags") or [])))
    for w in warned:
        print("  ! %s" % w)
    if len(written) < 6:
        print("  ! %d page(s) seulement (cible 6-10 du prompt) : sortie conservatrice du modele."
              % len(written))
    print("index.md et log.md mis a jour (serveur : %s)" % served)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
