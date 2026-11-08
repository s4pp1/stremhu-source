from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def is_sensitive_response_path(path: str) -> bool:
    parts = path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "api":
        return False
    if parts[1] in {"auth", "me", "users", "playbacks"}:
        return True
    return len(parts) >= 3 and (
        parts[2] == "subtitles"
        or (len(parts) >= 4 and parts[2:4] == ["stremio", "subtitles"])
    )


class SensitiveResponsePolicy:
    """Set a response-start policy without buffering media or subtitle bytes."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not is_sensitive_response_path(scope["path"]):
            await self.app(scope, receive, send)
            return
        started = False

        async def sensitive_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message = dict(message)
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
            await send(message)

        try:
            await self.app(scope, receive, sensitive_send)
        except Exception:
            # ServerErrorMiddleware is outside user middleware. Preserve its
            # default response while ensuring its pre-start 500 is no-store too.
            if not started:
                await PlainTextResponse("Internal Server Error", status_code=500)(scope, receive, sensitive_send)
            raise
