import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from aiocache import Cache

from app.config import get_settings

settings = get_settings()


class Middleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        # aiocache Redis backend (matches DEV article)
        self.cache = Cache.REDIS(
            endpoint=settings.redis_host,
            port=settings.redis_port,
            namespace="stats"
        )

        # separate namespace for rate limiting
        self.ratelimit_cache = Cache.REDIS(
            endpoint=settings.redis_host,
            port=settings.redis_port,
            namespace="ratelimit"
        )

    # ---------------------------------------------------------
    # RATE LIMITING
    # ---------------------------------------------------------
    async def rate_limit(self, request: Request) -> Response | None:
        client_ip = request.client.host

        bucket_key = f"ip:{client_ip}"
        limit = settings.rate_limit_per_minute

        current = await self.ratelimit_cache.get(bucket_key)
        current = int(current) if current else 0

        if current >= limit:
            return Response(
                content=json.dumps({"detail": "Rate limit exceeded"}),
                status_code=429,
                media_type="application/json",
            )

        await self.ratelimit_cache.set(bucket_key, current + 1, ttl=60)
        return None

    # ---------------------------------------------------------
    # LOGGING
    # ---------------------------------------------------------
    def log_request_start(self, request: Request):
        print(json.dumps({
            "event": "request_start",
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
            "api_key_used": bool(request.headers.get("X-API-Key")),
        }))

    def log_request_end(self, request: Request, response: Response, duration_ms: float):
        print(json.dumps({
            "event": "request_end",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host,
        }))



    # ---------------------------------------------------------
    # BUILD CACHE KEY FOR /api/stats
    # ---------------------------------------------------------
    def build_stats_cache_key(self, request: Request) -> str | None:
        if not settings.enable_cache:
            return None

        if request.method != "GET":
            return None

        if request.url.path != "/api/stats":
            return None

        params = request.query_params

        ticker = params.get("ticker")
        start = params.get("start")
        end = params.get("end")

        if not ticker or not start or not end:
            return None

        return f"{ticker}:{start}:{end}"

    # ---------------------------------------------------------
    # CACHING: GET cached response
    # ---------------------------------------------------------
    async def get_cached_response(self, cache_key: str | None) -> Response | None:
        if not cache_key:
            return None

        cached_value = await self.cache.get(cache_key)
        if cached_value:
            print(json.dumps({
                "event": "cache_hit",
                "cache_key": cache_key,
            }))
            return Response(
                content=cached_value,
                media_type="application/json",
                status_code=200,
            )

        return None

    # ---------------------------------------------------------
    # CACHING: store response
    # ---------------------------------------------------------
    async def store_cached_response(self, cache_key: str | None, body: str):
        if not cache_key or not settings.enable_cache:
            return

        await self.cache.set(cache_key, body, ttl=settings.cache_ttl_seconds)


    # ---------------------------------------------------------
    # MAIN DISPATCH
    # ---------------------------------------------------------
    async def dispatch(self, request: Request, call_next):
        # Rate limiting
        rl = await self.rate_limit(request)
        if rl:
            return rl

        start = time.time()
        self.log_request_start(request)

        cache_key = self.build_stats_cache_key(request)

        # Try cache
        cached = await self.get_cached_response(cache_key)
        if cached:
            duration = round((time.time() - start) * 1000, 2)
            self.log_request_end(request, cached, duration)
            return cached

        # Process request
        response = await call_next(request)

        # Capture body from StreamingResponse
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Restore body iterator with async generator
        async def new_body_iterator():
            yield body

        response.body_iterator = new_body_iterator()

        # Store in cache
        await self.store_cached_response(cache_key, body.decode())

        duration = round((time.time() - start) * 1000, 2)
        self.log_request_end(request, response, duration)

        return response


