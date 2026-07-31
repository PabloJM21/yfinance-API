import requests
import threading
import time
from plot_scripts.plot_traffic import plot_traffic
from app.config import get_settings

settings = get_settings()


def run_query(params, metrics, endpoint, label, with_memory=False):
    r = requests.get(settings.backend_url + endpoint, params=params)

    # Store detailed sample
    params_str = ", ".join(f"{k}={v}" for k, v in params.items())

    if label:
        new_label = f"{label}: {params_str}"
    else:
        new_label = params_str

    metrics["samples"].append({
        "endpoint": endpoint,
        "label": new_label, #{endpoint} 
        "latency_ms": r.json().get("latency_ms"), #duration_ms,
        "status": r.status_code,
    })


    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert all(data.get(k) == v for k, v in params.items())

    if with_memory:
        return r.json().get("rss_mb")





def run_concurrent_queries(params, metrics, endpoint, label, number):
    threads = []
    for _ in range(number):
        t = threading.Thread(target=run_query, args=(params, metrics, endpoint, label))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()






def test_stability():
    time.sleep(3)



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

    params = {"ticker": "AAPL"}

    run_concurrent_queries(params, metrics, endpoint, label, number=10)


    # Test QUOTE endpoint
    endpoint = "/quote"

    # Concurrent queries
    params = {"ticker": "AAPL"}

    run_concurrent_queries(params, metrics, endpoint, label, number=10)



    plot_traffic(metrics, "/artifacts/latency_plot.png") #, mem_mb, MAX_MEMORY)