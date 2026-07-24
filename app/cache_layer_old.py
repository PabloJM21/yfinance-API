import json
from functools import wraps
import pandas as pd
from fastapi import HTTPException
from datetime import datetime, timedelta
from redis.asyncio import Redis




"""
Per‑date caching:

- Check which dates exist
- Fetch only missing dates
- Merge cached + fresh data

Pros:

- Works well with Redis hashes
- Very efficient for short repeated queries, and incremental updates

Cons:

- More Redis calls (unless pipelined)
- Harder to invalidate if data changes

"""


async def get_cached_dates(redis: Redis, ticker: str):
    key = f"users:ticker:{ticker}"
    try:
        return await redis.hkeys(key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error caching data: {e}")






async def get_cached_data(redis: Redis, ticker: str, start: str, end: str):
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    key = f"users:ticker:{ticker}"

    try:
        raw = await redis.hmget(key, *dates)
        payloads = [json.loads(item) for item in raw if item]
        return payloads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cached data: {e}")



async def store_date_data(redis: Redis, ticker: str, date: str, data: dict, ttl_seconds: int):
    key = f"users:ticker:{ticker}"
    try:
        await redis.hset(key, date, json.dumps(data))
        await redis.expire(key, ttl_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error caching data: {e}")




def dissect_date_ranges(start: str, end: str, cached_dates: list[str]):
    cached = set(cached_dates)

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    ranges = []
    range_start = start_dt
    current_flag = "present" if start in cached else "missing"

    current = start_dt + timedelta(days=1)

    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        flag = "present" if date_str in cached else "missing"

        # If the flag changes, close the previous range
        if flag != current_flag:
            ranges.append((
                range_start.strftime("%Y-%m-%d"),
                (current - timedelta(days=1)).strftime("%Y-%m-%d"),
                current_flag
            ))
            range_start = current
            current_flag = flag

        current += timedelta(days=1)

    # Close final range
    ranges.append((
        range_start.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
        current_flag
    ))

    return ranges




async def cache_response_handler(func, cache, ticker, start, end, ttl_seconds):
    cached_dates = set(await get_cached_dates(cache, ticker))
    payloads = []

    for sub_start, sub_end, flag in dissect_date_ranges(start, end, cached_dates):

        if flag == "missing":
            fresh_payloads = await func(ticker=ticker, start=sub_start, end=sub_end)
            payloads.extend(fresh_payloads)

            for payload in fresh_payloads:
                await store_date_data(cache, ticker, payload["date"], payload, ttl_seconds)

        else:
            cached_payloads = await get_cached_data(cache, ticker, sub_start, sub_end)
            payloads.extend(cached_payloads)

    return payloads



