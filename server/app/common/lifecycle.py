from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class StoppingPolicy:
    """Prevent request dependencies from recreating resources during teardown."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        owner = scope.get("app")
        if scope["type"] == "http" and owner is not None and getattr(owner.state, "stopping", False):
            response = JSONResponse(
                {"detail": "A szerver leállítás alatt áll."}, status_code=503,
                headers={"Retry-After": "1", "Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
