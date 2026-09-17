#!/usr/bin/env python3
"""
NVIDIA NIM Proxy — Translate OmniRoute openai-prefixed model names to NVIDIA NIM format.
OmniRoute sends:  model = "openai/nvidia/nemotron-3.5-lightning-30b-a3b"
This proxy strips "openai/" and forwards to https://integrate.api.nvidia.com/v1

Usage:
  python nvidia-nim-proxy.py                    # default port 20200
  python nvidia-nim-proxy.py --port 20200

Configure in OmniRoute as an "openai" provider with baseUrl = http://127.0.0.1:20200/v1
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

class NIMProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Suppress default logging, use custom
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            self._forward_get_models()
        elif self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            self._forward_chat()
        elif self.path == "/v1/completions":
            self._forward_completions()
        else:
            self._respond(404, {"error": "not found"})

    def _forward_get_models(self):
        """Forward /v1/models to NVIDIA NIM."""
        try:
            req = urllib.request.Request(
                f"{NVIDIA_NIM_URL}/models",
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            self._respond(200, data)
        except Exception as e:
            self._respond(502, {"error": str(e)})

    def _forward_chat(self):
        """Forward /v1/chat/completions, normalizing the model name for NVIDIA NIM."""
        body = self._read_body()
        if not body:
            self._respond(400, {"error": "empty body"})
            return

        # OmniRoute (provider "openai") strips the original namespace and adds "openai/".
        # NVIDIA NIM expects "nvidia/<name>". Normalize: strip known router prefixes,
        # then re-add "nvidia/" if no remaining namespace.
        model = body.get("model", "")
        original = model
        if "/" in model:
            parts = model.split("/", 1)
            if parts[0] in ("openai", "pollinations", "auto", "oc", "opencode"):
                model = parts[1]
        # If still no namespace (e.g. "nemotron-3.5-lightning-30b-a3b"), re-add "nvidia/"
        if "/" not in model:
            model = f"nvidia/{model}"
        body["model"] = model

        # NVIDIA NIM rejects unknown parameters (prompt_cache_key, etc.) with 400.
        for key in ("prompt_cache_key", "prompt_cache_behavior"):
            body.pop(key, None)

        # Ce proxy ne relaie que du JSON complet : s'il transmet stream=true, NVIDIA repond en
        # SSE et json.loads echoue -> 502 "Expecting value: line 1 column 1 (char 0)". On force
        # donc le non-stream en amont ; OmniRoute refabrique le flux SSE cote client.
        body["stream"] = False
        body.pop("stream_options", None)

        print(f"[PROXY] {original} → {model}", flush=True)

        try:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                f"{NVIDIA_NIM_URL}/chat/completions",
                data=data,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {NVIDIA_API_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            self._respond(200, result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"[PROXY] NIM error {e.code}: {error_body[:200]}", flush=True)
            self._respond(e.code, json.loads(error_body) if error_body.startswith("{") else {"error": error_body})
        except Exception as e:
            self._respond(502, {"error": str(e)})

    def _forward_completions(self):
        """Forward /v1/completions (same prefix stripping)."""
        body = self._read_body()
        if not body:
            self._respond(400, {"error": "empty body"})
            return

        model = body.get("model", "")
        if "/" in model:
            parts = model.split("/", 1)
            if parts[0] in ("openai", "pollinations", "auto"):
                body["model"] = parts[1]

        # Meme raison que dans _forward_chat : le proxy ne sait pas relayer du SSE.
        body["stream"] = False
        body.pop("stream_options", None)

        try:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                f"{NVIDIA_NIM_URL}/completions",
                data=data,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {NVIDIA_API_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            self._respond(200, result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            self._respond(e.code, json.loads(error_body) if error_body.startswith("{") else {"error": error_body})
        except Exception as e:
            self._respond(502, {"error": str(e)})

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw)
        except Exception:
            return {}

    def _respond(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="NVIDIA NIM Proxy for OmniRoute")
    parser.add_argument("--port", type=int, default=20200)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # Load API key from .env if not set
    global NVIDIA_API_KEY
    if not NVIDIA_API_KEY:
        env_file = os.path.expanduser("~/AppData/Local/hermes/data/nvidia/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NVIDIA_API_KEY_GEMMA4="):
                        NVIDIA_API_KEY = line.split("=", 1)[1]
                        break

    if not NVIDIA_API_KEY:
        print("[ERROR] No NVIDIA API key found. Set NVIDIA_API_KEY or configure ~/AppData/Local/hermes/data/nvidia/.env")
        sys.exit(1)

    server = ThreadingHTTPServer((args.host, args.port), NIMProxyHandler)
    print(f"[NIM Proxy] Listening on {args.host}:{args.port}")
    print(f"[NIM Proxy] Upstream: {NVIDIA_NIM_URL}")
    # Ne JAMAIS journaliser la cle : ce log est un fichier en clair sur disque.
    print("[NIM Proxy] API key: nvapi-***")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[NIM Proxy] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
