import requests
import threading
import time
from ..plot_scripts.plot_traffic import plot_traffic

BACKEND_URL = "http://backend:8080/api"


def run_query(params, metrics, endpoint):
    start = time.time()
    r = requests.get(BACKEND_URL + endpoint, params=params)
    duration_ms = (time.time() - start) * 1000

    # Store detailed sample
    metrics["samples"].append({
        "endpoint": endpoint,
        "params": params,
        "latency_ms": duration_ms,
        "status": r.status_code,
    })

    # Aggregate stats
    metrics["status_counts"][str(r.status_code)] = (
        metrics["status_counts"].get(str(r.status_code), 0) + 1
    )
    metrics["count"] += 1

    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert data["ticker"] == params["ticker"]


def test_stability():
    time.sleep(3)

    metrics = {
        "samples": [],          # list of detailed measurements
        "status_counts": {},    # aggregated status codes
        "count": 0,             # total requests
    }

    # Test STATS endpoint
    endpoint = "/stats"

    # Heavy query
    params = {"ticker": "AAPL", "start": "2020-01-01", "end": "2024-01-01"}
    run_query(params, metrics, endpoint)

    # Concurrent queries
    params_small = {"ticker": "AAPL", "start": "2024-05-01", "end": "2024-05-10"}

    threads = []
    for _ in range(10):
        t = threading.Thread(target=run_query, args=(params_small, metrics, endpoint))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Generate plot directly
    plot_traffic(metrics, "/tmp/traffic_plot.png")
