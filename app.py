import os
import random
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------- Database Setup ----------------
DATABASE_URL = "sqlite:///./test.db"  # SQLite database stored locally

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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

# Create tables (and the SQLite file if it doesn't exist)
Base.metadata.create_all(bind=engine)

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
def fetch_teachers(db: Session, student: Dict[str, Any]):
    return db.query(Teacher.id, Teacher.available, Lesson.title, Teacher.rating, Lesson.travelDistance)\
        .join(Lesson, Teacher.id == Lesson.teacherId)\
        .filter(
            Teacher.available == True,
            Lesson.title == student["desired_subject"],
            Lesson.travelDistance <= student["distance"],
            Lesson.level == student["grade_level"]
        ).all()

def calculate_matching_score(student: Dict[str, Any], teacher: tuple):
    teacher_id, available, title, rating, distance = teacher
    score = 0
    if student["desired_subject"] == title:
        score += 10
    if available:
        score += 5
    score += rating  # Higher rating increases score
    if distance <= student["distance"]:
        score += 2
    return score

def send_notification(teacher_id: int, booking_id: int):
    print(f"Notification sent to Teacher {teacher_id} for Booking {booking_id}")

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
        
        teachers = fetch_teachers(db, student.dict())
        teacher_scores = [
            {"teacher_id": teacher[0], "score": calculate_matching_score(student.dict(), teacher)}
            for teacher in teachers
        ]
        teacher_scores.sort(key=lambda x: x["score"], reverse=True)
        recommended = teacher_scores[:3]
        
        for rec in recommended:
            notification = TeacherNotification(booking_id=booking.id, teacher_id=rec["teacher_id"], active=True)
            db.add(notification)
            db.commit()
            background_tasks.add_task(send_notification, rec["teacher_id"], booking.id)
        
        return {
            "message": "Booking created and notifications sent.",
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

# ---------------- Database Seeding ----------------
def seed_data():
    """
    Seed the database with:
      - 200 teacher records (each with an associated lesson)
      - 2 sample student profiles
    """
    db = SessionLocal()
    
    # Insert 200 teachers and their associated lessons
    for i in range(1, 201):
        available = random.choice([True, True, True, False])
        rating = round(random.uniform(3.0, 5.0), 1)
        teacher = Teacher(available=available, rating=rating)
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        
        travel_distance = random.randint(5, 20)
        lesson = Lesson(
            title="Mathematics",
            level="Intermediate",
            travelDistance=travel_distance,
            teacherId=teacher.id
        )
        db.add(lesson)
        db.commit()
    
    # Insert sample student profiles
    student1 = StudentProfile(name="Alice Johnson", email="alice@example.com", phone="1234567890")
    student2 = StudentProfile(name="Bob Smith", email="bob@example.com", phone="0987654321")
    db.add(student1)
    db.add(student2)
    db.commit()
    
    print("Database seeded successfully with 200 teachers, lessons, and sample student profiles!")
    db.close()

# ---------------- Main Block ----------------
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_data()
    else:
        import uvicorn
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
