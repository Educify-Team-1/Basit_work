import json
from typing import List, Optional
from pathlib import Path
from app.models.student import Student
from app.models.teacher import Teacher
from app.core.logging import logger
from app.core.config import settings


class DataService:
    """Service for managing data access - abstracts data source"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
    
    async def get_student(self, student_id: str) -> Optional[Student]:
        """Get student by ID"""
        try:
            if settings.DATA_SOURCE == "local":
                return self._get_student_local(student_id)
            elif settings.DATA_SOURCE == "api":
                return await self._get_student_api(student_id)
            else:
                raise ValueError(f"Unsupported data source: {settings.DATA_SOURCE}")
        except Exception as e:
            logger.error(f"Error fetching student {student_id}: {e}")
            return None
    
    def _get_student_local(self, student_id: str) -> Optional[Student]:
        """Get student from local JSON file"""
        file_path = self.data_dir / "students.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            students_data = json.load(f)
        
        for student_data in students_data:
            if student_data['id'] == student_id:
                return Student(**student_data)
        return None
    
    async def _get_student_api(self, student_id: str) -> Optional[Student]:
        """Fetch student from external API (placeholder for future)"""
        # TODO: Implement API call using httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{settings.EXTERNAL_API_URL}/students/{student_id}")
        #     return Student(**response.json())
        raise NotImplementedError("API data source not yet implemented")
    
    async def get_all_teachers(self, 
                               subject: Optional[str] = None,
                               min_rating: Optional[float] = None,
                               max_rate: Optional[float] = None) -> List[Teacher]:
        """Get all teachers with optional filters"""
        try:
            if settings.DATA_SOURCE == "local":
                teachers = self._get_teachers_local()
            elif settings.DATA_SOURCE == "api":
                teachers = await self._get_teachers_api()
            else:
                raise ValueError(f"Unsupported data source: {settings.DATA_SOURCE}")
            
            # Apply filters
            if subject:
                teachers = [t for t in teachers if subject in t.subjects]
            if min_rating:
                teachers = [t for t in teachers if t.rating >= min_rating]
            if max_rate:
                teachers = [t for t in teachers if t.hourly_rate <= max_rate]
            
            return teachers
        except Exception as e:
            logger.error(f"Error fetching teachers: {e}")
            return []
    
    def _get_teachers_local(self) -> List[Teacher]:
        """Get teachers from local JSON file"""
        file_path = self.data_dir / "teachers.json"
        if not file_path.exists():
            return []
        
        with open(file_path, 'r') as f:
            teachers_data = json.load(f)
        
        return [Teacher(**t) for t in teachers_data]
    
    async def _get_teachers_api(self) -> List[Teacher]:
        """Fetch teachers from external API (placeholder for future)"""
        raise NotImplementedError("API data source not yet implemented")
