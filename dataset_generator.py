# dataset_generator.py - Generate realistic training data
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import json

def generate_students_data(n_students=1000):
    """Generate realistic student data"""
    subjects_pool = [
        "mathematics", "physics", "chemistry", "biology", "english", 
        "literature", "history", "geography", "computer_science", "economics",
        "french", "spanish", "art", "music", "philosophy"
    ]
    
    learning_styles = ["visual", "auditory", "kinesthetic", "reading"]
    time_slots = ["morning", "afternoon", "evening", "weekend"]
    locations = ["online", "in_person", "both"]
    experience_levels = ["beginner", "intermediate", "advanced"]
    
    students = []
    for i in range(n_students):
        # Realistic subject combinations
        num_subjects = random.randint(1, 4)
        student_subjects = random.sample(subjects_pool, num_subjects)
        
        # Realistic availability (1-3 time slots)
        num_slots = random.randint(1, 3)
        availability = random.sample(time_slots, num_slots)
        
        # Budget ranges based on location preference
        location_pref = random.choice(locations)
        if location_pref == "online":
            budget_min = random.randint(15, 25)
            budget_max = budget_min + random.randint(10, 25)
        else:
            budget_min = random.randint(20, 35)
            budget_max = budget_min + random.randint(15, 30)
        
        students.append({
            'id': f's{i+1:04d}',
            'subjects': ','.join(student_subjects),
            'learning_style': random.choice(learning_styles),
            'availability': ','.join(availability),
            'location_preference': location_pref,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'experience_level': random.choice(experience_levels),
            'age': random.randint(16, 45),
            'preferred_teacher_gender': random.choice([None, 'male', 'female', 'any'])
        })
    
    return pd.DataFrame(students)

def generate_teachers_data(n_teachers=200):
    """Generate realistic teacher data"""
    subjects_pool = [
        "mathematics", "physics", "chemistry", "biology", "english", 
        "literature", "history", "geography", "computer_science", "economics",
        "french", "spanish", "art", "music", "philosophy"
    ]
    
    teaching_styles = ["visual", "hands_on", "discussion", "interactive", "structured"]
    time_slots = ["morning", "afternoon", "evening", "weekend"]
    locations = ["online", "in_person", "both"]
    genders = ["male", "female", "non_binary"]
    languages_pool = ["english", "spanish", "french", "german", "mandarin", "arabic"]
    
    teachers = []
    for i in range(n_teachers):
        # Teachers usually specialize in 1-3 subjects
        num_subjects = random.randint(1, 3)
        teacher_subjects = random.sample(subjects_pool, num_subjects)
        
        # Availability (2-4 time slots)
        num_slots = random.randint(2, 4)
        availability = random.sample(time_slots, num_slots)
        
        # Experience affects rating and rate
        experience_years = random.randint(1, 20)
        base_rating = 3.5 + (experience_years / 20) * 1.3 + random.uniform(-0.3, 0.3)
        rating = max(3.0, min(5.0, base_rating))
        
        # Hourly rate based on experience and subjects
        base_rate = 20 + (experience_years * 1.5)
        if any(subj in ["mathematics", "physics", "computer_science"] for subj in teacher_subjects):
            base_rate += 5  # STEM premium
        hourly_rate = base_rate + random.uniform(-5, 10)
        
        # Total students based on experience and rating
        total_students = int(experience_years * 5 * (rating / 5.0) + random.randint(0, 20))
        
        # Languages (1-3)
        num_languages = random.randint(1, 3)
        languages = random.sample(languages_pool, num_languages)
        
        # Specializations from subjects
        specializations = []
        for subject in teacher_subjects:
            if subject == "mathematics":
                specializations.extend(random.sample(
                    ["algebra", "calculus", "geometry", "statistics"], 
                    random.randint(1, 2)
                ))
            elif subject == "physics":
                specializations.extend(random.sample(
                    ["mechanics", "quantum_physics", "thermodynamics"], 
                    random.randint(1, 2)
                ))
            elif subject == "english":
                specializations.extend(random.sample(
                    ["grammar", "creative_writing", "literature"], 
                    random.randint(1, 2)
                ))
        
        teachers.append({
            'id': f't{i+1:04d}',
            'subjects': ','.join(teacher_subjects),
            'teaching_style': random.choice(teaching_styles),
            'availability': ','.join(availability),
            'location_preference': random.choice(locations),
            'hourly_rate': round(hourly_rate, 2),
            'experience_years': experience_years,
            'rating': round(rating, 1),
            'total_students': total_students,
            'specializations': ','.join(specializations) if specializations else teacher_subjects[0],
            'gender': random.choice(genders),
            'languages': ','.join(languages)
        })
    
    return pd.DataFrame(teachers)

def generate_interactions_data(students_df, teachers_df, n_interactions=5000):
    """Generate realistic student-teacher interaction data"""
    interactions = []
    
    for i in range(n_interactions):
        student = students_df.sample(1).iloc[0]
        
        # Find teachers that match student's subjects
        student_subjects = set(student['subjects'].split(','))
        compatible_teachers = []
        
        for _, teacher in teachers_df.iterrows():
            teacher_subjects = set(teacher['subjects'].split(','))
            if student_subjects & teacher_subjects:  # Has common subjects
                # Check availability overlap
                student_availability = set(student['availability'].split(','))
                teacher_availability = set(teacher['availability'].split(','))
                if student_availability & teacher_availability:
                    # Check budget compatibility
                    if student['budget_min'] <= teacher['hourly_rate'] <= student['budget_max']:
                        compatible_teachers.append(teacher)
        
        if not compatible_teachers:
            # If no perfect match, just pick a random teacher
            teacher = teachers_df.sample(1).iloc[0]
        else:
            # Bias towards higher-rated teachers
            teacher = random.choices(
                compatible_teachers,
                weights=[t['rating'] for t in compatible_teachers]
            )[0]
        
        # Generate rating based on compatibility
        base_rating = teacher['rating']
        
        # Adjust based on compatibility factors
        student_subjects = set(student['subjects'].split(','))
        teacher_subjects = set(teacher['subjects'].split(','))
        subject_match = len(student_subjects & teacher_subjects) / len(student_subjects)
        
        student_avail = set(student['availability'].split(','))
        teacher_avail = set(teacher['availability'].split(','))
        schedule_match = len(student_avail & teacher_avail) / len(student_avail)
        
        budget_fit = 1.0 if student['budget_min'] <= teacher['hourly_rate'] <= student['budget_max'] else 0.5
        
        # Final rating with some randomness
        compatibility_score = (subject_match * 0.4 + schedule_match * 0.3 + budget_fit * 0.3)
        final_rating = base_rating * (0.7 + compatibility_score * 0.3) + random.uniform(-0.5, 0.5)
        final_rating = max(1.0, min(5.0, final_rating))
        
        interactions.append({
            'student_id': student['id'],
            'teacher_id': teacher['id'],
            'rating': round(final_rating, 1),
            'lesson_completed': random.choice([True, True, True, False]),  # 75% completion rate
            'timestamp': datetime.now() - timedelta(days=random.randint(0, 365))
        })
    
    return pd.DataFrame(interactions)

def create_complete_dataset():
    """Create the complete dataset for training"""
    print("Generating students data...")
    students_df = generate_students_data(1000)
    
    print("Generating teachers data...")
    teachers_df = generate_teachers_data(200)
    
    print("Generating interactions data...")
    interactions_df = generate_interactions_data(students_df, teachers_df, 5000)
    
    # Create data directory
    import os
    os.makedirs('data', exist_ok=True)
    
    # Save datasets
    students_df.to_csv('data/students.csv', index=False)
    teachers_df.to_csv('data/teachers.csv', index=False)
    interactions_df.to_csv('data/interactions.csv', index=False)
    
    print(f"Dataset created:")
    print(f"- Students: {len(students_df)}")
    print(f"- Teachers: {len(teachers_df)}")
    print(f"- Interactions: {len(interactions_df)}")
    
    return students_df, teachers_df, interactions_df

if __name__ == "__main__":
    create_complete_dataset()