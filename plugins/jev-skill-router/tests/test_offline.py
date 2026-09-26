"""Offline tests for jev-skill-router — no network, no keys. Run: python3 tests/test_offline.py"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from jev_router import roster as R
from jev_router import router as RT
from jev_router import client as C

# Root __init__ loaded as a package alias (dir name has hyphens, so no plain import).
_pkg = types.ModuleType("jevskillrouter")
_pkg.__path__ = [str(BASE)]
sys.modules["jevskillrouter"] = _pkg
_spec = importlib.util.spec_from_file_location(
    "jevskillrouter", BASE / "__init__.py", submodule_search_locations=[str(BASE)]
)
plugin = importlib.util.module_from_spec(_spec)
plugin.__path__ = [str(BASE)]
sys.modules["jevskillrouter"] = plugin
_spec.loader.exec_module(plugin)


class StubClient:
    """Canned evaluate() result, or None to simulate failure. Records calls."""

    def __init__(self, first=None, second=None, confidence=None):
        self.first = first
        self.second = second
        self.confidence = confidence or {}
        self.calls = []

    def evaluate(self, state, questions):
        self.calls.append((state, questions))
        answers = self.second if any(k.startswith("fits::") for k in questions) else self.first
        if answers is None:
            return None
        return {
            "answers": answers,
            "confidence": self.confidence,
            "cost": "0.00002",
            "usage": {},
            "latency_ms": 12,
        }


class FailClient:
    def evaluate(self, state, questions):
        return None


class FakeCtx:
    def __init__(self, cfg=None):
        self.cfg = dict(cfg or {})
        self.hooks = []
        self.commands = []

    def get_config(self, key, default=None):
        return self.cfg.get(key, default)

    def set_config(self, key, value):
        self.cfg[key] = value

    def register_hook(self, name, callback):
        self.hooks.append((name, callback))

    def register_cli_command(self, name, help, setup_fn, handler_fn, description=""):
        self.commands.append((name, help, setup_fn, handler_fn, description))


def write_skill(root, dirname, name, desc, body="Body text here."):
    d = Path(root) / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}\n", encoding="utf-8"
    )
    return d / "SKILL.md"


def first_answers(probs, acts=0.9, follow=0.9, prose=0.1):
    return {
        "which": {"probabilities": dict(probs)},
        "gate::acts_on_user_system": {"probability": acts},
        "gate::would_follow_documented_procedure": {"probability": follow},
        "gate::prose_suffices": {"probability": prose},
    }


def second_answers(choice, probs, fits):
    out = {"which": {"choice": choice, "probabilities": dict(probs)}}
    for name, prob in fits.items():
        out[f"fits::{name}"] = {"probability": prob}
    return out


def three_skills(tmp):
    write_skill(tmp, "a", "alpha", "Alpha does deploys.", "Alpha body " * 50)
    write_skill(tmp, "b", "beta", "Beta writes docs.", "Beta body " * 50)
    write_skill(tmp, "c", "gamma", "Gamma crunches numbers.", "Gamma body " * 50)
    return R.load_roster([tmp])


def test_frontmatter_quoted():
    data, _ = R.parse_frontmatter('---\nname: "my-skill"\ndescription: \'does "x" things\'\n---\n\nbody\n')
    assert data == {"name": "my-skill", "description": 'does "x" things'}, data
    print("ok  frontmatter com aspas")


def test_frontmatter_block():
    text = "---\nname: blk\ndescription: >-\n  line one\n  line two\n---\n\nbody\n"
    data, body = R.parse_frontmatter(text)
    assert data["description"] == "line one line two", data
    assert body.strip() == "body", repr(body)
    print("ok  frontmatter em bloco")


def test_frontmatter_missing():
    data, body = R.parse_frontmatter("just a body, no fence\n")
    assert data == {} and body.startswith("just a body"), (data, body)
    print("ok  frontmatter ausente")


def test_roster_scan_dedup():
    with tempfile.TemporaryDirectory() as tmp:
        write_skill(tmp, "a", "alpha", "First " * 40)
        write_skill(tmp, "b", "beta", "Second skill")
        write_skill(tmp, "dup", "alpha", "Duplicate name elsewhere")
        skills = R.load_roster([tmp])
        assert [s.name for s in skills] == ["alpha", "beta"], [s.name for s in skills]
        assert len(skills[0].description) <= R.INDEX_DESC_CHARS, skills[0].description
        print("ok  roster escaneou e deduplicou")


def test_skip_rules():
    assert RT.should_skip_request("/cmd args") is True
    assert RT.should_skip_request("   ") is True
    assert RT.should_skip_request("") is True
    assert RT.should_skip_request("x" * 4001, suggest_chars=4000) is True
    assert RT.should_skip_request("help <skill_relevance>old</skill_relevance>") is True
    assert RT.should_skip_request("help me deploy this") is False
    print("ok  skip rules")


def test_gate_mean_inverted():
    answers = {
        "gate::acts_on_user_system": {"probability": 0.8},
        "gate::would_follow_documented_procedure": {"probability": 0.6},
        "gate::prose_suffices": {"probability": 0.9},
    }
    assert abs(RT.gate_mean(answers) - 0.5) < 1e-9, RT.gate_mean(answers)
    print("ok  gate mean com chave invertida")


def test_chunking_250():
    skills = [
        R.Skill(name=f"s{i:03d}", description=f"Skill {i}", path=Path(f"/tmp/x/s{i:03d}/SKILL.md"))
        for i in range(250)
    ]
    groups = RT.chunk_roster(skills, 240)
    assert len(groups) == 2 and len(groups[0]) == 240 and len(groups[1]) == 10
    probs = {s.name: 0.001 for s in skills}
    probs["s000"] = 0.4
    probs[RT.NONE_OPTION] = 0.05
    stub = StubClient(first=first_answers(probs))
    ranked = RT.rank_wide(stub, "do the thing", skills, chunk=240, shortlist=3)
    assert ranked["calls"] == 2, ranked
    for _, questions in stub.calls:
        assert RT.NONE_OPTION in questions["which"]["criteria"], "chunk sem none_of_these"
    assert ranked["shortlist"], ranked
    print("ok  chunking 250 skills em 2 chunks com none_of_these")


def test_suggest_below_gate():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        stub = StubClient(first=first_answers({"alpha": 0.8, "beta": 0.1, "gamma": 0.1},
                                              acts=0.1, follow=0.1, prose=0.9))
        assert RT.suggest(stub, "deploy it", skills) is None
        assert len(stub.calls) == 1, "gate baixo nao devia chamar request 2"
        print("ok  suggest gate baixo devolve None")


def test_suggest_clean_winner():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        stub = StubClient(
            first=first_answers({"alpha": 0.7, "beta": 0.2, "gamma": 0.1}),
            second=second_answers("alpha", {"alpha": 0.75}, {"alpha": 0.9, "beta": 0.1, "gamma": 0.1}),
            confidence={"which": 0.8},
        )
        res = RT.suggest(stub, "deploy the site", skills)
        assert res is not None and res.skill == "alpha", res
        assert res.calls == 2 and res.gate >= 0.3, res
        print("ok  suggest vencedor limpo devolve Result")


def test_suggest_none_winner():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        stub = StubClient(
            first=first_answers({"alpha": 0.5, "beta": 0.3, "gamma": 0.2}),
            second=second_answers(RT.NONE_OPTION, {RT.NONE_OPTION: 0.8}, {}),
        )
        assert RT.suggest(stub, "something else", skills) is None
        print("ok  suggest none_of_these devolve None")


def test_suggest_fits_below():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        stub = StubClient(
            first=first_answers({"alpha": 0.7, "beta": 0.2, "gamma": 0.1}),
            second=second_answers("alpha", {"alpha": 0.6}, {"alpha": 0.1}),
        )
        assert RT.suggest(stub, "deploy the site", skills) is None
        print("ok  suggest fits abaixo devolve None")


def test_suggest_fail_open():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        assert RT.suggest(FailClient(), "deploy it", skills) is None
        assert RT.suggest(StubClient(first=None), "deploy it", skills) is None
        print("ok  fail-open com client None")


class ChunkStub:
    """One canned answer per call: ranks a different skill first in each chunk."""

    def __init__(self, per_call):
        self.per_call = per_call
        self.calls = []

    def evaluate(self, state, questions):
        idx = len(self.calls)
        self.calls.append((state, questions))
        return {
            "answers": self.per_call[idx],
            "confidence": {},
            "cost": "0.00002",
            "usage": {},
            "latency_ms": 12,
        }


def test_rank_best_chunk_first():
    skills = [
        R.Skill(name=n, description=f"Skill {n}", path=Path(f"/tmp/x/{n}/SKILL.md"))
        for n in ("s-a", "s-b", "s-c", "s-d")
    ]
    gate_answers = {
        "gate::acts_on_user_system": {"probability": 0.9},
        "gate::would_follow_documented_procedure": {"probability": 0.9},
        "gate::prose_suffices": {"probability": 0.1},
    }
    stub = ChunkStub(
        [
            {
                "which": {"probabilities": {"s-a": 0.5, "s-b": 0.3, RT.NONE_OPTION: 0.0}},
                **gate_answers,
            },
            {
                "which": {"probabilities": {"s-c": 0.9, "s-d": 0.05, RT.NONE_OPTION: 0.0}},
            },
        ]
    )
    ranked = RT.rank_wide(stub, "do the thing", skills, chunk=2, shortlist=1)
    assert ranked is not None
    assert ranked["calls"] == 2, ranked
    assert ranked["shortlist"] == ["s-c"], ranked
    print("ok  shortlist comeca pelo melhor chunk")


def test_rank_discards_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        skills = three_skills(tmp)
        stub = StubClient(
            first=first_answers(
                {"ghost-skill": 0.9, "alpha": 0.05, "beta": 0.02, "gamma": 0.01}
            ),
            second=second_answers(
                "alpha", {"alpha": 0.8}, {"alpha": 0.9, "beta": 0.1, "gamma": 0.1}
            ),
            confidence={"which": 0.8},
        )
        res = RT.suggest(stub, "deploy the site", skills)
        assert res is not None and res.skill == "alpha", res
        print("ok  nome alucinado descartado da shortlist")


def test_roster_no_cap():
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(260):
            write_skill(tmp, f"d{i:03d}", f"skill-{i:03d}", f"Skill number {i}")
        skills = R.load_roster([tmp])
        assert len(skills) == 260, len(skills)
        print("ok  roster acima de 255 sem teto")


def test_register_hook_and_command():
    ctx = FakeCtx()
    plugin.register(ctx)
    assert [n for n, _ in ctx.hooks] == ["pre_llm_call"], ctx.hooks
    assert [c[0] for c in ctx.commands] == ["jev-skill-router"], ctx.commands
    assert all(kw for _, cb in ctx.hooks for kw in [True] if "kwargs" in str(cb.__code__.co_varnames))
    print("ok  register hook e comando")


def test_hook_fail_open():
    ctx = FakeCtx({"mode": "off"})
    plugin.register(ctx)
    handler = ctx.hooks[0][1]
    assert handler(user_message="hello") is None
    assert handler(user_message=None) is None
    assert handler() is None
    assert handler(user_message="/own flow") is None
    print("ok  hook fail-open")


def test_cli_status_and_check():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        (home / "skills").mkdir(parents=True)
        old_home, old_key = os.environ.get("HERMES_HOME"), os.environ.get("AI_GATEWAY_API_KEY")
        old_ts = os.environ.get("TYPESAFE_API_KEY")
        os.environ["HERMES_HOME"] = str(home)
        os.environ.pop("AI_GATEWAY_API_KEY", None)
        os.environ.pop("TYPESAFE_API_KEY", None)
        try:
            ctx = FakeCtx({"mode": "off", "roster_dir": str(home / "skills"),
                           "log_path": str(home / "logs" / "jev-skill-router.log")})
            plugin.register(ctx)
            _, _, setup_fn, handler_fn, _ = ctx.commands[0]
            parser = argparse.ArgumentParser()
            setup_fn(parser)
            assert handler_fn(parser.parse_args(["status"])) == 0
            assert handler_fn(parser.parse_args(["check"])) == 1  # sem chave
        finally:
            if old_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = old_home
            if old_key is not None:
                os.environ["AI_GATEWAY_API_KEY"] = old_key
            if old_ts is not None:
                os.environ["TYPESAFE_API_KEY"] = old_ts
    print("ok  cli status e check")


# --- Dual backend (ticket 10): transporte stubado, relógio mockado, sem rede ---

import contextlib as _contextlib
import email.utils as _email_utils
import time as _time
import urllib.error as _urlerror


class _FakeResp:
    def __init__(self, body):
        self._raw = json.dumps(body).encode()

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(code, retry_after=None):
    hdrs = {}
    if retry_after is not None:
        hdrs["retry-after"] = retry_after
    return _urlerror.HTTPError("https://x.invalid/", code, "limited", hdrs, None)


class _Script:
    """Transporte stubado: sequência de ('ok', body) | ('http', code, retry-after)."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []  # (url, headers minúsculos, payload)

    def __call__(self, req, timeout=None):
        headers = {k.lower(): v for k, v in req.header_items()}
        payload = json.loads(req.data.decode())
        self.calls.append((req.full_url, headers, payload))
        kind = self.steps.pop(0)
        if kind[0] == "ok":
            return _FakeResp(kind[1])
        raise _http_error(kind[1], kind[2] if len(kind) > 2 else None)


class _Clock:
    def __init__(self):
        self.t = 1000.0
        self.sleeps = []

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


_TS_BODY = {
    "answers": {
        "destructive": {"type": "noul", "noul": 0.97},
        "pick": {
            "type": "choice",
            "choice": "b",
            "probabilities": {"a": 0.1, "b": 0.9},
            "confidence": 0.8,
        },
    },
    "usage": {"input_tokens": 10, "output_tokens": 5},
}

_OR_BODY = {
    "answers": {
        "urgent": {"type": "noul", "noul": 0.88},
        "which": {
            "type": "choice",
            "choice": "alpha",
            "probabilities": {"alpha": 0.7},
            "confidence": 0.8,
        },
    },
    "usage": {"input_tokens": 10, "output_tokens": 0, "cost": 0.00002},
}

_GW_BODY = {
    "answers": {"which": {"choice": "alpha", "probabilities": {"alpha": 0.7}}},
    "providerMetadata": {
        "typesafe": {"confidence": {"which": 0.8}},
        "gateway": {"cost": "0.00002"},
    },
    "usage": {"input_tokens": 10, "output_tokens": 5},
}

_Q = {"q": {"type": "boolean", "instructions": "?"}}
_TS_URL = "https://api.typesafe.ai/v1/systemone"
_OR_URL = "https://openrouter.ai/api/alpha/decisions"
_GW_URL = "https://ai-gateway.vercel.sh/v4/ai/evaluation-model"


def _dual_client(keys, **kw):
    """Cliente com HERMES_HOME vazio, chaves controladas e estado global zerado."""
    steps = kw.pop("_steps", None) or []
    kw.setdefault("min_interval_s", 0)
    with tempfile.TemporaryDirectory() as home:
        saved = {
            n: os.environ.get(n)
            for n in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY", "HERMES_HOME")
        }
        try:
            for n in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY"):
                os.environ.pop(n, None)
            for n, v in keys.items():
                os.environ[n] = v
            os.environ["HERMES_HOME"] = home
            C._PACE_LAST.clear()
            C._BREAKER.clear()
            client = C.JevClient(**kw)
            clock = _Clock()
            client._clock = clock.monotonic
            client._sleep = clock.sleep
            script = _Script(steps)
            client._urlopen = script
            yield client, script, clock
        finally:
            for n, v in saved.items():
                if v is None:
                    os.environ.pop(n, None)
                else:
                    os.environ[n] = v


def _run_dual(keys, **kw):
    """Devolve o context manager; entrar com _enter, sair com _leave."""
    return _contextlib.contextmanager(_dual_client)(keys, **kw)


def _enter(ctx):
    entered = ctx.__enter__()
    entered[0]._test_ctx = ctx
    return entered


def _leave(client):
    client._test_ctx.__exit__(None, None, None)


def test_settings_dual_defaults():
    s = plugin._settings(FakeCtx({}))
    assert s["backend"] == "auto", s
    assert s["typesafe_model"] == "jev-latest", s
    assert s["typesafe_base_url"] == "https://api.typesafe.ai", s
    assert s["openrouter_model"] == "~typesafe/jev-latest", s
    assert s["openrouter_base_url"] == "https://openrouter.ai/api/alpha", s
    assert s["retry_max_wait_s"] == 2.0, s
    assert s["breaker_threshold"] == 3, s
    assert s["breaker_cooldown_s"] == 120, s
    assert s["min_interval_s"] == 0.25, s
    assert s["cache_seconds"] == 300, s
    print("ok  settings com defaults do backend duplo")


def test_hook_auto_silent_without_key():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        (home / "skills").mkdir(parents=True)
        saved = {
            n: os.environ.get(n)
            for n in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY", "HERMES_HOME")
        }
        os.environ.pop("TYPESAFE_API_KEY", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("AI_GATEWAY_API_KEY", None)
        os.environ["HERMES_HOME"] = str(home)
        try:
            ctx = FakeCtx({"mode": "auto"})
            plugin.register(ctx)
            handler = ctx.hooks[0][1]
            assert handler(user_message="deploy the site") is None
            ctx2 = FakeCtx({"mode": "auto", "backend": "typesafe"})
            plugin.register(ctx2)
            assert ctx2.hooks[0][1](user_message="deploy the site") is None
        finally:
            for n, v in saved.items():
                if v is None:
                    os.environ.pop(n, None)
                else:
                    os.environ[n] = v
    print("ok  hook auto silencioso sem chave (sem rede)")


def test_typesafe_noul_mapping():
    client, script, _ = _enter(
        _run_dual({"TYPESAFE_API_KEY": "ts-key"}, _steps=[("ok", _TS_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None, "typesafe com chave devia responder"
        assert len(script.calls) == 1
        url, headers, payload = script.calls[0]
        assert url == _TS_URL, url
        assert headers.get("authorization") == "Bearer ts-key", headers
        assert "ai-model-id" not in headers, headers
        assert payload["model"] == "jev-latest", payload
        assert payload["questions"] == {"q": {"type": "noul", "instructions": "?"}}, payload
        assert res["answers"]["destructive"] == {"type": "boolean", "probability": 0.97}, res
        assert res["answers"]["pick"]["choice"] == "b", res
        assert res["confidence"] == {"pick": 0.8}, res["confidence"]
        assert res["cost"] is None, res
        assert res["usage"] == {"input_tokens": 10, "output_tokens": 5}, res
    finally:
        _leave(client)
    print("ok  typesafe direto: boolean vira noul, confiança inline, custo None")


def test_gateway_confidence_and_cost():
    client, script, _ = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "gw-key"}, _steps=[("ok", _GW_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None
        url, headers, payload = script.calls[0]
        assert url == _GW_URL, url
        assert headers.get("ai-model-id") == "typesafe-ai/jev", headers
        assert "model" not in payload, payload
        assert payload["questions"] == _Q, payload
        assert res["answers"] == _GW_BODY["answers"], res
        assert res["confidence"] == {"which": 0.8}, res
        assert res["cost"] == "0.00002", res
    finally:
        _leave(client)
    print("ok  gateway: confiança via providerMetadata, custo repassado")


def test_openrouter_decisions_endpoint():
    client, script, _ = _enter(
        _run_dual({"OPENROUTER_API_KEY": "or-key"}, _steps=[("ok", _OR_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None
        url, headers, payload = script.calls[0]
        assert url == _OR_URL, url
        assert headers.get("authorization") == "Bearer or-key", headers
        assert payload["model"] == "~typesafe/jev-latest", payload
        assert payload["questions"] == {"q": {"type": "noul", "instructions": "?"}}, payload
        assert res["answers"]["urgent"] == {"type": "boolean", "probability": 0.88}, res
        assert res["answers"]["which"]["choice"] == "alpha", res
        assert res["confidence"] == {"which": 0.8}, res["confidence"]
        assert res["cost"] == 0.00002, res
    finally:
        _leave(client)
    print("ok  openrouter decisions: noul mapping e endpoint alpha")


def test_openrouter_pool_runtime_key_import_hook():
    """OpenRouter pool lookup uses Hermes' runtime key resolver before raw auth.json."""
    class Entry:
        runtime_api_key = "pool-runtime-key"

    class Pool:
        def select(self):
            return Entry()

        def peek(self):
            return Entry()

    fake_agent = types.ModuleType("agent")
    fake_pool = types.ModuleType("agent.credential_pool")
    fake_pool.load_pool = lambda provider: Pool()
    old_agent = sys.modules.get("agent")
    old_pool = sys.modules.get("agent.credential_pool")
    sys.modules["agent"] = fake_agent
    sys.modules["agent.credential_pool"] = fake_pool
    saved = {n: os.environ.get(n) for n in ("OPENROUTER_API_KEY", "HERMES_HOME")}
    try:
        os.environ.pop("OPENROUTER_API_KEY", None)
        with tempfile.TemporaryDirectory() as home:
            Path(home, "auth.json").write_text(
                json.dumps({"credential_pool": {"openrouter": [{"access_token": "stale-disk-key"}]}}),
                encoding="utf-8",
            )
            os.environ["HERMES_HOME"] = home
            assert C.openrouter_api_key() == "pool-runtime-key"
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        if old_agent is None:
            sys.modules.pop("agent", None)
        else:
            sys.modules["agent"] = old_agent
        if old_pool is None:
            sys.modules.pop("agent.credential_pool", None)
        else:
            sys.modules["agent.credential_pool"] = old_pool
    print("ok  openrouter credential pool usa runtime_api_key")


def test_openrouter_pool_empty_selection_does_not_reuse_disk_key():
    """A loaded Hermes pool with no selected entry must not fall back to auth.json."""
    class Pool:
        def select(self):
            return None

        def peek(self):
            return None

    fake_agent = types.ModuleType("agent")
    fake_pool = types.ModuleType("agent.credential_pool")
    fake_pool.load_pool = lambda provider: Pool()
    old_agent = sys.modules.get("agent")
    old_pool = sys.modules.get("agent.credential_pool")
    sys.modules["agent"] = fake_agent
    sys.modules["agent.credential_pool"] = fake_pool
    saved = {n: os.environ.get(n) for n in ("OPENROUTER_API_KEY", "HERMES_HOME")}
    try:
        os.environ.pop("OPENROUTER_API_KEY", None)
        with tempfile.TemporaryDirectory() as home:
            Path(home, "auth.json").write_text(
                json.dumps({"credential_pool": {"openrouter": [{"access_token": "stale-disk-key"}]}}),
                encoding="utf-8",
            )
            os.environ["HERMES_HOME"] = home
            assert C.openrouter_api_key() == ""
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        if old_agent is None:
            sys.modules.pop("agent", None)
        else:
            sys.modules["agent"] = old_agent
        if old_pool is None:
            sys.modules.pop("agent.credential_pool", None)
        else:
            sys.modules["agent.credential_pool"] = old_pool
    print("ok  openrouter credential pool vazio nao reaproveita auth.json")


def test_openrouter_pool_detection_uses_peek_not_select():
    """Backend detection may inspect the pool but must not rotate it."""
    class Entry:
        runtime_api_key = "pool-runtime-key"

    class Pool:
        select_calls = 0
        peek_calls = 0

        def select(self):
            type(self).select_calls += 1
            return Entry()

        def peek(self):
            type(self).peek_calls += 1
            return Entry()

    fake_agent = types.ModuleType("agent")
    fake_pool = types.ModuleType("agent.credential_pool")
    fake_pool.load_pool = lambda provider: Pool()
    old_agent = sys.modules.get("agent")
    old_pool = sys.modules.get("agent.credential_pool")
    sys.modules["agent"] = fake_agent
    sys.modules["agent.credential_pool"] = fake_pool
    saved = {n: os.environ.get(n) for n in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY", "HERMES_HOME")}
    try:
        for n in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY"):
            os.environ.pop(n, None)
        with tempfile.TemporaryDirectory() as home:
            os.environ["HERMES_HOME"] = home
            assert C.resolve_backend("auto") == "openrouter"
            assert Pool.peek_calls == 1
            assert Pool.select_calls == 0
            client, script, _ = _enter(_run_dual({}, _steps=[("ok", _OR_BODY)]))
            try:
                assert client.evaluate({"request": "x"}, _Q) is not None
                assert script.calls[0][1].get("authorization") == "Bearer pool-runtime-key"
                assert client.evaluate({"request": "x"}, _Q) is not None
                assert len(script.calls) == 1
            finally:
                _leave(client)
            assert Pool.select_calls == 1
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        if old_agent is None:
            sys.modules.pop("agent", None)
        else:
            sys.modules["agent"] = old_agent
        if old_pool is None:
            sys.modules.pop("agent.credential_pool", None)
        else:
            sys.modules["agent.credential_pool"] = old_pool
    print("ok  openrouter credential pool usa peek para detectar")


def test_openrouter_malformed_response_shapes_fail_open():
    client, _, _ = _enter(
        _run_dual({"OPENROUTER_API_KEY": "or-key"}, _steps=[("ok", ["not", "an", "object"])])
    )
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
    finally:
        _leave(client)

    body = dict(_OR_BODY)
    body["usage"] = ["not", "a", "mapping"]
    client, _, _ = _enter(
        _run_dual({"OPENROUTER_API_KEY": "or-key"}, _steps=[("ok", body)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None
        assert res["cost"] is None, res
        assert res["usage"] == {}, res
    finally:
        _leave(client)

    body = dict(_OR_BODY)
    body["answers"] = ["not", "a", "mapping"]
    client, _, _ = _enter(
        _run_dual({"OPENROUTER_API_KEY": "or-key"}, _steps=[("ok", body)])
    )
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
    finally:
        _leave(client)
    print("ok  openrouter respostas malformadas falham abertas")


def test_backend_selection():
    cases = [
        ({"TYPESAFE_API_KEY": "t", "OPENROUTER_API_KEY": "o", "AI_GATEWAY_API_KEY": "g"}, "auto", "typesafe", _TS_URL),
        ({"OPENROUTER_API_KEY": "o", "AI_GATEWAY_API_KEY": "g"}, "auto", "openrouter", _OR_URL),
        ({"AI_GATEWAY_API_KEY": "g"}, "auto", "gateway", _GW_URL),
        ({"TYPESAFE_API_KEY": "t"}, "auto", "typesafe", _TS_URL),
        ({"OPENROUTER_API_KEY": "o"}, "auto", "openrouter", _OR_URL),
        ({}, "auto", None, None),
        ({"TYPESAFE_API_KEY": "", "OPENROUTER_API_KEY": "o", "AI_GATEWAY_API_KEY": "g"}, "auto", "openrouter", _OR_URL),
        ({"AI_GATEWAY_API_KEY": "g"}, "typesafe", None, None),
        ({"OPENROUTER_API_KEY": "o"}, "typesafe", None, None),
        ({"TYPESAFE_API_KEY": "t"}, "gateway", None, None),
        ({"OPENROUTER_API_KEY": "o"}, "gateway", None, None),
        ({"AI_GATEWAY_API_KEY": "g"}, "openrouter", None, None),
        ({"OPENROUTER_API_KEY": "o"}, "openrouter", "openrouter", _OR_URL),
        ({"TYPESAFE_API_KEY": "t", "AI_GATEWAY_API_KEY": "g"}, "gateway", "gateway", _GW_URL),
        ({"TYPESAFE_API_KEY": "t", "AI_GATEWAY_API_KEY": "g"}, "bogus", "typesafe", _TS_URL),
    ]
    for keys, backend, want, url in cases:
        steps = [("ok", _OR_BODY if want in ("typesafe", "openrouter") else _GW_BODY)] if want else []
        client, script, _ = _enter(_run_dual(keys, backend=backend, _steps=steps))
        try:
            assert C.resolve_backend(backend) == want, (keys, backend, want)
            res = client.evaluate({"request": "x"}, _Q)
            if want is None:
                assert res is None and script.calls == [], (keys, backend)
            else:
                assert res is not None and len(script.calls) == 1, (keys, backend)
                assert script.calls[0][0] == url, script.calls[0][0]
        finally:
            _leave(client)
    print("ok  backend auto|typesafe|openrouter|gateway resolve e silencia sem chave")


def test_retry_after_seconds():
    client, script, clock = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("http", 429, "1"), ("ok", _GW_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None and len(script.calls) == 2, script.calls
        assert clock.sleeps == [1.0], clock.sleeps
    finally:
        _leave(client)
    print("ok  retry honrou Retry-After em segundos (1 retry)")


def test_retry_after_http_date():
    when = _email_utils.formatdate(_time.time() + 1, usegmt=True)
    client, script, clock = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("http", 429, when), ("ok", _GW_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None and len(script.calls) == 2, script.calls
        assert len(clock.sleeps) == 1 and 0 < clock.sleeps[0] <= 2.0, clock.sleeps
    finally:
        _leave(client)
    print("ok  retry honrou Retry-After como data HTTP")


def test_retry_after_garbage():
    client, script, clock = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("http", 429, "banana")])
    )
    try:
        assert C.retry_after_s("banana", _time.time()) is None
        assert C.retry_after_s("", _time.time()) is None
        assert C.retry_after_s(None, _time.time()) is None
        assert client.evaluate({"request": "x"}, _Q) is None
        assert len(script.calls) == 1 and clock.sleeps == [], (script.calls, clock.sleeps)
    finally:
        _leave(client)
    print("ok  Retry-After lixo: sem retry, fail-open")


def test_retry_after_too_long():
    client, script, clock = _enter(
        _run_dual(
            {"AI_GATEWAY_API_KEY": "g"},
            retry_max_wait_s=2.0,
            _steps=[("http", 429, "30")],
        )
    )
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
        assert len(script.calls) == 1 and clock.sleeps == [], (script.calls, clock.sleeps)
    finally:
        _leave(client)
    print("ok  espera acima do teto: sem retry, fail-open")


def test_retry_529():
    client, script, clock = _enter(
        _run_dual({"TYPESAFE_API_KEY": "t"}, _steps=[("http", 529, "1"), ("ok", _TS_BODY)])
    )
    try:
        res = client.evaluate({"request": "x"}, _Q)
        assert res is not None and len(script.calls) == 2, script.calls
        assert res["answers"]["destructive"] == {"type": "boolean", "probability": 0.97}, res
    finally:
        _leave(client)
    print("ok  529 tratado como rate limit (1 retry)")


def test_retry_only_once():
    client, script, clock = _enter(
        _run_dual(
            {"AI_GATEWAY_API_KEY": "g"},
            _steps=[("http", 429, "1"), ("http", 429, "1"), ("ok", _GW_BODY)],
        )
    )
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
        assert len(script.calls) == 2, script.calls  # nunca em loop
    finally:
        _leave(client)
    print("ok  retry único: segundo 429 não tenta de novo")


def test_breaker_opens_and_recovers():
    client, script, clock = _enter(
        _run_dual(
            {"AI_GATEWAY_API_KEY": "g"},
            breaker_threshold=3,
            breaker_cooldown_s=120,
            _steps=[("http", 429, "lixo")] * 3,
        )
    )
    try:
        for i in range(3):
            assert client.evaluate({"request": i}, _Q) is None
        assert len(script.calls) == 3, script.calls
        # Breaker aberto: silêncio sem tocar o transporte.
        assert client.evaluate({"request": 99}, _Q) is None
        assert len(script.calls) == 3, script.calls
        # Cooldown passou: volta a tentar; sucesso zera o contador.
        clock.t += 121
        script.steps.append(("ok", _GW_BODY))
        assert client.evaluate({"request": 100}, _Q) is not None
        assert len(script.calls) == 4, script.calls
        script.steps.extend([("http", 429, "lixo")] * 2)
        assert client.evaluate({"request": 101}, _Q) is None
        assert client.evaluate({"request": 102}, _Q) is None
        assert len(script.calls) == 6, script.calls  # 2 falhas pós-sucesso não abrem
    finally:
        _leave(client)
    print("ok  breaker abriu após 3, recuperou após cooldown, sucesso zerou")


def test_min_interval_spacing():
    client, script, clock = _enter(
        _run_dual(
            {"AI_GATEWAY_API_KEY": "g"},
            min_interval_s=0.25,
            _steps=[("ok", _GW_BODY), ("ok", _GW_BODY)],
        )
    )
    try:
        assert client.evaluate({"request": 1}, _Q) is not None
        assert client.evaluate({"request": 2}, _Q) is not None
        assert clock.sleeps == [0.25], clock.sleeps
    finally:
        _leave(client)
    print("ok  min_interval_s espaçou chamadas (clock mockado)")


def test_silence_without_key():
    client, script, _ = _enter(_run_dual({}, _steps=[("ok", _GW_BODY)]))
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
        assert script.calls == [], script.calls
    finally:
        _leave(client)
    print("ok  sem chave nenhuma: silencioso, transporte intocado")


def test_retry_after_nonfinite():
    now = _time.time()
    assert C.retry_after_s("nan", now) is None
    assert C.retry_after_s("inf", now) is None
    assert C.retry_after_s("-inf", now) is None
    client, script, clock = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("http", 429, "nan")])
    )
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
        assert len(script.calls) == 1 and clock.sleeps == [], (script.calls, clock.sleeps)
    finally:
        _leave(client)
    print("ok  Retry-After nan/inf: sem retry, fail-open")


def test_breaker_counts_once_per_evaluate():
    client, script, clock = _enter(
        _run_dual(
            {"AI_GATEWAY_API_KEY": "g"},
            breaker_threshold=4,
            _steps=[("http", 429, "1"), ("http", 429, "1")] * 3,
        )
    )
    try:
        for i in range(3):
            assert client.evaluate({"request": i}, _Q) is None
        # 3 evaluates x 2 attempts; breaker counts 1 per evaluate, still closed.
        assert len(script.calls) == 6, script.calls
        script.steps.append(("http", 429, "lixo"))
        assert client.evaluate({"request": 99}, _Q) is None
        assert len(script.calls) == 7, script.calls
    finally:
        _leave(client)
    print("ok  breaker conta 1 por evaluate (429+429 sem retry duplo)")


def test_boolean_criteria_passthrough():
    out = C.to_typesafe_questions(
        {
            "q": {
                "type": "boolean",
                "instructions": "?",
                "criteria": {"true": "loss", "false": "safe"},
            }
        }
    )
    assert out == {
        "q": {"type": "noul", "instructions": "?", "criteria": {"true": "loss", "false": "safe"}}
    }, out
    plain = C.to_typesafe_questions({"q": {"type": "boolean", "instructions": "?"}})
    assert plain == {"q": {"type": "noul", "instructions": "?"}}, plain
    print("ok  criteria propagado no boolean->noul")


def test_cache_ttl():
    client, script, _ = _enter(
        _run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("ok", _GW_BODY), ("ok", _GW_BODY)])
    )
    try:
        assert client.cache_seconds == 300, client.cache_seconds
        assert client.evaluate({"request": "x"}, _Q) is not None
        assert client.evaluate({"request": "x"}, _Q) is not None
        assert len(script.calls) == 1, script.calls  # hit within TTL
        for key in list(client._cache):
            _, result = client._cache[key]
            client._cache[key] = (0.0, result)  # force expiry
        assert client.evaluate({"request": "x"}, _Q) is not None
        assert len(script.calls) == 2, script.calls
    finally:
        _leave(client)
    print("ok  cache do router com TTL: hit dentro, miss fora")


def test_roster_follows_external_symlink():
    with tempfile.TemporaryDirectory() as tmp:
        outside = Path(tmp) / "outside"
        write_skill(outside, "ext", "external", "External skill via symlink.")
        root = Path(tmp) / "root"
        write_skill(root, "plain", "plain", "Plain local skill.")
        os.symlink(outside / "ext", root / "ext")
        skills = R.load_roster([root])
        assert [s.name for s in skills] == ["external", "plain"], [s.name for s in skills]
        print("ok  roster alcançou skill via symlink externo")


def test_roster_symlink_cycle_no_hang_no_dup():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_skill(root, "a", "alpha", "Alpha skill.")
        write_skill(root, "b", "beta", "Beta skill.")
        os.symlink(root, root / "a" / "loop")  # ancestral cycle
        os.symlink(root / "b", root / "b" / "self")  # self cycle
        os.symlink(root / "b", root / "b-alias")  # alias: same target, second path
        files = list(R.iter_skill_files(root))
        assert len(files) == 2, files  # each canonical dir visited once
        skills = R.load_roster([root])
        assert [s.name for s in skills] == ["alpha", "beta"], [s.name for s in skills]
        print("ok  symlink cíclico não travou nem duplicou")


# --- Ticket 19: transporte endurecido + normalização estrita ---

import urllib.request as _urlrequest


def _opener_uses_proxy(opener):
    """True se algum ProxyHandler atua nas cadeias http/https do opener."""
    chains = opener.handle_open.get("http", []) + opener.handle_open.get("https", [])
    return any(isinstance(h, _urlrequest.ProxyHandler) for h in chains)


def test_transport_default_hardened():
    with _run_dual({}):
        fresh = C.JevClient()  # fresco: _dual_client troca _urlopen pelo stub
        assert fresh._urlopen is C._urlopen, "default deve ser o transporte endurecido"
        assert fresh._urlopen is not _urlrequest.urlopen
        assert any(isinstance(h, C._NoRedirect) for h in C._OPENER.handlers)
        assert not _opener_uses_proxy(C._OPENER)
    print("ok  transporte default: sem redirect, sem proxy do ambiente")


def test_transport_redirect_fail_open():
    client, script, _ = _enter(_run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("http", 302)]))
    try:
        assert client.evaluate({"request": "x"}, _Q) is None
        assert len(script.calls) == 1, script.calls  # 3xx nunca é seguido
    finally:
        _leave(client)
    redir = C._NoRedirect().redirect_request(
        object(), None, 302, "Found", {}, "https://x.invalid/"
    )
    assert redir is None, redir
    print("ok  302 vira fail-open sem seguir redirect")


def test_transport_ignores_proxy_env():
    saved = {n: os.environ.get(n) for n in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")}
    try:
        for n in saved:
            os.environ[n] = "http://proxy.invalid:8080"
        assert _urlrequest.getproxies(), "sanidade: o env vaza para o default do urllib"
        assert _opener_uses_proxy(_urlrequest.build_opener()), "sanidade: opener default usa proxy"
        assert not _opener_uses_proxy(C._OPENER), "opener endurecido ignora o env"
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    print("ok  proxy do ambiente ignorado mesmo com http(s)_proxy setado")


def test_payload_cap_fail_open():
    big = {"request": "x", "blob": "y" * (C.MAX_PAYLOAD_BYTES + 1)}
    client, script, _ = _enter(_run_dual({"AI_GATEWAY_API_KEY": "g"}, _steps=[("ok", _GW_BODY)]))
    try:
        assert client.evaluate(big, _Q) is None
        assert script.calls == [], script.calls  # nada saiu: nunca vira veredito
        assert client.evaluate({"request": "x"}, _Q) is not None  # sob o cap, passa
        assert len(script.calls) == 1, script.calls
    finally:
        _leave(client)
    print("ok  payload acima do cap: nada enviado, fail-open")


def test_normalize_strict_noul():
    out = C.normalize_typesafe_answers(
        {
            "ok": {"type": "noul", "noul": 0.88},
            "zero": {"type": "noul", "noul": 0.0},  # 0.0 explícito do servidor passa
            "one": {"type": "noul", "noul": 1.0},  # 1.0 explícito do servidor passa
            "false": {"type": "noul", "noul": False},  # bool não é número: some (#28)
            "true": {"type": "noul", "noul": True},  # bool não é número: some (#28)
            "missing": {"type": "noul"},
            "null": {"type": "noul", "noul": None},
            "garbage": {"type": "noul", "noul": "alta"},
            "nan": {"type": "noul", "noul": "nan"},
            "inf": {"type": "noul", "noul": float("inf")},
            "choice": {"type": "choice", "choice": "alpha"},
        }
    )
    assert out["ok"] == {"type": "boolean", "probability": 0.88}, out
    assert out["zero"] == {"type": "boolean", "probability": 0.0}, out
    assert out["one"] == {"type": "boolean", "probability": 1.0}, out
    assert out["choice"] == {"type": "choice", "choice": "alpha"}, out
    for qid in ("missing", "null", "garbage", "nan", "inf", "false", "true"):
        assert qid not in out, (qid, out)  # nunca fabrica 0.0: some
    print("ok  noul ausente/malformado some (nunca 0.0); 0.0 explícito passa")


if __name__ == "__main__":
    for fn in (
        test_frontmatter_quoted,
        test_frontmatter_block,
        test_frontmatter_missing,
        test_roster_scan_dedup,
        test_skip_rules,
        test_gate_mean_inverted,
        test_chunking_250,
        test_suggest_below_gate,
        test_suggest_clean_winner,
        test_suggest_none_winner,
        test_suggest_fits_below,
        test_suggest_fail_open,
        test_rank_best_chunk_first,
        test_rank_discards_unknown,
        test_roster_no_cap,
        test_register_hook_and_command,
        test_hook_fail_open,
        test_cli_status_and_check,
        test_settings_dual_defaults,
        test_hook_auto_silent_without_key,
        test_typesafe_noul_mapping,
        test_gateway_confidence_and_cost,
        test_openrouter_decisions_endpoint,
        test_openrouter_pool_runtime_key_import_hook,
        test_openrouter_pool_empty_selection_does_not_reuse_disk_key,
        test_openrouter_pool_detection_uses_peek_not_select,
        test_openrouter_malformed_response_shapes_fail_open,
        test_backend_selection,
        test_retry_after_seconds,
        test_retry_after_http_date,
        test_retry_after_garbage,
        test_retry_after_too_long,
        test_retry_529,
        test_retry_only_once,
        test_breaker_opens_and_recovers,
        test_min_interval_spacing,
        test_silence_without_key,
        test_retry_after_nonfinite,
        test_breaker_counts_once_per_evaluate,
        test_boolean_criteria_passthrough,
        test_cache_ttl,
        test_roster_follows_external_symlink,
        test_roster_symlink_cycle_no_hang_no_dup,
        test_transport_default_hardened,
        test_transport_redirect_fail_open,
        test_transport_ignores_proxy_env,
        test_payload_cap_fail_open,
        test_normalize_strict_noul,
    ):
        fn()
    print("\ntodos os testes offline passaram")
