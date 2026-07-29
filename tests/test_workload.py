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

    # Progresively larger queries
    label = None
    params = {"ticker": "AAPL", "start": "2024-01-01", "end": "2025-01-01"}
    run_query(params, metrics, endpoint, label)
    params = {"ticker": "AAPL", "start": "2023-01-01", "end": "2025-01-01"}
    run_query(params, metrics, endpoint, label)
    params = {"ticker": "AAPL", "start": "2022-01-01", "end": "2025-01-01"}
    run_query(params, metrics, endpoint, label)
    params = {"ticker": "AAPL", "start": "2021-01-01", "end": "2025-01-01"}
    mem_mb = run_query(params, metrics, endpoint, label, with_memory=True)

    

    assert mem_mb < MAX_MEMORY, f"Memory usage too high: {mem_mb:.2f} MB"


    # Generate plot directly
    #print("plot_traffic called, saving to:", "/tmp/traffic_plot.png")

    plot_traffic(metrics, "/artifacts/workload_plot.png", mem_mb, MAX_MEMORY)