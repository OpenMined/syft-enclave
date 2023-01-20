import requests

FASTAPI_PORT = 7777


def test_message():
    res = requests.get(f"http://localhost:{FASTAPI_PORT}")
    assert res.status_code == 200
    assert res.json()["message"] == "FastAPI service running"
