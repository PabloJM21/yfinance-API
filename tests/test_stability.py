import requests
import threading
import time

BACKEND_URL = "https://stock-api.example.com/api/stats"

def run_query(params):
    r = requests.get(BACKEND_URL, params=params)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert data["ticker"] == params["ticker"]

def test_stability():
    time.sleep(3)

    # 1. Large query (heavy load)
    params = {"ticker": "AAPL", "start": "2020-01-01", "end": "2024-01-01"}
    run_query(params)

    # 2. Many concurrent smaller queries (simulate multiple clients)
    params_small = {"ticker": "AAPL", "start": "2024-05-01", "end": "2024-05-10"}

    threads = []
    for _ in range(10):  # 10 concurrent requests
        t = threading.Thread(target=run_query, args=(params_small,))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()
