import pytest
from app.services.matching_service import MatchingService
from app.models.student import Student, TimeSlot
from app.models.teacher import Teacher


@pytest.fixture
def matching_service():
    return MatchingService()


@pytest.fixture
def sample_student():
    return Student(
        id="S001",
        name="Test Student",
        email="test@example.com",
        subjects_needed=["Mathematics"],
        budget=50.0,
        availability=[
            TimeSlot(day="Monday", start_time="14:00", end_time="18:00")
        ]
    )


@pytest.fixture
def sample_teachers():
    return [
        Teacher(
            id="T001",
            name="Teacher One",
            email="t1@example.com",
            subjects=["Mathematics"],
            hourly_rate=45.0,
            rating=4.8,
            total_reviews=100,
            availability=[
                TimeSlot(day="Monday", start_time="10:00", end_time="20:00")
            ],
            experience_years=5
        ),
        Teacher(
            id="T002",
            name="Teacher Two",
            email="t2@example.com",
            subjects=["Mathematics"],
            hourly_rate=60.0,  # Over budget
            rating=4.9,
            total_reviews=150,
            availability=[
                TimeSlot(day="Monday", start_time="10:00", end_time="20:00")
            ],
            experience_years=10
        )
    ]


def test_filter_by_subject(matching_service, sample_teachers):
    result = matching_service._filter_by_subject(sample_teachers, "Mathematics")
    assert len(result) == 2


def test_filter_by_budget(matching_service, sample_teachers):
    result = matching_service._filter_by_budget(sample_teachers, 50.0)
    assert len(result) == 1
    assert result[0].id == "T001"


def test_find_matches_success(matching_service, sample_student, sample_teachers):
    response = matching_service.find_matches(
        sample_student, 
        sample_teachers, 
        "Mathematics"
    )
    assert response.success is True
    assert response.total_matches >= 1
    assert response.matches[0].teacher.id == "T001"


def test_find_matches_no_budget(matching_service, sample_student, sample_teachers):
    sample_student.budget = 30.0  # Below all teachers
    response = matching_service.find_matches(
        sample_student,
        sample_teachers,
        "Mathematics"
    )
    assert response.success is False
    assert "budget" in response.message.lower()