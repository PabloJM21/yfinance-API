# tests/test_stability.py
import requests
import threading
import time

BACKEND_URL = "http://localhost:8080/api/stats"

def run_query(params):
    r = requests.get(
        BACKEND_URL,
        params=params
    )
    assert r.status_code == 200
    assert "results" in r.json()


def test_stability():
    # Give backend time to fully boot
    time.sleep(3)

    # 1. Large query (heavy load)
    params={"ticker": "AAPL", "start": "2020-01-01", "end": "2024-01-01"}
    run_query(params)

    # 2. Two concurrent smaller queries
    params = {"ticker": "AAPL", "start": "2024-05-01", "end": "2024-05-10"}
    t1 = threading.Thread(target=run_query(params))
    t2 = threading.Thread(target=run_query(params))

    # Run both API calls concurrently
    t1.start()
    t2.start()

    # Wait for both API calls to complete
    t1.join()
    t2.join()
