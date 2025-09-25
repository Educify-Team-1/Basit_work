# backend/app.py
import os
import time
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request
from pydantic import BaseModel
import logging

from matcher import MatchingEngine, Student, BASE_DIR, DATA_DIR, DEFAULT_MODEL_PATH

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("educify-api")

# Paths
MODEL_PATH = DEFAULT_MODEL_PATH
TEACHERS_CSV = os.path.join(DATA_DIR, "teachers.csv")
STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
INTERACTIONS_CSV = os.path.join(DATA_DIR, "interactions.csv")

# Simple API key protection for train/feedback (optional)
API_KEYS = set(os.getenv("API_KEYS", "mk_test_key_dev").split(","))

# Initialize engine
engine = MatchingEngine()
model_loaded = engine.load(MODEL_PATH)
if not model_loaded:
    # Attempt to auto-train if CSVs exist (useful for first-time deploy)
    if os.path.exists(TEACHERS_CSV):
        logger.info("No model found - training from CSVs on startup...")
        try:
            engine.fit_from_csv(TEACHERS_CSV, STUDENTS_CSV, INTERACTIONS_CSV, save_path=MODEL_PATH)
            engine.load(MODEL_PATH)
            logger.info("Startup training complete.")
        except Exception as e:
            logger.error("Startup training failed: %s", e)
    else:
        logger.warning("No model and no teachers.csv found. /match will return empty until model is built.")

app = FastAPI(title="Educify Matching API", version="1.0.0")


# -------------------------
# Pydantic models
# -------------------------
class StudentRequest(BaseModel):
    id: Optional[str] = ""
    subjects: List[str]
    learning_style: Optional[str] = ""
    availability: Optional[List[str]] = None
    location_preference: Optional[str] = ""
    budget_max: Optional[float] = 0.0
    experience_level: Optional[str] = "beginner"
    preferred_teacher_gender: Optional[str] = None
    age: Optional[int] = None


class TeacherResponse(BaseModel):
    id: str
    subjects: List[str]
    teaching_style: Optional[str] = ""
    availability: Optional[List[str]] = None
    location_preference: Optional[str] = ""
    hourly_rate: Optional[float] = 0.0
    experience_years: Optional[float] = 0.0
    rating: Optional[float] = 0.0
    total_students: Optional[int] = 0
    specializations: Optional[List[str]] = None
    gender: Optional[str] = ""
    languages: Optional[List[str]] = None


class MatchResponse(BaseModel):
    teacher_id: str
    student_id: str
    compatibility_score: float
    confidence: float
    reasons: List[str]
    teacher_details: Optional[TeacherResponse] = None


class FeedbackRequest(BaseModel):
    student_id: str
    teacher_id: str
    rating: float
    lesson_completed: bool
    feedback_text: Optional[str] = None


# -------------------------
# Helpers
# -------------------------
def verify_api_key(x_api_key: str = Header(None)):
    if API_KEYS and (x_api_key not in API_KEYS):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def append_interaction_row(feedback: FeedbackRequest):
    # append to interactions.csv (simple)
    os.makedirs(DATA_DIR, exist_ok=True)
    row = {
        "student_id": feedback.student_id,
        "teacher_id": feedback.teacher_id,
        "rating": float(feedback.rating),
        "lesson_completed": bool(feedback.lesson_completed),
        "feedback_text": feedback.feedback_text or "",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # write header if file doesn't exist
    if not os.path.exists(INTERACTIONS_CSV) or os.path.getsize(INTERACTIONS_CSV) == 0:
        import pandas as pd
        pd.DataFrame([row]).to_csv(INTERACTIONS_CSV, index=False)
    else:
        with open(INTERACTIONS_CSV, "a", encoding="utf-8") as f:
            f.write(",".join([str(row[k]) for k in row.keys()]) + "\n")


def background_retrain():
    try:
        logger.info("Background retrain started...")
        engine.fit_from_csv(TEACHERS_CSV, STUDENTS_CSV, INTERACTIONS_CSV, save_path=MODEL_PATH)
        logger.info("Background retrain finished.")
    except Exception as e:
        logger.error("Background retrain failed: %s", e)


# -------------------------
# Endpoints
# -------------------------
@app.get("/")
def root():
    return {"message": "Educify Matching API", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": engine.teacher_subject_matrix is not None and engine.teacher_subject_matrix.size > 0,
        "teachers_count": len(engine.teacher_ids),
        "data_files": {
            "teachers.csv": os.path.exists(TEACHERS_CSV),
            "students.csv": os.path.exists(STUDENTS_CSV),
            "interactions.csv": os.path.exists(INTERACTIONS_CSV)
        }
    }


@app.post("/match", response_model=List[MatchResponse])
def match(student: StudentRequest, top_k: int = 3):
    if engine.teacher_subject_matrix is None or engine.teacher_subject_matrix.size == 0:
        raise HTTPException(status_code=503, detail="Model not ready. Train the model first.")

    stud = Student(
        id=student.id or "",
        subjects=[s.strip().lower() for s in student.subjects],
        learning_style=student.learning_style or "",
        availability=[a.strip().lower() for a in (student.availability or [])] if student.availability else [],
        location_preference=student.location_preference or "",
        budget_max=float(student.budget_max or 0.0),
        experience_level=student.experience_level or "beginner",
        preferred_teacher_gender=student.preferred_teacher_gender,
        age=student.age
    )

    matches = engine.find_matches(stud, top_k=top_k)

    response = []
    for m in matches:
        meta = engine.teacher_meta.get(m.teacher_id, {})
        teacher_resp = TeacherResponse(
            id=meta.get("id", m.teacher_id),
            subjects=meta.get("subjects", []),
            teaching_style=meta.get("teaching_style", ""),
            availability=meta.get("availability", []),
            location_preference=meta.get("location_preference", ""),
            hourly_rate=meta.get("hourly_rate", 0.0),
            experience_years=meta.get("experience_years", 0.0),
            rating=meta.get("rating", 0.0),
            total_students=meta.get("total_students", 0),
            specializations=meta.get("specializations", []),
            gender=meta.get("gender", ""),
            languages=meta.get("languages", [])
        )
        response.append(MatchResponse(
            teacher_id=m.teacher_id,
            student_id=m.student_id,
            compatibility_score=m.compatibility_score,
            confidence=m.confidence,
            reasons=m.reasons,
            teacher_details=teacher_resp
        ))
    return response


@app.post("/train")
def trigger_train(background_tasks: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    # Run training in background (doesn't block API)
    background_tasks.add_task(background_retrain)
    return {"message": "Retraining started in background (check logs). This may take a while."}


@app.post("/feedback")
def feedback(feedback: FeedbackRequest, background_tasks: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    try:
        append_interaction_row(feedback)
        # Optionally retrain if interactions grow large — do it in background to not block request
        background_tasks.add_task(background_retrain)
        return {"message": "Feedback recorded; retrain scheduled in background."}
    except Exception as e:
        logger.error("Failed to record feedback: %s", e)
        raise HTTPException(status_code=500, detail="Failed to record feedback")
