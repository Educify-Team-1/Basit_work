# API Service Layer for Teacher-Student Matching
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import pandas as pd
import uvicorn
from contextlib import asynccontextmanager
import logging
import os
from prometheus_client import Counter, Histogram, generate_latest
from matcher import MatchingEngine, Student, Teacher
import time


# Metrics
MATCH_REQUESTS = Counter('matching_requests_total', 'Total matching requests')
MATCH_DURATION = Histogram('matching_duration_seconds', 'Time spent on matching')
MATCH_SUCCESS = Counter('matching_success_total', 'Successful matches')

# Pydantic models for API
class StudentRequest(BaseModel):
    id: str
    subjects: List[str]
    learning_style: str
    availability: List[str]
    location_preference: str
    budget_range: List[float]
    experience_level: str
    preferred_teacher_gender: Optional[str] = None
    age: int = 0

class TeacherResponse(BaseModel):
    id: str
    subjects: List[str]
    teaching_style: str
    availability: List[str]
    location_preference: str
    hourly_rate: float
    experience_years: int
    rating: float
    total_students: int
    specializations: List[str]
    gender: str
    languages: List[str]

class MatchResponse(BaseModel):
    teacher_id: str
    student_id: str
    compatibility_score: float
    confidence: float
    reasons: List[str]
    teacher_details: TeacherResponse

class FeedbackRequest(BaseModel):
    student_id: str
    teacher_id: str
    rating: float
    lesson_completed: bool
    feedback_text: Optional[str] = None

class BatchMatchRequest(BaseModel):
    students: List[StudentRequest]
    max_matches_per_student: int = 5

# Global variables
matching_engine = None
teacher_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    global matching_engine, teacher_cache
    
    # Initialize matching engine
    matching_engine = MatchingEngine()
    
    # Load teachers from database (mock data for example)
    teacher_cache = await load_teachers_from_db()
    
    # Train model with historical data
    interaction_data = await load_interaction_data()
    if not interaction_data.empty:
        matching_engine.train(interaction_data)
    
    logging.info("Matching service initialized successfully")
    yield
    
    # Cleanup
    logging.info("Shutting down matching service")

app = FastAPI(
    title="AI Teacher-Student Matching Service",
    description="Intelligent matching service for connecting students with suitable teachers",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "teachers_loaded": len(teacher_cache) if teacher_cache else 0,  # Fixed this line
        "model_ready": matching_engine is not None
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.post("/match", response_model=List[MatchResponse])
async def find_matches(student_request: StudentRequest, top_k: int = 10):
    """Find matching teachers for a student"""
    MATCH_REQUESTS.inc()
    start_time = time.time()
    
    try:
        # Convert request to internal format
        student = Student(
            id=student_request.id,
            subjects=student_request.subjects,
            learning_style=student_request.learning_style,
            availability=student_request.availability,
            location_preference=student_request.location_preference,
            budget_range=tuple(student_request.budget_range),
            experience_level=student_request.experience_level,
            preferred_teacher_gender=student_request.preferred_teacher_gender,
            age=student_request.age
        )
        
        # Get available teachers
        teachers = list(teacher_cache.values())
        
        # Find matches
        matches = matching_engine.find_matches(student, teachers, top_k)
        
        # Convert to response format
        response_matches = []
        for match in matches:
            teacher = teacher_cache[match.teacher_id]
            teacher_response = TeacherResponse(
                id=teacher.id,
                subjects=teacher.subjects,
                teaching_style=teacher.teaching_style,
                availability=teacher.availability,
                location_preference=teacher.location_preference,
                hourly_rate=teacher.hourly_rate,
                experience_years=teacher.experience_years,
                rating=teacher.rating,
                total_students=teacher.total_students,
                specializations=teacher.specializations,
                gender=teacher.gender,
                languages=teacher.languages
            )
            
            response_matches.append(MatchResponse(
                teacher_id=match.teacher_id,
                student_id=match.student_id,
                compatibility_score=match.compatibility_score,
                confidence=match.confidence,
                reasons=match.reasons,
                teacher_details=teacher_response
            ))
        
        MATCH_SUCCESS.inc()
        MATCH_DURATION.observe(time.time() - start_time)
        
        return response_matches
        
    except Exception as e:
        logger.error(f"Error in matching: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/batch-match")
async def batch_match(request: BatchMatchRequest):
    """Process multiple student matching requests"""
    results = {}
    
    for student_request in request.students:
        try:
            matches = await find_matches(student_request, request.max_matches_per_student)
            results[student_request.id] = matches
        except Exception as e:
            logger.error(f"Error matching student {student_request.id}: {str(e)}")
            results[student_request.id] = {"error": str(e)}
    
    return {"results": results, "total_processed": len(request.students)}

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, background_tasks: BackgroundTasks):
    """Submit feedback for a teacher-student interaction"""
    try:
        # Update matching engine with feedback
        matching_engine.update_feedback(
            feedback.student_id,
            feedback.teacher_id,
            feedback.rating,
            feedback.lesson_completed
        )
        
        # Schedule background task to retrain model if needed
        background_tasks.add_task(check_retrain_trigger)
        
        return {"message": "Feedback recorded successfully"}
        
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")

@app.get("/teacher/{teacher_id}/stats")
async def get_teacher_stats(teacher_id: str):
    """Get statistics for a specific teacher"""
    if teacher_id not in teacher_cache:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    teacher = teacher_cache[teacher_id]
    
    # Calculate additional stats (mock data)
    stats = {
        "teacher_id": teacher_id,
        "rating": teacher.rating,
        "total_students": teacher.total_students,
        "experience_years": teacher.experience_years,
        "subjects": teacher.subjects,
        "match_success_rate": 0.85,  # Would calculate from real data
        "avg_lesson_duration": 55,   # minutes
        "response_time": 2.3         # hours
    }
    
    return stats

@app.get("/student/{student_id}/recommendations")
async def get_student_recommendations(student_id: str):
    """Get personalized teacher recommendations for a student"""
    # This would typically load student data from database
    # For demo, return mock recommendations
    return {
        "student_id": student_id,
        "recommended_subjects": ["math", "physics"],
        "suggested_session_length": 60,
        "optimal_time_slots": ["evening"],
        "learning_tips": [
            "Consider visual learning materials",
            "Practice problems work best for you",
            "Short breaks improve retention"
        ]
    }

# Add this endpoint to app.py
@app.post("/generate-api-key")
async def generate_api_key(team_name: str):
    import secrets
    api_key = f"mk_{secrets.token_urlsafe(32)}"
    # Store in database with team_name
    return {"api_key": api_key, "team": team_name}


# Background tasks
async def check_retrain_trigger():
    """Check if model needs retraining based on feedback volume"""
    # Mock implementation - would check feedback count/time since last training
    feedback_count = 100  # Would get from Redis/DB
    last_train_time = time.time() - 86400  # 24 hours ago
    
    if feedback_count > 50 and (time.time() - last_train_time) > 86400:
        logger.info("Triggering model retraining...")
        # Would trigger async model retraining job

def is_valid_api_key(api_key: str) -> bool:
    """Validate API key - mock implementation for development"""
    # For development, accept any key that starts with 'mk_'
    # In production, this would check against a database
    if not api_key or not isinstance(api_key, str):
        return False
    return api_key.startswith('mk_') and len(api_key) > 10

async def verify_api_key(x_api_key: str = Header(...)):
    # Verify API key from database
    if not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
        
async def load_teachers_from_db():
    """Load teachers from database - mock implementation"""
    # Mock teacher data
    mock_teachers = {
        "t1": Teacher(
            id="t1",
            subjects=["math", "algebra", "calculus"],
            teaching_style="visual",
            availability=["morning", "afternoon"],
            location_preference="online",
            hourly_rate=25.0,
            experience_years=5,
            rating=4.8,
            total_students=50,
            specializations=["calculus", "linear_algebra"],
            gender="female",
            languages=["english", "french"]
        ),
        "t2": Teacher(
            id="t2",
            subjects=["physics", "chemistry"],
            teaching_style="hands_on",
            availability=["evening"],
            location_preference="both",
            hourly_rate=35.0,
            experience_years=8,
            rating=4.6,
            total_students=75,
            specializations=["quantum_physics", "organic_chemistry"],
            gender="male",
            languages=["english", "spanish"]
        ),
        "t3": Teacher(
            id="t3",
            subjects=["english", "literature"],
            teaching_style="discussion",
            availability=["morning", "evening"],
            location_preference="in_person",
            hourly_rate=30.0,
            experience_years=12,
            rating=4.9,
            total_students=120,
            specializations=["creative_writing", "grammar"],
            gender="non_binary",
            languages=["english"]
        )
    }
    
    return mock_teachers

async def load_interaction_data():
    """Load historical interaction data - mock implementation"""
    import pandas as pd
    
    # Mock interaction data
    data = {
        'student_id': ['s1', 's1', 's2', 's2', 's3', 's3'],
        'teacher_id': ['t1', 't2', 't1', 't3', 't2', 't3'],
        'rating': [4.5, 3.8, 4.9, 4.2, 4.0, 4.7]
    }
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    # Production deployment would use gunicorn/uvicorn workers
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )

# Docker Configuration
"""
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""

# Kubernetes Deployment
"""
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: matching-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: matching-service
  template:
    metadata:
      labels:
        app: matching-service
    spec:
      containers:
      - name: matching-service
        image: matching-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: matching-service
spec:
  selector:
    app: matching-service
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: matching-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: matching-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""

# Requirements.txt
"""
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
redis==4.6.0
prometheus-client==0.19.0
python-multipart==0.0.6
"""