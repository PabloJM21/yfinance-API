import os
from fastapi import FastAPI
import yfinance as yf
from functools import wraps
from .config import ENABLE_CACHE
from .cache_layer_old import cache_response_handler
import time

os.makedirs("/tmp/yfinance-cache", exist_ok=True)
yf.set_tz_cache_location("/tmp/yfinance-cache")

app = FastAPI()


def cache_response(ttl_seconds: int = 60, namespace: str = "users"):

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            ticker = kwargs["ticker"]
            start = kwargs["start"]
            end = kwargs["end"]

            # CASE 1: caching disabled → call endpoint directly
            if not ENABLE_CACHE:
                call_start = time.time()
                fresh_payloads = await func(*args, **kwargs)
                call_end = time.time()
                elapsed = round(call_end - call_start, 2)
                return {
                    "ticker": ticker,
                    "start": start,
                    "end": end,
                    "latency (s)": elapsed, 
                    "results": fresh_payloads
                }

            # CASE 2: caching enabled → delegate to caching handler if available
            try:
                #from aiocache import Cache
                #cache = Cache(Cache.REDIS, endpoint="redis", port=6379, namespace=namespace)
                from redis.asyncio import Redis

                redis = Redis(
                    host="redis",
                    port=6379,
                    decode_responses=True  # ensures JSON strings come back as str, not bytes
                )

                call_start = time.time()
                payloads = await cache_response_handler(func, redis, ticker, start, end, ttl_seconds)
                call_end = time.time()
                elapsed = round(call_end - call_start, 2)


            except Exception as e:
                print(f"Caching not possible: {e}")
                call_start = time.time()
                payloads = await func(ticker=ticker, start=start, end=end)
                call_end = time.time()
                elapsed = round(call_end - call_start, 2)

            return {
                "ticker": ticker,
                "start": start,
                "end": end,
                "latency (s)": elapsed, 
                "results": payloads
            }

        return wrapper
    return decorator


@app.get("/api/stats")
@cache_response(ttl_seconds=120, namespace="users")
async def get_stock_data(ticker: str, start: str, end: str):
    stock = yf.Ticker(ticker)
    data = stock.history(start=start, end=end)

    results = []
    for date, row in data.iterrows():
        date_str = date.strftime("%Y-%m-%d")
        results.append({
            "date": date_str,
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume": int(row["Volume"]),
            "average": (row["Open"] + row["High"] + row["Low"] + row["Close"]) / 4
        })

    return results
