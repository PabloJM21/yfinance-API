import requests
import threading
import time
from plot_scripts.plot_traffic import plot_traffic

BACKEND_URL = "http://backend:8080/api"
#BACKEND_URL = "http://localhost:8080/api"


def run_query(params, metrics, endpoint, label, with_memory=False):
    r = requests.get(BACKEND_URL + endpoint, params=params)

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




