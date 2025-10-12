import json
import httpx
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.models.student import Student, TimeSlot
from app.models.teacher import Teacher
from app.core.logging import logger
from app.core.config import settings


class DataService:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.base_url = "https://api.staging.educify.org/api/v1"
        self.timeout = 30.0
        self.api_key = settings.API_KEY if hasattr(settings, 'API_KEY') else None
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def get_student(self, student_id: str) -> Optional[Student]:
        try:
            if settings.DATA_SOURCE == "api":
                return await self._get_student_api(student_id)
            elif settings.DATA_SOURCE == "local":
                return self._get_student_local(student_id)
        except Exception as e:
            logger.error(f"Error fetching student {student_id}: {e}")
            if settings.DATA_SOURCE == "api":
                logger.info("Falling back to local data")
                return self._get_student_local(student_id)
            return None
    
    async def _get_student_api(self, student_id: str) -> Optional[Student]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/students/{student_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                student_data = response.json()
                logger.info(f"Fetched student {student_id} from API")
                transformed_data = self._transform_student_data(student_data)
                return Student(**transformed_data)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    def _transform_student_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        if "user" in api_data:
            user_data = api_data["user"]
            name = user_data.get("name", "")
            email = user_data.get("email", "")
        else:
            name = api_data.get("name", "")
            email = api_data.get("email", "")
        
        student_id = api_data.get("id") or api_data.get("_id") or api_data.get("studentId")
        subjects = api_data.get("subjects", [])
        if isinstance(subjects, str):
            subjects = [subjects]
        elif not subjects:
            subjects = ["General"]
        
        budget = float(api_data.get("budget") or api_data.get("maxHourlyRate") or 100)
        availability = self._transform_availability(api_data.get("availability", []))
        
        return {
            "id": str(student_id),
            "name": name,
            "email": email,
            "subjects_needed": subjects,
            "budget": budget,
            "availability": availability,
            "preferred_learning_style": api_data.get("learningStyle"),
            "current_level": api_data.get("level") or api_data.get("educationLevel")
        }
    
    def _transform_availability(self, api_availability: Any) -> List[TimeSlot]:
        if not api_availability:
            return [
                TimeSlot(day="Monday", start_time="09:00", end_time="17:00"),
                TimeSlot(day="Tuesday", start_time="09:00", end_time="17:00"),
                TimeSlot(day="Wednesday", start_time="09:00", end_time="17:00"),
                TimeSlot(day="Thursday", start_time="09:00", end_time="17:00"),
                TimeSlot(day="Friday", start_time="09:00", end_time="17:00"),
            ]
        
        if isinstance(api_availability, list):
            slots = []
            for slot in api_availability:
                try:
                    day = slot.get("day") or slot.get("dayOfWeek")
                    start = slot.get("startTime") or slot.get("start_time") or slot.get("start")
                    end = slot.get("endTime") or slot.get("end_time") or slot.get("end")
                    if day and start and end:
                        slots.append(TimeSlot(day=day, start_time=start, end_time=end))
                except Exception as e:
                    logger.warning(f"Failed to parse slot: {e}")
            return slots if slots else self._transform_availability(None)
        return self._transform_availability(None)
    
    def _get_student_local(self, student_id: str) -> Optional[Student]:
        file_path = self.data_dir / "students.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                students_data = json.load(f)
            for student_data in students_data:
                if student_data['id'] == student_id:
                    return Student(**student_data)
        except Exception as e:
            logger.error(f"Error reading local student: {e}")
        return None
    
    async def get_all_teachers(self, subject: Optional[str] = None,
                               location: Optional[str] = None,
                               min_rating: Optional[float] = None,
                               max_rate: Optional[float] = None) -> List[Teacher]:
        try:
            if settings.DATA_SOURCE == "api":
                teachers = await self._get_teachers_api(subject, location)
            elif settings.DATA_SOURCE == "local":
                teachers = self._get_teachers_local()
            
            if subject and settings.DATA_SOURCE == "local":
                teachers = [t for t in teachers if subject in t.subjects]
            if min_rating:
                teachers = [t for t in teachers if t.rating >= min_rating]
            if max_rate:
                teachers = [t for t in teachers if t.hourly_rate <= max_rate]
            return teachers
        except Exception as e:
            logger.error(f"Error fetching teachers: {e}")
            if settings.DATA_SOURCE == "api":
                return self._get_teachers_local()
            return []
    
    async def _get_teachers_api(self, subject: Optional[str] = None,
                                location: Optional[str] = None) -> List[Teacher]:
        try:
            params = {}
            if subject:
                params["subject"] = subject
            if location:
                params["location"] = location
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/teachers",
                    params=params,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                teachers_data = response.json()
                logger.info(f"Fetched teachers from API")
                
                if isinstance(teachers_data, dict):
                    if "data" in teachers_data:
                        teachers_data = teachers_data["data"]
                    elif "teachers" in teachers_data:
                        teachers_data = teachers_data["teachers"]
                
                if not isinstance(teachers_data, list):
                    return []
                
                teachers = []
                for teacher_data in teachers_data:
                    try:
                        transformed = self._transform_teacher_data(teacher_data)
                        teachers.append(Teacher(**transformed))
                    except Exception as e:
                        logger.warning(f"Failed to parse teacher: {e}")
                
                logger.info(f"Parsed {len(teachers)} teachers")
                return teachers
        except Exception as e:
            logger.error(f"Error fetching teachers: {e}")
            raise
    
    def _transform_teacher_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        if "user" in api_data:
            user_data = api_data["user"]
            name = user_data.get("name", "")
            email = user_data.get("email", "")
        else:
            name = api_data.get("name", "")
            email = api_data.get("email", "")
        
        teacher_id = api_data.get("id") or api_data.get("_id") or api_data.get("teacherId")
        subjects = api_data.get("subjects") or api_data.get("categories") or []
        if isinstance(subjects, str):
            subjects = [subjects]
        elif not subjects:
            subjects = ["General"]
        
        hourly_rate = float(api_data.get("hourlyRate") or api_data.get("rate") or 0)
        rating = float(api_data.get("rating") or 0)
        total_reviews = int(api_data.get("totalReviews") or api_data.get("reviewCount") or 0)
        experience_years = int(api_data.get("experienceYears") or api_data.get("experience") or 0)
        availability = self._transform_availability(api_data.get("availability", []))
        certifications = api_data.get("certifications") or []
        if isinstance(certifications, str):
            certifications = [certifications]
        
        return {
            "id": str(teacher_id),
            "name": name,
            "email": email,
            "subjects": subjects,
            "hourly_rate": hourly_rate,
            "rating": rating,
            "total_reviews": total_reviews,
            "availability": availability,
            "experience_years": experience_years,
            "bio": api_data.get("bio"),
            "teaching_style": api_data.get("teachingStyle"),
            "certifications": certifications
        }
    
    def _get_teachers_local(self) -> List[Teacher]:
        file_path = self.data_dir / "teachers.json"
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                teachers_data = json.load(f)
            return [Teacher(**t) for t in teachers_data]
        except Exception as e:
            logger.error(f"Error reading local teachers: {e}")
            return []
    
    async def send_booking(self, student_id: str, teacher_id: str,
                          lesson_details: Optional[Dict] = None) -> Dict[str, Any]:
        try:
            payload = {
                "booking": {
                    "studentId": student_id,
                    "teacherId": teacher_id,
                    "type": "WEEKLY",
                    "location": "online",
                    "subscription": False
                }
            }
            if lesson_details:
                payload["booking"].update(lesson_details)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/bookings",
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                logger.info(f"Created booking: student {student_id}, teacher {teacher_id}")
                return response.json()
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            raise

