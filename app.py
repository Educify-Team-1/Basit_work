import os
from typing import Any, Dict

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

# database connection
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DATABASE"),
    user=os.getenv("USER"),
    password=os.getenv("PASSWORD"),
)
cursor = conn.cursor()

app = FastAPI()


class Student(BaseModel):
    desired_subject: str
    grade_level: str
    preferred_location: str 


def fetch_teachers(student: Dict[str, Any]):
    query = """
    SELECT T.id, T.available, L."title", T.rating, L."location"
    FROM "Teacher" AS T
    JOIN "Lesson" AS L ON T.id = L."teacherId"
    WHERE T.available = true
      AND L."title" = %(desired_subject)s
      AND L."level" = %(grade_level)s
      AND %(preferred_location)s = ANY(L."location")
    """
    cursor.execute(
        query,
        {
            "desired_subject": student["desired_subject"],
            "grade_level": student["grade_level"],
            "preferred_location": student["preferred_location"],
        },
    )

    teachers = cursor.fetchall()
    return teachers


def calculate_matching_score(student: Dict[str, Any], teacher: tuple):
    # Unpack the teacher tuple: (id, available, title, rating, location)
    teacher_id, available, title, rating, locations = teacher

    score = 0

    # Subject match bonus (should always be true due to the SQL filter,
    # but included here for clarity)
    if student["desired_subject"].lower() == title.lower():
        score += 10

    # Bonus for availability
    if available:
        score += 5

    score += rating

    if isinstance(locations, list) and len(locations) > 1:
        score += 2

    return score


@app.post("/recommend-teachers/")
async def recommend_teachers(student: Student):
    try:
        # Fetch teachers based on the student's criteria
        teachers = fetch_teachers(student.dict())
        teacher_scores = []

        # Calculate a matching score for each teacher
        for teacher in teachers:
            score = calculate_matching_score(student.dict(), teacher)
            teacher_scores.append({"teacher_id": teacher[0], "score": score})

        # Sort teachers by matching score in descending order
        teacher_scores.sort(key=lambda x: x["score"], reverse=True)

        # Return the top 3 teacher recommendations
        return {"recommended_teachers": teacher_scores[:3]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Close the database connection when the server shuts down
@app.on_event("shutdown")
def shutdown_db():
    cursor.close()
    conn.close()
