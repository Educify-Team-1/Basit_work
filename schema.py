from typing import Literal
from pydantic import BaseModel


class StudentModel(BaseModel):
    """student data schema for the api"""
    user_id: str
    name: str
    email: str  # privacy concern
    phone: str  # privacy concern
    subject: str  # or subjects
    learning_style: str
    availability: str
    grade_level: str
    location_preference: Literal["in-person", "online", "hybrid"]
    location: str


class TeacherModel(BaseModel):
    """teacher data schema for the api"""
    user_id: str
    name: str
    email: str  # privacy concern
    phone: str  # privacy concern
    subject: str  # or subjects
    teaching_style: str
    schedule: str
    location_preference: Literal["in-person", "online", "hybrid"]
    travel_distance: int
    ratings: int
    reviews: str
