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
    """
    Match a student to the best teachers
    
    Returns top 3 matches by default (configurable)
    """
    try:
        # Get student data
        student = await data_service.get_student(request.student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {request.student_id} not found")
        
        # Verify subject is in student's needed subjects
        if request.subject not in student.subjects_needed:
            raise HTTPException(
                status_code=400, 
                detail=f"Subject {request.subject} not in student's requested subjects"
            )
        
        # Get all eligible teachers
        teachers = await data_service.get_all_teachers(
            subject=request.subject,
            max_rate=student.budget
        )
        
        # Find matches
        matches = matching_service.find_matches(student, teachers, request.subject)
        
        logger.info(f"Match request completed: {matches.total_matches} matches found")
        return matches
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in match endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teachers", response_model=List[Teacher])
async def get_teachers(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    max_rate: Optional[float] = Query(None, gt=0, description="Maximum hourly rate")
):
    """Get all teachers with optional filters"""
    try:
        teachers = await data_service.get_all_teachers(
            subject=subject,
            min_rating=min_rating,
            max_rate=max_rate
        )
        return teachers
    except Exception as e:
        logger.error(f"Error fetching teachers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    """Get student profile by ID"""
    try:
        student = await data_service.get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "student-teacher-matching"}

