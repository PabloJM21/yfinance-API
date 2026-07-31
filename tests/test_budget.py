import requests
import time
from app.config import get_settings

settings = get_settings()

MAX_MEMORY = 200

def test_budget():
    time.sleep(3)

    r = requests.get(settings.backend_url + "/memory")
    mem_mb = r.json().get("mem_mb")

    print(f"MEMORY_USAGE={mem_mb}")  

    assert mem_mb < MAX_MEMORY, f"Memory usage too high: {mem_mb:.2f} MB"
