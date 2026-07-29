import requests
import threading
import time
from plot_scripts.plot_traffic import plot_traffic
from .query_functions import run_query, run_concurrent_queries
import psutil

MAX_MEMORY = 200


def test_stability():
    time.sleep(3)


    # Find the uvicorn process
    """uvicorn_procs = [
        p for p in psutil.process_iter(['name']) 
        if p.info['name'] and 'uvicorn' in p.info['name']
    ]
    assert uvicorn_procs, "Backend process not found"
    proc = uvicorn_procs[0]
    mem_mb = proc.memory_info().rss / (1024 * 1024)"""
    #print(f"Memory usage before: {mem_mb}")

    metrics = {
        "samples": [],          # list of detailed measurements
        "status_counts": {},    # aggregated status codes
        "count": 0,             # total requests
    }

    # Test STATS endpoint
    endpoint = "/stats"


    label = "10x small queries"
    params = {"ticker": "AAPL", "start": "2024-05-01", "end": "2024-05-10"}
    
    run_concurrent_queries(params, metrics, endpoint, label, number=10)


    # Test COMPANY endpoint
    endpoint = "/company"

    # Concurrent queries
    label = "10x small queries"
    params = {"ticker": "AAPL"}

    run_concurrent_queries(params, metrics, endpoint, label, number=10)


    # Test QUOTE endpoint
    endpoint = "/quote"

    # Concurrent queries
    label = "10x concurrent queries"
    params = {"ticker": "AAPL"}

    run_concurrent_queries(params, metrics, endpoint, label, number=10)


    #mem_mb = #proc.memory_info().rss / (1024 * 1024)
    #assert mem_mb < MAX_MEMORY, f"Memory usage too high: {mem_mb:.2f} MB"


    plot_traffic(metrics, "/tmp/concurrency_plot.png") #, mem_mb, MAX_MEMORY)