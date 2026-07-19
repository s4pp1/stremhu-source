import asyncio

from starlette.types import Message

from app.common.middleware import CapitalizeHeaderMiddleware


def test_capitalize_header_middleware_http1():
    async def run_test():
        sent_messages = []

        async def mock_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-length", b"123"),
                        (b"content-type", b"video/mp4"),
                        (b"content-range", b"bytes 0-122/123"),
                        (b"accept-ranges", b"bytes"),
                        (b"other-header", b"value"),
                    ],
                }
            )

        async def mock_receive() -> Message:
            return {"type": "http.request", "body": b""}

        async def mock_send(message: Message):
            sent_messages.append(message)

        middleware = CapitalizeHeaderMiddleware(mock_app)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        await middleware(scope, mock_receive, mock_send)

        assert len(sent_messages) == 1
        response_start = sent_messages[0]
        assert response_start["type"] == "http.response.start"

        headers = response_start["headers"]

        assert (b"Content-Length", b"123") in headers
        assert (b"Content-Type", b"video/mp4") in headers
        assert (b"Content-Range", b"bytes 0-122/123") in headers
        assert (b"Accept-Ranges", b"bytes") in headers
        assert (b"other-header", b"value") in headers

        header_names = [name for name, _ in headers]
        assert b"content-length" not in header_names
        assert b"content-type" not in header_names
        assert b"content-range" not in header_names
        assert b"accept-ranges" not in header_names

    asyncio.run(run_test())


def test_capitalize_header_middleware_ignores_http2():
    async def run_test():
        sent_messages = []

        async def mock_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-length", b"123"),
                    ],
                }
            )

        async def mock_receive() -> Message:
            return {"type": "http.request", "body": b""}

        async def mock_send(message: Message):
            sent_messages.append(message)

        middleware = CapitalizeHeaderMiddleware(mock_app)

        scope = {
            "type": "http",
            "http_version": "2",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        await middleware(scope, mock_receive, mock_send)

        assert len(sent_messages) == 1
        headers = sent_messages[0]["headers"]

        assert (b"content-length", b"123") in headers
        assert (b"Content-Length", b"123") not in headers

    asyncio.run(run_test())
