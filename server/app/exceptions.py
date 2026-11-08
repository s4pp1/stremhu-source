from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.singleflight import SearchOverloadedError, SearchStoppingError
from app.modules.torznab.exceptions import (
    TorznabProtocolError,
    torznab_protocol_error_handler,
)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        msg = error.get("msg", str(error))
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "")
        messages.append(msg)

    return JSONResponse(
        status_code=422,
        content={"detail": "\n".join(messages)},
    )


def setup_exception_handlers(app: FastAPI):
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(TorznabProtocolError, torznab_protocol_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SearchStoppingError, search_stopping_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SearchOverloadedError, search_overloaded_handler)  # type: ignore[arg-type]


async def search_stopping_handler(request: Request, exc: SearchStoppingError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "A keresési szolgáltatás leállítás alatt áll."},
        headers={"Retry-After": "1", "Cache-Control": "no-store"},
    )


async def search_overloaded_handler(request: Request, exc: SearchOverloadedError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "A keresési szolgáltatás túlterhelt, próbáld újra később."},
        headers={"Retry-After": "2", "Cache-Control": "no-store"},
    )
