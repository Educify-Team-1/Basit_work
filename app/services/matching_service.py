from typing import List, Tuple, Optional
from datetime import datetime
from app.models.student import Student, TimeSlot
from app.models.teacher import Teacher
from app.models.match import TeacherMatch, MatchScore, MatchResponse
from app.core.logging import logger
from app.core.config import settings


class MatchingService:
    def __init__(self):
        self.rating_weight = settings.RATING_WEIGHT
        self.availability_weight = settings.AVAILABILITY_WEIGHT
    
    def find_matches(self, student: Student, teachers: List[Teacher],
                     subject: str, max_matches: int = None) -> MatchResponse:
        max_matches = max_matches or settings.MAX_MATCHES
        logger.info(f"Finding matches for student {student.id} for {subject}")
        
        candidates = self._filter_by_subject(teachers, subject)
        logger.info(f"After subject filter: {len(candidates)}")
        if not candidates:
            return self._no_match_response(student.id, subject, "No teachers for this subject")
        
        candidates = self._filter_by_budget(candidates, student.budget)
        logger.info(f"After budget filter: {len(candidates)}")
        if not candidates:
            return self._no_match_response(student.id, subject, "No teachers within budget")
        
        candidates_with_avail = self._filter_by_availability(candidates, student.availability)
        logger.info(f"After availability filter: {len(candidates_with_avail)}")
        if not candidates_with_avail:
            return self._no_match_response(student.id, subject, "No teachers available")
        
        scored_matches = []
        for teacher, matching_slots in candidates_with_avail:
            score = self._calculate_match_score(student, teacher, matching_slots)
            match = TeacherMatch(
                teacher=teacher,
                score=score,
                matching_subjects=[subject],
                matching_time_slots=matching_slots,
                recommended_reason=self._generate_reason(teacher, score)
            )
            scored_matches.append(match)
        
        scored_matches.sort(key=lambda x: x.score.overall_score, reverse=True)
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
        return [t for t in teachers if subject in t.subjects]
    
    def _filter_by_budget(self, teachers: List[Teacher], budget: float) -> List[Teacher]:
        return [t for t in teachers if t.hourly_rate <= budget]
    
    def _filter_by_availability(self, teachers: List[Teacher],
                                student_slots: List[TimeSlot]) -> List[Tuple[Teacher, List[TimeSlot]]]:
        matches = []
        for teacher in teachers:
            matching_slots = self._find_overlapping_slots(student_slots, teacher.availability)
            if matching_slots:
                matches.append((teacher, matching_slots))
        return matches
    
    def _find_overlapping_slots(self, student_slots: List[TimeSlot],
                                teacher_slots: List[TimeSlot]) -> List[TimeSlot]:
        overlapping = []
        for s_slot in student_slots:
            for t_slot in teacher_slots:
                if s_slot.day == t_slot.day:
                    overlap = self._calculate_time_overlap(s_slot, t_slot)
                    if overlap:
                        overlapping.append(overlap)
        return overlapping
    
    def _calculate_time_overlap(self, slot1: TimeSlot, slot2: TimeSlot) -> Optional[TimeSlot]:
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
    
    def _calculate_match_score(self, student: Student, teacher: Teacher,
                               matching_slots: List[TimeSlot]) -> MatchScore:
        rating_score = (teacher.rating / 5.0) * 100
        availability_score = min(len(matching_slots) * 25, 100)
        overall_score = (rating_score * self.rating_weight +
                        availability_score * self.availability_weight)
        
        return MatchScore(
            overall_score=round(overall_score, 2),
            rating_score=round(rating_score, 2),
            availability_score=round(availability_score, 2),
            subject_match=True,
            budget_match=teacher.hourly_rate <= student.budget
        )
    
    def _generate_reason(self, teacher: Teacher, score: MatchScore) -> str:
        reasons = []
        if teacher.rating >= 4.5:
            reasons.append(f"Highly rated ({teacher.rating}/5.0)")
        if teacher.experience_years >= 5:
            reasons.append(f"{teacher.experience_years} years experience")
        if score.availability_score >= 75:
            reasons.append("Excellent availability")
        return " • ".join(reasons) if reasons else "Good match"
    
    def _no_match_response(self, student_id: str, subject: str, message: str) -> MatchResponse:
        return MatchResponse(
            success=False,
            student_id=student_id,
            subject=subject,
            matches=[],
            total_matches=0,
            message=message
        )