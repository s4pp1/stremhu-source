from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CapitalizeHeaderMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        if scope.get("http_version") not in ("1.0", "1.1"):
            return await self.app(scope, receive, send)

        async def send_wrapper(message: Message):
            if message["type"] == "http.response.start":
                header_map = {
                    b"content-length": b"Content-Length",
                    b"content-type": b"Content-Type",
                    b"content-range": b"Content-Range",
                    b"accept-ranges": b"Accept-Ranges",
                }

                message["headers"] = [
                    (header_map.get(name.lower(), name), value)
                    for name, value in message.get("headers", [])
                ]

            await send(message)

        await self.app(scope, receive, send_wrapper)
