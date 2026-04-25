import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000)
            logger.info(
                "request finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000)
            logger.error(
                "request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise
