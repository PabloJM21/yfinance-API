import psutil
import requests
import time

BACKEND_URL = "http://localhost:8080/api/stats"

def test_dependency_budget():
    # Give backend time to fully boot
    time.sleep(3)

    # Find the uvicorn process
    uvicorn_procs = [
        p for p in psutil.process_iter(['name']) 
        if p.info['name'] and 'uvicorn' in p.info['name']
    ]
    assert uvicorn_procs, "Backend process not found"
    proc = uvicorn_procs[0]

    # Trigger dependency loading (yfinance, pandas, redis client)
    response = requests.get(
        BACKEND_URL,
        params={"ticker": "AAPL", "start": "2024-01-01", "end": "2024-06-01"}
    )
    assert response.status_code == 200

    # Measure memory usage
    mem_mb = proc.memory_info().rss / (1024 * 1024)
    assert mem_mb < 200, f"Memory usage too high: {mem_mb:.2f} MB"
