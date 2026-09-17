# -*- coding: utf-8 -*-
"""Upload a file to gofile.io and print the share link. Stdlib only (no requests).

Usage:
    python gofile_upload.py <file> [<output_name>]

Example:
    python gofile_upload.py resultat_final_v4.mp4
    # -> https://gofile.io/d/XXXX

gofile links expire after a few days (free tier). Use for videos > 50 MB (Telegram
upload cap) when the user is remote and can't use SwissTransfer's browser flow.
"""
import json, sys, urllib.request, urllib.error


def upload(path, filename=None):
    filename = filename or path.replace("\\", "/").split("/")[-1]

    # 1. pick an eu-zone server (gofile rotates hostnames)
    with urllib.request.urlopen("https://api.gofile.io/servers", timeout=30) as r:
        servers = json.loads(r.read())["data"]["servers"]
    srv = next((s for s in servers if s.get("zone") == "eu"), servers[0])["name"]

    # 2. multipart upload (hand-rolled boundary — no requests dependency)
    boundary = "----HermesUploadBoundary123456"
    with open(path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://{srv}.gofile.io/contents/uploadfile",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read())
    if resp.get("status") != "ok":
        raise RuntimeError(f"gofile upload failed: {resp}")
    return resp["data"]["downloadPage"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python gofile_upload.py <file> [<output_name>]")
    link = upload(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(link)
