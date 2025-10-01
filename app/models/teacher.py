from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.student import TimeSlot

class Teacher(BaseModel):
    id: str
    name: str
    email: str
    subjects: List[str]
    hourly_rate: float = Field(gt=0)
    rating: float = Field(ge=0, le=5)
    total_reviews: int = Field(ge=0)
    availability: List[TimeSlot]
    experience_years: int = Field(ge=0)
    bio: Optional[str] = None
    teaching_style: Optional[str] = None
    certifications: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "T001",
                "name": "Jane Smith",
                "email": "jane@example.com",
                "subjects": ["Mathematics", "Calculus"],
                "hourly_rate": 45.0,
                "rating": 4.8,
                "total_reviews": 120,
                "availability": [
                    {"day": "Monday", "start_time": "10:00", "end_time": "20:00"}
                ],
                "experience_years": 5
            }
        }

