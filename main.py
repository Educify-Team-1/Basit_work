import os
import joblib
import numpy as np
import random
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Load the AI model (make sure teacher_recommendation_model.pkl exists)
model = joblib.load("teacher_recommendation_model.pkl")

# ---------------- Database Setup ----------------
# Use your Educify PostgreSQL database connection string
DATABASE_URL = "postgresql://postgres:!post123!@72.52.132.11:5432/test_db_educify"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------- Database Models ----------------
class Teacher(Base):
    __tablename__ = "Teacher"
    id = Column(Integer, primary_key=True, index=True)
    available = Column(Boolean, default=True)
    rating = Column(Float, default=0.0)

class Lesson(Base):
    __tablename__ = "Lesson"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    level = Column(String, index=True)
    travelDistance = Column(Integer)
    teacherId = Column(Integer, ForeignKey("Teacher.id"))

class Booking(Base):
    __tablename__ = "Booking"
    id = Column(Integer, primary_key=True, index=True)
    desired_subject = Column(String, index=True)
    distance = Column(Integer)
    grade_level = Column(String, index=True)
    status = Column(String, default="pending")  # "pending" or "accepted"
    accepted_teacher_id = Column(Integer, nullable=True)

class TeacherNotification(Base):
    __tablename__ = "TeacherNotification"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("Booking.id"))
    teacher_id = Column(Integer)
    active = Column(Boolean, default=True)

class StudentProfile(Base):
    __tablename__ = "StudentProfile"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, index=True)

# If the tables haven't been created yet, you can run this once.
# Base.metadata.create_all(bind=engine)

# ---------------- FastAPI Application ----------------
app = FastAPI()

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Pydantic Models ----------------
class Student(BaseModel):
    desired_subject: str
    distance: int
    grade_level: str

class TeacherResponse(BaseModel):
    booking_id: int
    teacher_id: int
    response: str  # Expected values: "accept" or "deny"

# ---------------- Helper Functions ----------------
def send_notification(teacher_id: int, booking_id: int):
    print(f"Notification sent to Teacher {teacher_id} for Booking {booking_id}")

def recommend_teachers_with_ai(db: Session, student: Dict[str, Any]):
    # Query teacher details from the database
    teachers = db.query(Teacher.id, Lesson.title, Teacher.rating, Lesson.travelDistance)\
        .join(Lesson, Teacher.id == Lesson.teacherId)\
        .filter(Lesson.title == student["desired_subject"]).all()
    
    teacher_scores = []
    for teacher in teachers:
        teacher_id, title, rating, travel_distance = teacher
        subject_match = 1 if student["desired_subject"] == title else 0

        # Predict acceptance probability using the model
        prediction = model.predict(np.array([[teacher_id, subject_match, rating, travel_distance]]))[0]
        if prediction == 1:  # Only consider teachers predicted to accept
            teacher_scores.append({"teacher_id": teacher_id, "score": rating})

    teacher_scores.sort(key=lambda x: x["score"], reverse=True)
    return teacher_scores[:3]

# ---------------- API Endpoints ----------------
@app.post("/book-free-trial/")
async def book_free_trial(student: Student, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        booking = Booking(
            desired_subject=student.desired_subject,
            distance=student.distance,
            grade_level=student.grade_level,
            status="pending"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Use the AI-based recommendation function
        recommended = recommend_teachers_with_ai(db, student.dict())
        
        for rec in recommended:
            notification = TeacherNotification(booking_id=booking.id, teacher_id=rec["teacher_id"], active=True)
            db.add(notification)
            db.commit()
            background_tasks.add_task(send_notification, rec["teacher_id"], booking.id)
        
        return {
            "message": "Booking created and AI-recommended teachers notified.",
            "booking_id": booking.id,
            "recommended_teachers": recommended
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/teacher-response/")
async def teacher_response(response: TeacherResponse, db: Session = Depends(get_db)):
    try:
        booking = db.query(Booking).filter(Booking.id == response.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking.status == "accepted":
            return {"message": "Booking already accepted by another teacher."}
        
        if response.response.lower() == "accept":
            booking.status = "accepted"
            booking.accepted_teacher_id = response.teacher_id
            db.commit()
            db.query(TeacherNotification)\
              .filter(TeacherNotification.booking_id == booking.id,
                      TeacherNotification.teacher_id != response.teacher_id)\
              .update({"active": False})
            db.commit()
            return {"message": f"Booking accepted by Teacher {response.teacher_id}"}
        elif response.response.lower() == "deny":
            db.query(TeacherNotification)\
              .filter(TeacherNotification.booking_id == booking.id,
                      TeacherNotification.teacher_id == response.teacher_id)\
              .update({"active": False})
            db.commit()
            return {"message": f"Teacher {response.teacher_id} denied the booking."}
        else:
            raise HTTPException(status_code=400, detail="Invalid response. Use 'accept' or 'deny'.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    # Run the FastAPI server without seeding the database.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
