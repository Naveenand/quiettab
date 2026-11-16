"""Front door of the QuietTab server: only the plugin gets in.

Think of it as a doorman with four rules:
  1. Host must be 127.0.0.1 or localhost   -> stops DNS rebinding (a web page pretending to be "localhost")
  2. No browser Origin header               -> stops any web page that reaches us anyway
  3. Secret token in X-QuietTab-Token       -> stops other programs / users on this machine
  4. Body size limit                        -> stops memory/GPU flooding

/health stays open (no token) so the plugin can check WHO is listening before it sends code:
it sends a random nonce, and only the real server (which knows the token) can answer with
HMAC(token, nonce). A program squatting on port 8000 can't.
"""
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

TOKEN_FILE = Path(os.environ.get("QT_TOKEN_FILE", Path.home() / ".quiettab" / "token"))
ALLOWED_HOSTS = {h.strip() for h in os.environ.get("QT_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")}
OPEN_PATHS = {"/health"}
MAX_BODY = {"/log": 64 * 1024}      # one event: a suggestion + numbers, never big
DEFAULT_MAX_BODY = 256 * 1024       # /complete: 8k prefix + 4k suffix + 8 x 4k extras, with JSON escaping


def load_or_create_token(path: Path = TOKEN_FILE) -> str:
    """Read the token, or make a new random one the first time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not path.read_text().strip():
        path.write_text(secrets.token_urlsafe(32))
        try:
            os.chmod(path, 0o600)       # only you can read it (no effect on /mnt/c, Windows ACLs apply there)
        except OSError:
            pass
    return path.read_text().strip()


def proof(token: str, nonce: str) -> str:
    """What the real server answers on /health: HMAC-SHA256(token, nonce) in hex."""
    return hmac.new(token.encode(), nonce.encode()[:128], hashlib.sha256).hexdigest()


class Guard:
    """Plain ASGI middleware: runs before FastAPI reads or parses anything."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}

        async def reject(status: int, reason: str):
            body = json.dumps({"error": reason}).encode()
            await send({"type": "http.response.start", "status": status,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})

        host = headers.get("host", "").rsplit(":", 1)[0].strip("[]")
        if host not in ALLOWED_HOSTS:
            return await reject(400, "bad host")
        if "origin" in headers:                       # browsers add Origin to cross-site requests; the plugin never does
            return await reject(403, "browser requests not allowed")
        path = scope["path"]
        if path not in OPEN_PATHS and not hmac.compare_digest(headers.get("x-quiettab-token", ""), self.token):
            return await reject(401, "missing or wrong token")

        limit = MAX_BODY.get(path, DEFAULT_MAX_BODY)
        try:
            if int(headers.get("content-length") or 0) > limit:
                return await reject(413, "body too large")
        except ValueError:
            return await reject(400, "bad content-length")

        # Read the body ourselves so a sender without content-length (chunked) can't go past the limit either
        chunks, size, more = [], 0, True
        while more:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                return
            chunk = msg.get("body", b"")
            size += len(chunk)
            if size > limit:
                return await reject(413, "body too large")
            chunks.append(chunk)
            more = msg.get("more_body", False)
        body, replayed = b"".join(chunks), False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()                      # after the body: lets FastAPI notice a hang-up

        return await self.app(scope, replay, send)
