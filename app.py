import os
from typing import Any, Dict, List

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

# Database connection
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DATABASE"),
    user=os.getenv("USER"),
    password=os.getenv("PASSWORD"),
)
cursor = conn.cursor()

app = FastAPI()


# Define request body schema using Pydantic
class Student(BaseModel):
    desired_subject: str
    distance: int
    grade_level: str
    # language_preference: Optional[str]  # Add this field if language preference is considered


# subject, location, availability of teacher, and grade_level
def fetch_teachers(student: Dict[str, Any]):
    query = """
    SELECT T.id, T.available, L."title", T.rating, L."travelDistance"
    FROM "Teacher" AS T
    JOIN "Lesson" AS L ON T.id = L."teacherId"
    WHERE T.available = true
    AND L."title" = %(desired_subject)s
    AND L."travelDistance" <= %(distance)s
    AND L."level" = %(grade)s
    """
    cursor.execute(
        query,
        {
            "desired_subject": student["desired_subject"],
            "distance": student["distance"],
            "grade": student["grade_level"],
        },
    )

    teachers = cursor.fetchall()
    return teachers


def calculate_matching_score(student: Dict[str, Any], teacher: tuple):
    # Assuming teacher is a tuple based on fetch_teachers query result
    teacher_id, available, skills, rating, distance = teacher

    score = 0
    # Subject match
    if student["desired_subject"] in skills:
        score += 10  # Subject expertise is highly valued

    # Availability match (already checked by fetch, so adding score)
    if available:
        score += 5  # Teacher is available

    # Experience & Rating match
    score += rating  # Higher rating, higher score

    # Distance match
    if student["distance"] is not None and distance <= student["distance"]:
        score += 2  # Closer distance bonus

    return score


@app.post("/recommend-teachers/")
async def recommend_teachers(student: Student):
    try:
        # Fetch teachers based on student information
        teachers = fetch_teachers(student.dict())
        teacher_scores = []

        # Calculate matching scores
        for teacher in teachers:
            score = calculate_matching_score(student.dict(), teacher)
            teacher_scores.append(
                {"teacher_id": teacher[0], "score": score}  # teacher[0] is the "id"
            )

        # Sort by matching score in descending order
        teacher_scores.sort(key=lambda x: x["score"], reverse=True)

        # Return top 3 recommendations
        return {"recommended_teachers": teacher_scores[:3]}  # Return top 3

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Close the database connection after server shutdown
@app.on_event("shutdown")
def shutdown_db():
    cursor.close()
    conn.close()
