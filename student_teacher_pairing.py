# import psycopg2

# # Database connection
# conn = psycopg2.connect(
#     host="72.52.132.11",
#     database="educify_backup",
#     user="postgres",
#     password="!post123!",
# )
# cursor = conn.cursor()


# # subject, location, availability of teacher, and grade_level
# def fetch_teachers(student):
#     query = """
#     SELECT T.id, T.available, L."title", T.rating, L."travelDistance"
#     FROM "Teacher" AS T
#     JOIN "Lesson" AS L ON T.id = L."teacherId"
#     WHERE T.available = true
#     AND L."title" = %(desired_subject)s
#     AND L."travelDistance" <= %(distance)s
#     AND L."level" = %(grade)s
#     """
#     cursor.execute(
#         query,
#         {
#             "desired_subject": student["desired_subject"],
#             "distance": student["distance"],
#             "grade": student["grade_level"],
#         },
#     )

#     teachers = cursor.fetchall()
#     return teachers


# def calculate_matching_score(student, teacher):
#     # Assuming teacher is a tuple based on fetch_teachers query result
#     teacher_id, available, skills, rating, distance = teacher

#     score = 0
#     # Subject match
#     if student["desired_subject"] in skills:
#         score += 10  # Subject expertise is highly valued

#     # Availability match (already checked by fetch, so adding score)
#     if available:
#         score += 5  # Teacher is available

#     # Language match - (assuming a language preference check)
#     # Placeholder: Adjust if "languages" data is available in query or by another fetch
#     # if student.get("language_preference") in skills:
#     #     score += 3  # Preferred language match

#     # Experience & Rating match
#     # Assuming "experience_years" is part of teacher["skills"]
#     score += rating  # Higher rating, higher score

#     # Distance match
#     if student["distance"] is not None and distance <= student["distance"]:
#         score += 2  # Closer distance bonus

#     return score


# def recommend_teachers(student):
#     teachers = fetch_teachers(student)
#     teacher_scores = []

#     for teacher in teachers:
#         score = calculate_matching_score(student, teacher)
#         teacher_scores.append((teacher[0], score))  # teacher[0] is the "id"

#     # Sort by matching score in descending order
#     teacher_scores.sort(key=lambda x: x[1], reverse=True)
#     return teacher_scores[:3]  # Return top 3 recommendations


# # Example usage
# student = {
#     "desired_subject": "Mathematics",
#     "distance": 8,
#     "grade_level": "BEGINNER",
#     # "language_preference": "English"
# }

# recommended_teachers = recommend_teachers(student)
# print("Top recommended teachers:", recommended_teachers)

# # Close the database connection
# cursor.close()
# conn.close()
