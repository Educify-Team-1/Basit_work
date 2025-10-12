import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_teachers():
    response = client.get("/api/v1/teachers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_teachers_with_filters():
    response = client.get("/api/v1/teachers?subject=Mathematics&min_rating=4.5")
    assert response.status_code == 200