import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

EXCLUDED = {"/health", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        timestamps = self._requests[ip]
        timestamps[:] = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= self.max_requests:
            return Response(status_code=429, content="Too Many Requests")

        timestamps.append(now)
        return await call_next(request)
