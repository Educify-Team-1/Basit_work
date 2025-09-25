# backend/train.py
import os
from matcher import MatchingEngine, BASE_DIR, DATA_DIR, DEFAULT_MODEL_PATH

if __name__ == "__main__":
    teachers = os.path.join(DATA_DIR, "teachers.csv")
    students = os.path.join(DATA_DIR, "students.csv")
    interactions = os.path.join(DATA_DIR, "interactions.csv")

    engine = MatchingEngine()
    print("Training model from:")
    print(" -", teachers)
    print(" -", students)
    print(" -", interactions)
    engine.fit_from_csv(teachers_csv_path=teachers,
                        students_csv_path=students,
                        interactions_csv_path=interactions,
                        save_path=DEFAULT_MODEL_PATH)
    print("✅ Model trained and saved to:", DEFAULT_MODEL_PATH)
