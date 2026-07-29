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

        # Redis for endpoint caching
        self.cache = Cache.REDIS(
            endpoint=settings.redis_host,
            port=settings.redis_port,
            namespace="stats"
        )


        # Redis for rate limiting
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
    # BUILD CACHE KEY FOR /api/stats
    # ---------------------------------------------------------
    def build_stats_cache_key(self, request: Request) -> str | None:
        if not settings.enable_cache:
            return None

        # Only cache GET requests
        if request.method != "GET":
            return None

        path = request.url.path  # e.g. "/api/stats"

        # Extract query parameters
        params = request.query_params

        # If no params → no cache key
        if not params:
            return None

        # Build sorted param list to avoid ordering issues
        # Example: ["ticker=AAPL", "start=2023-01-01", "end=2023-12-31"]
        parts = []
        for key in sorted(params.keys()):
            value = params.get(key)
            if value is None:
                continue
            parts.append(value)

        # If still empty → no cache
        if not parts:
            return None

        # Final cache key format:
        # "/api/stats:AAPL:2023-01-01:2023-12-31"
        return f"{path}:" + ":".join(parts)


    # ---------------------------------------------------------
    # CACHING: GET cached response
    # ---------------------------------------------------------
    async def get_cached_response(self, cache_key: str | None) -> Response | None:
        if not cache_key:
            return None

        cached_value = await self.cache.get(cache_key)
        if cached_value:
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
    # Helpers
    # ---------------------------------------------------------

    async def extract_cache(self, start: float, cached: Response):
        duration = round((time.time() - start) * 1000, 2)

        cached_body = json.loads(cached.body.decode())
        cached_body["latency_ms"] = duration

        return Response(
            content=json.dumps(cached_body),
            media_type="application/json",
            status_code=200,
        )


    async def extract_body(self, response, start, cache_key):
        # Read the body from the response stream
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        duration = round((time.time() - start) * 1000, 2)

        # Always produce valid JSON
        try:
            payload = json.loads(body.decode())
        except Exception:
            # Fallback: wrap raw text in JSON
            payload = {"data": body.decode()}

        payload["latency_ms"] = duration

        # Store original response (without latency) in cache
        if cache_key:
            await self.store_cached_response(cache_key, body.decode())

        # Return JSON response
        return Response(
            content=json.dumps(payload),
            media_type="application/json",
            status_code=response.status_code,
        )


        

    # ---------------------------------------------------------
    # MAIN DISPATCH
    # ---------------------------------------------------------
    async def dispatch(self, request: Request, call_next):
        # Rate limiting
        rl = await self.rate_limit(request)
        if rl:
            return rl

        start = time.time()
        cache_key = self.build_stats_cache_key(request)

        # Try cache
        cached = await self.get_cached_response(cache_key)
        if cached:
            return await self.extract_cache(start, cached)

        # Process request normally
        response = await call_next(request)

        # Extract body + add latency + store cache 
        return await self.extract_body(response, start, cache_key)

