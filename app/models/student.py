from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time


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
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "S001",
                "name": "John Doe",
                "email": "john@example.com",
                "subjects_needed": ["Mathematics", "Physics"],
                "budget": 50.0,
                "availability": [
                    {"day": "Monday", "start_time": "14:00", "end_time": "18:00"}
                ]
            }
        }
