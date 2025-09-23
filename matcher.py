# AI Teacher-Student Matching System
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import redis
import json
from datetime import datetime, timedelta
import logging

@dataclass
class Student:
    id: str
    subjects: List[str]
    learning_style: str  # visual, auditory, kinesthetic, reading
    availability: List[str]  # time slots
    location_preference: str  # online, in_person, both
    budget_range: Tuple[float, float]
    experience_level: str  # beginner, intermediate, advanced
    preferred_teacher_gender: Optional[str] = None
    age: int = 0

@dataclass
class Teacher:
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

@dataclass
class MatchResult:
    teacher_id: str
    student_id: str
    compatibility_score: float
    confidence: float
    reasons: List[str]

class FeatureEngineering:
    """Handle feature extraction and preprocessing"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000)
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def extract_features(self, student: Student, teacher: Teacher) -> np.ndarray:
        """Extract features for a student-teacher pair"""
        features = []
        
        # Subject compatibility
        subject_overlap = len(set(student.subjects) & set(teacher.subjects))
        subject_score = subject_overlap / max(len(student.subjects), 1)
        features.append(subject_score)
        
        # Schedule compatibility
        schedule_overlap = len(set(student.availability) & set(teacher.availability))
        schedule_score = schedule_overlap / max(len(student.availability), 1)
        features.append(schedule_score)
        
        # Location preference match
        location_match = 1.0 if (student.location_preference == teacher.location_preference or 
                                student.location_preference == "both" or 
                                teacher.location_preference == "both") else 0.0
        features.append(location_match)
        
        # Budget compatibility
        budget_match = 1.0 if student.budget_range[0] <= teacher.hourly_rate <= student.budget_range[1] else 0.0
        features.append(budget_match)
        
        # Teaching style compatibility
        style_compatibility = self._calculate_style_compatibility(student.learning_style, teacher.teaching_style)
        features.append(style_compatibility)
        
        # Teacher quality metrics
        features.extend([
            teacher.rating / 5.0,  # normalized rating
            min(teacher.experience_years / 10.0, 1.0),  # normalized experience
            min(teacher.total_students / 100.0, 1.0)  # normalized student count
        ])
        
        # Gender preference
        gender_match = 1.0 if (student.preferred_teacher_gender is None or 
                              student.preferred_teacher_gender == teacher.gender) else 0.5
        features.append(gender_match)
        
        return np.array(features)
    
    def _calculate_style_compatibility(self, learning_style: str, teaching_style: str) -> float:
        """Calculate compatibility between learning and teaching styles"""
        compatibility_matrix = {
            ("visual", "visual"): 1.0,
            ("visual", "interactive"): 0.8,
            ("auditory", "discussion"): 1.0,
            ("auditory", "interactive"): 0.7,
            ("kinesthetic", "hands_on"): 1.0,
            ("kinesthetic", "interactive"): 0.8,
            ("reading", "structured"): 1.0,
            ("reading", "academic"): 0.9
        }
        return compatibility_matrix.get((learning_style, teaching_style), 0.5)

class CollaborativeFiltering:
    """Collaborative filtering for teacher-student matching"""
    
    def __init__(self):
        self.user_item_matrix = None
        self.similarity_matrix = None
    
    def fit(self, interaction_data: pd.DataFrame):
        """Train collaborative filtering model"""
        # Create user-item matrix (students x teachers)
        self.user_item_matrix = interaction_data.pivot_table(
            index='student_id', 
            columns='teacher_id', 
            values='rating',
            fill_value=0
        )
        
        # Calculate teacher similarity matrix
        self.similarity_matrix = cosine_similarity(self.user_item_matrix.T)
    
    def predict_rating(self, student_id: str, teacher_id: str) -> float:
        """Predict rating for student-teacher pair"""
        if self.user_item_matrix is None:
            return 0.5  # Default rating
        
        try:
            student_idx = self.user_item_matrix.index.get_loc(student_id)
            teacher_idx = self.user_item_matrix.columns.get_loc(teacher_id)
            
            # Get student's ratings
            student_ratings = self.user_item_matrix.iloc[student_idx]
            
            # Find similar teachers
            teacher_similarities = self.similarity_matrix[teacher_idx]
            
            # Calculate weighted average
            numerator = np.sum(teacher_similarities * student_ratings)
            denominator = np.sum(np.abs(teacher_similarities))
            
            if denominator == 0:
                return 0.5
            
            return min(max(numerator / denominator, 0), 1)
            
        except (KeyError, IndexError):
            return 0.5

class MatchingEngine:
    """Main matching engine combining multiple approaches"""
    
    def __init__(self, redis_client=None):
        self.feature_engineer = FeatureEngineering()
        self.collaborative_filter = CollaborativeFiltering()
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.logger = logging.getLogger(__name__)
        
        # Model weights (can be learned)
        self.weights = {
            'content_based': 0.6,
            'collaborative': 0.3,
            'popularity': 0.1
        }
    
    def train(self, interaction_data: pd.DataFrame):
        """Train the matching models"""
        self.logger.info("Training collaborative filtering model...")
        self.collaborative_filter.fit(interaction_data)
        self.logger.info("Training completed")
    
    def find_matches(self, student: Student, teachers: List[Teacher], 
                    top_k: int = 10) -> List[MatchResult]:
        """Find best matching teachers for a student"""
        
        # Check cache first
        cache_key = f"matches:{student.id}:{hash(str(student))}"
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        matches = []
        
        for teacher in teachers:
            # Content-based score
            content_score = self._calculate_content_score(student, teacher)
            
            # Collaborative filtering score
            collab_score = self.collaborative_filter.predict_rating(student.id, teacher.id)
            
            # Popularity score (teacher rating and experience)
            popularity_score = (teacher.rating / 5.0) * 0.7 + (min(teacher.total_students / 100.0, 1.0)) * 0.3
            
            # Combined score
            final_score = (
                self.weights['content_based'] * content_score +
                self.weights['collaborative'] * collab_score +
                self.weights['popularity'] * popularity_score
            )
            
            # Calculate confidence based on available data
            confidence = self._calculate_confidence(student, teacher)
            
            # Generate reasons
            reasons = self._generate_reasons(student, teacher, content_score)
            
            matches.append(MatchResult(
                teacher_id=teacher.id,
                student_id=student.id,
                compatibility_score=final_score,
                confidence=confidence,
                reasons=reasons
            ))
        
        # Sort by score and return top k
        matches.sort(key=lambda x: x.compatibility_score, reverse=True)
        top_matches = matches[:top_k]
        
        # Cache results
        self.redis_client.setex(
            cache_key, 
            timedelta(hours=1), 
            json.dumps([match.__dict__ for match in top_matches])
        )
        
        return top_matches
    
    def _calculate_content_score(self, student: Student, teacher: Teacher) -> float:
        """Calculate content-based compatibility score"""
        features = self.feature_engineer.extract_features(student, teacher)
        
        # Weighted feature importance
        weights = np.array([0.25, 0.2, 0.15, 0.15, 0.1, 0.05, 0.05, 0.03, 0.02])
        
        if len(features) != len(weights):
            # Adjust weights if feature count differs
            weights = weights[:len(features)]
            weights = weights / weights.sum()
        
        return np.dot(features, weights)
    
    def _calculate_confidence(self, student: Student, teacher: Teacher) -> float:
        """Calculate confidence in the match"""
        confidence_factors = []
        
        # Data completeness
        student_completeness = sum([
            bool(student.subjects),
            bool(student.availability),
            bool(student.learning_style),
            student.budget_range[0] > 0
        ]) / 4.0
        
        teacher_completeness = sum([
            bool(teacher.subjects),
            bool(teacher.availability),
            teacher.total_students > 0,
            teacher.rating > 0
        ]) / 4.0
        
        confidence_factors.extend([student_completeness, teacher_completeness])
        
        # Teacher track record
        track_record = min(teacher.total_students / 20.0, 1.0)
        confidence_factors.append(track_record)
        
        return np.mean(confidence_factors)
    
    def _generate_reasons(self, student: Student, teacher: Teacher, content_score: float) -> List[str]:
        """Generate human-readable reasons for the match"""
        reasons = []
        
        # Subject match
        subject_overlap = set(student.subjects) & set(teacher.subjects)
        if subject_overlap:
            reasons.append(f"Teaches {', '.join(list(subject_overlap)[:3])}")
        
        # Schedule compatibility
        schedule_overlap = set(student.availability) & set(teacher.availability)
        if schedule_overlap:
            reasons.append(f"Available during your preferred times")
        
        # Budget
        if student.budget_range[0] <= teacher.hourly_rate <= student.budget_range[1]:
            reasons.append("Within your budget range")
        
        # High rating
        if teacher.rating >= 4.5:
            reasons.append(f"Highly rated ({teacher.rating}/5.0)")
        
        # Experience
        if teacher.experience_years >= 5:
            reasons.append(f"{teacher.experience_years} years of experience")
        
        # Teaching style match
        if self.feature_engineer._calculate_style_compatibility(
            student.learning_style, teacher.teaching_style) >= 0.8:
            reasons.append("Compatible teaching style")
        
        return reasons[:4]  # Limit to top 4 reasons
    
    def update_feedback(self, student_id: str, teacher_id: str, rating: float, 
                       lesson_completed: bool):
        """Update model with feedback data"""
        feedback_data = {
            'student_id': student_id,
            'teacher_id': teacher_id,
            'rating': rating,
            'lesson_completed': lesson_completed,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in Redis for real-time updates
        feedback_key = f"feedback:{student_id}:{teacher_id}:{datetime.now().isoformat()}"
        self.redis_client.setex(feedback_key, timedelta(days=30), json.dumps(feedback_data))
        
        self.logger.info(f"Feedback recorded: {feedback_data}")

# Usage Example and Testing
if __name__ == "__main__":
    # Sample data
    students = [
        Student(
            id="s1",
            subjects=["math", "physics"],
            learning_style="visual",
            availability=["morning", "evening"],
            location_preference="online",
            budget_range=(20.0, 40.0),
            experience_level="intermediate"
        )
    ]
    
    teachers = [
        Teacher(
            id="t1",
            subjects=["math", "algebra"],
            teaching_style="visual",
            availability=["morning", "afternoon"],
            location_preference="online",
            hourly_rate=25.0,
            experience_years=5,
            rating=4.8,
            total_students=50,
            specializations=["calculus"],
            gender="female",
            languages=["english"]
        ),
        Teacher(
            id="t2",
            subjects=["physics", "chemistry"],
            teaching_style="hands_on",
            availability=["evening"],
            location_preference="online",
            hourly_rate=35.0,
            experience_years=8,
            rating=4.6,
            total_students=75,
            specializations=["quantum_physics"],
            gender="male",
            languages=["english", "spanish"]
        )
    ]
    
    # Initialize matching engine
    matching_engine = MatchingEngine()
    
    # Sample interaction data for collaborative filtering
    interaction_data = pd.DataFrame({
        'student_id': ['s1', 's1', 's2', 's2'],
        'teacher_id': ['t1', 't2', 't1', 't2'],
        'rating': [4.5, 3.8, 4.9, 4.2]
    })
    
    # Train the model
    matching_engine.train(interaction_data)
    
    # Find matches
    matches = matching_engine.find_matches(students[0], teachers)
    
    print("Top Matches:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. Teacher {match.teacher_id}")
        print(f"   Score: {match.compatibility_score:.3f}")
        print(f"   Confidence: {match.confidence:.3f}")
        print(f"   Reasons: {', '.join(match.reasons)}")
        print()