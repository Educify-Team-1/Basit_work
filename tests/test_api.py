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
    teachers = response.json()
    for teacher in teachers:
        assert "Mathematics" in teacher["subjects"]
        assert teacher["rating"] >= 4.5


def test_match_endpoint():
    match_request = {
        "student_id": "S001",
        "subject": "Mathematics"
    }
    response = client.post("/api/v1/match", json=match_request)
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert data["success"] is True or data["success"] is False