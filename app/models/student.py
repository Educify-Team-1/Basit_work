from pydantic import BaseModel, Field
from typing import List, Optional


class TimeSlot(BaseModel):
    day: str
    start_time: str
    end_time: str


class Student(BaseModel):
    id: str
    name: str
    email: str
    subjects_needed: List[str]
    budget: float = Field(gt=0, description="Budget per hour")
    availability: List[TimeSlot]
    preferred_learning_style: Optional[str] = None
    current_level: Optional[str] = None
