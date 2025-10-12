from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.teacher import Teacher
from app.models.student import TimeSlot


class MatchScore(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    rating_score: float
    availability_score: float
    subject_match: bool
    budget_match: bool


class TeacherMatch(BaseModel):
    teacher: Teacher
    score: MatchScore
    matching_subjects: List[str]
    matching_time_slots: List[TimeSlot]
    recommended_reason: str


class MatchRequest(BaseModel):
    student_id: str
    subject: str
    preferred_time_slots: Optional[List[TimeSlot]] = None


class MatchResponse(BaseModel):
    success: bool
    student_id: str
    subject: str
    matches: List[TeacherMatch]
    total_matches: int
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None
