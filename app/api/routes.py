from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.match import MatchRequest, MatchResponse
from app.models.teacher import Teacher
from app.models.student import Student
from app.services.data_service import DataService
from app.services.matching_service import MatchingService
from app.core.logging import logger

router = APIRouter()
data_service = DataService()
matching_service = MatchingService()


@router.post("/match", response_model=MatchResponse)
async def match_student_to_teachers(request: MatchRequest):
    try:
        student = await data_service.get_student(request.student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {request.student_id} not found")
        
        location = getattr(student, 'location', None)
        teachers = await data_service.get_all_teachers(
            subject=request.subject,
            location=location,
            max_rate=student.budget
        )
        
        if not teachers:
            raise HTTPException(status_code=404, detail="No teachers found")
        
        matches = matching_service.find_matches(student, teachers, request.subject)
        
        if matches.success and matches.matches:
            try:
                best_teacher = matches.matches[0].teacher
                await data_service.send_booking(request.student_id, best_teacher.id)
                logger.info(f"Booking created for top match")
            except Exception as e:
                logger.error(f"Failed to create booking: {e}")
        
        return matches
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in match endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teachers", response_model=List[Teacher])
async def get_teachers(
    subject: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_rate: Optional[float] = Query(None, gt=0)
):
    try:
        teachers = await data_service.get_all_teachers(
            subject=subject, location=location,
            min_rating=min_rating, max_rate=max_rate
        )
        return teachers
    except Exception as e:
        logger.error(f"Error fetching teachers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    try:
        student = await data_service.get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student not found")
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "matching", "data_source": settings.DATA_SOURCE}
