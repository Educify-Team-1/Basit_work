from typing import List, Tuple
from datetime import datetime, time
from app.models.student import Student, TimeSlot
from app.models.teacher import Teacher
from app.models.match import TeacherMatch, MatchScore, MatchResponse
from app.core.logging import logger
from app.core.config import settings
from typing import List, Optional



class MatchingService:
    """Core matching logic for student-teacher pairing"""
    
    def __init__(self):
        self.rating_weight = settings.RATING_WEIGHT
        self.availability_weight = settings.AVAILABILITY_WEIGHT
    
    def find_matches(self, 
                     student: Student, 
                     teachers: List[Teacher],
                     subject: str,
                     max_matches: int = None) -> MatchResponse:
        """
        Find best teacher matches for a student
        
        Algorithm:
        1. Filter by subject
        2. Filter by budget
        3. Filter by availability overlap
        4. Score remaining candidates
        5. Return top N matches
        """
        max_matches = max_matches or settings.MAX_MATCHES
        
        logger.info(f"Finding matches for student {student.id} for subject {subject}")
        
        # Phase 1: Rule-based filtering
        candidates = self._filter_by_subject(teachers, subject)
        logger.info(f"After subject filter: {len(candidates)} candidates")
        
        if not candidates:
            return self._no_match_response(student.id, subject, "No teachers found for this subject")
        
        candidates = self._filter_by_budget(candidates, student.budget)
        logger.info(f"After budget filter: {len(candidates)} candidates")
        
        if not candidates:
            return self._no_match_response(student.id, subject, "No teachers within budget")
        
        candidates_with_availability = self._filter_by_availability(
            candidates, student.availability
        )
        logger.info(f"After availability filter: {len(candidates_with_availability)} candidates")
        
        if not candidates_with_availability:
            return self._no_match_response(
                student.id, subject, 
                "No teachers available at your preferred times"
            )
        
        # Phase 2: Score and rank
        scored_matches = []
        for teacher, matching_slots in candidates_with_availability:
            score = self._calculate_match_score(student, teacher, matching_slots)
            match = TeacherMatch(
                teacher=teacher,
                score=score,
                matching_subjects=[subject],
                matching_time_slots=matching_slots,
                recommended_reason=self._generate_recommendation_reason(teacher, score)
            )
            scored_matches.append(match)
        
        # Sort by overall score
        scored_matches.sort(key=lambda x: x.score.overall_score, reverse=True)
        
        # Return top N matches
        top_matches = scored_matches[:max_matches]
        
        return MatchResponse(
            success=True,
            student_id=student.id,
            subject=subject,
            matches=top_matches,
            total_matches=len(top_matches),
            message=f"Found {len(top_matches)} matching teachers"
        )
    
    def _filter_by_subject(self, teachers: List[Teacher], subject: str) -> List[Teacher]:
        """Filter teachers who teach the requested subject"""
        return [t for t in teachers if subject in t.subjects]
    
    def _filter_by_budget(self, teachers: List[Teacher], budget: float) -> List[Teacher]:
        """Filter teachers within student's budget"""
        return [t for t in teachers if t.hourly_rate <= budget]
    
    def _filter_by_availability(self, 
                                teachers: List[Teacher], 
                                student_slots: List[TimeSlot]) -> List[Tuple[Teacher, List[TimeSlot]]]:
        """
        Filter teachers with overlapping availability
        Returns list of (teacher, matching_slots) tuples
        """
        matches = []
        for teacher in teachers:
            matching_slots = self._find_overlapping_slots(student_slots, teacher.availability)
            if matching_slots:
                matches.append((teacher, matching_slots))
        return matches
    
    def _find_overlapping_slots(self, 
                                student_slots: List[TimeSlot], 
                                teacher_slots: List[TimeSlot]) -> List[TimeSlot]:
        """Find overlapping time slots between student and teacher"""
        overlapping = []
        for s_slot in student_slots:
            for t_slot in teacher_slots:
                if s_slot.day == t_slot.day:
                    overlap = self._calculate_time_overlap(s_slot, t_slot)
                    if overlap:
                        overlapping.append(overlap)
        return overlapping
    
    def _calculate_time_overlap(self, slot1: TimeSlot, slot2: TimeSlot) -> Optional[TimeSlot]:
        """Calculate overlap between two time slots"""
        start1 = datetime.strptime(slot1.start_time, "%H:%M").time()
        end1 = datetime.strptime(slot1.end_time, "%H:%M").time()
        start2 = datetime.strptime(slot2.start_time, "%H:%M").time()
        end2 = datetime.strptime(slot2.end_time, "%H:%M").time()
        
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start < overlap_end:
            return TimeSlot(
                day=slot1.day,
                start_time=overlap_start.strftime("%H:%M"),
                end_time=overlap_end.strftime("%H:%M")
            )
        return None
    
    def _calculate_match_score(self, 
                               student: Student, 
                               teacher: Teacher,
                               matching_slots: List[TimeSlot]) -> MatchScore:
        """
        Calculate match score based on multiple factors
        
        Future enhancement: This can be replaced with ML model predictions
        """
        # Rating score (normalized to 0-100)
        rating_score = (teacher.rating / 5.0) * 100
        
        # Availability score based on number of matching slots
        availability_score = min(len(matching_slots) * 25, 100)
        
        # Overall weighted score
        overall_score = (
            rating_score * self.rating_weight +
            availability_score * self.availability_weight
        )
        
        return MatchScore(
            overall_score=round(overall_score, 2),
            rating_score=round(rating_score, 2),
            availability_score=round(availability_score, 2),
            subject_match=True,
            budget_match=teacher.hourly_rate <= student.budget
        )
    
    def _generate_recommendation_reason(self, teacher: Teacher, score: MatchScore) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if teacher.rating >= 4.5:
            reasons.append(f"Highly rated ({teacher.rating}/5.0)")
        
        if teacher.experience_years >= 5:
            reasons.append(f"{teacher.experience_years} years experience")
        
        if score.availability_score >= 75:
            reasons.append("Excellent availability match")
        
        return " • ".join(reasons) if reasons else "Good match"
    
    def _no_match_response(self, student_id: str, subject: str, message: str) -> MatchResponse:
        """Generate response when no matches found"""
        return MatchResponse(
            success=False,
            student_id=student_id,
            subject=subject,
            matches=[],
            total_matches=0,
            message=message
        )
