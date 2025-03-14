from main import SessionLocal, Teacher, Lesson, Base, engine

# Ensure tables are created
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Create sample teachers
teacher1 = Teacher(available=True, rating=4.5)
teacher2 = Teacher(available=True, rating=4.2)
db.add(teacher1)
db.add(teacher2)
db.commit()

# Create sample lessons for each teacher
lesson1 = Lesson(title="Mathematics", level="Intermediate", travelDistance=10, teacherId=teacher1.id)
lesson2 = Lesson(title="Mathematics", level="Intermediate", travelDistance=5, teacherId=teacher2.id)
db.add(lesson1)
db.add(lesson2)
db.commit()

print("Sample data inserted successfully!")
db.close()
