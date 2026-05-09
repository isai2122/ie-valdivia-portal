"""Middleware: request_id + logging estructurado + latencia."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "request failed",
                extra={"request_id": rid, "method": request.method, "path": request.url.path},
            )
            raise
        dt_ms = round((time.perf_counter() - t0) * 1000, 1)
        response.headers["x-request-id"] = rid
        log.info(
            "%s %s -> %s (%sms)",
            request.method, request.url.path, response.status_code, dt_ms,
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": dt_ms,
            },
        )
        return response
