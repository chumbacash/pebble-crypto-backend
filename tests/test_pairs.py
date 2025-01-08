from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_pairs():
    response = client.get("/pairs/")
    assert response.status_code == 200
    assert "pairs" in response.json()
