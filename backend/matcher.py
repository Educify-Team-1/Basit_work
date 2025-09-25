# backend/matcher.py
"""
MatchingEngine:
 - trains from teachers.csv (+ optional students.csv, interactions.csv)
 - saves/loads model to backend/data/model.pkl
 - performs content-based matching combining subject overlap + teacher signals (rating, experience, popularity)
Designed for demo/MVP and safe to deploy on Render.
"""

import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_MODEL_PATH = os.path.join(DATA_DIR, "model.pkl")


# -------------------------
# Data classes
# -------------------------
@dataclass
class Teacher:
    id: str
    subjects: List[str]
    teaching_style: str = ""
    availability: List[str] = None
    location_preference: str = ""
    hourly_rate: float = 0.0
    experience_years: float = 0.0
    rating: float = 0.0
    total_students: int = 0
    specializations: List[str] = None
    gender: str = ""
    languages: List[str] = None


@dataclass
class Student:
    id: str
    subjects: List[str]
    learning_style: str = ""
    availability: List[str] = None
    location_preference: str = ""
    budget_max: float = 0.0
    experience_level: str = "beginner"
    preferred_teacher_gender: Optional[str] = None
    age: Optional[int] = None


@dataclass
class MatchResult:
    teacher_id: str
    student_id: str
    compatibility_score: float
    confidence: float
    reasons: List[str]


# -------------------------
# Matching engine
# -------------------------
class MatchingEngine:
    def __init__(self):
        # vocab and teacher storage
        self.subject_vocab: List[str] = []
        self.teacher_ids: List[str] = []                       # ordering of teachers in matrices
        self.teacher_subject_matrix: np.ndarray = np.zeros((0, 0))  # shape: (n_teachers, n_vocab)
        self.teacher_meta: Dict[str, Dict[str, Any]] = {}      # raw + normalized meta per teacher

        # normalization params (min,max) used for numeric features
        self._norm_params: Dict[str, Tuple[float, float]] = {}

    # ---------- Utilities ----------
    @staticmethod
    def _clean_subjects_field(s: Any) -> List[str]:
        if not s or (isinstance(s, float) and pd.isna(s)):
            return []
        if isinstance(s, list):
            seq = s
        else:
            seq = str(s).split(",")
        cleaned = [x.strip().lower() for x in seq if str(x).strip() != ""]
        return cleaned

    @staticmethod
    def _minmax_normalize(arr: List[float]) -> Tuple[List[float], float, float]:
        if len(arr) == 0:
            return [], 0.0, 0.0
        a = np.array(arr, dtype=float)
        mn = float(np.nanmin(a))
        mx = float(np.nanmax(a))
        if np.isclose(mx, mn):
            return [0.0 for _ in a], mn, mx
        normed = ((a - mn) / (mx - mn)).tolist()
        return normed, mn, mx

    @staticmethod
    def _cosine_sim_vectorized(A: np.ndarray, vec: np.ndarray) -> np.ndarray:
        # A: (n, d), vec: (d,)
        if vec is None or vec.size == 0:
            return np.zeros((A.shape[0],), dtype=float)
        denom = (np.linalg.norm(A, axis=1) * (np.linalg.norm(vec) + 1e-12)) + 1e-12
        num = A.dot(vec)
        return num / denom

    # ---------- Training ----------
    def fit_from_csv(self,
                     teachers_csv_path: str,
                     students_csv_path: Optional[str] = None,
                     interactions_csv_path: Optional[str] = None,
                     save_path: Optional[str] = None):
        """
        Build the subject vocab, teacher subject matrix, and compute normalized teacher signals.
        Save model to save_path (or default).
        """
        teachers_df = pd.read_csv(teachers_csv_path).fillna("")
        students_df = None
        if students_csv_path and os.path.exists(students_csv_path):
            students_df = pd.read_csv(students_csv_path).fillna("")

        interactions_df = None
        if interactions_csv_path and os.path.exists(interactions_csv_path):
            interactions_df = pd.read_csv(interactions_csv_path).fillna("")

        # Build subject vocabulary from both teachers and students (if available)
        subjects_sets = []
        for _, r in teachers_df.iterrows():
            subjects_sets.append(self._clean_subjects_field(r.get("subjects", "")))
        if students_df is not None:
            for _, r in students_df.iterrows():
                subjects_sets.append(self._clean_subjects_field(r.get("subjects", "")))

        vocab = sorted({s for ss in subjects_sets for s in ss})
        self.subject_vocab = vocab

        # Precompute per-teacher subject vectors
        teacher_ids = []
        subj_vectors = []
        ratings = []
        experiences = []
        hourly_rates = []
        total_students = []

        # gather base arrays from teachers_df
        for _, r in teachers_df.iterrows():
            tid = str(r.get("id"))
            teacher_ids.append(tid)
            subs = self._clean_subjects_field(r.get("subjects", ""))
            vec = [1.0 if s in subs else 0.0 for s in self.subject_vocab]
            subj_vectors.append(vec)

            # numeric stats (safe parse)
            try:
                ratings.append(float(r.get("rating", 0.0) or 0.0))
            except:
                ratings.append(0.0)
            try:
                experiences.append(float(r.get("experience_years", 0.0) or 0.0))
            except:
                experiences.append(0.0)
            try:
                hourly_rates.append(float(r.get("hourly_rate", 0.0) or 0.0))
            except:
                hourly_rates.append(0.0)
            try:
                total_students.append(int(r.get("total_students", 0) or 0))
            except:
                total_students.append(0)

        # interactions -> compute counts and avg_rating per teacher if available
        pop_count = [0 for _ in teacher_ids]
        pop_avg_rating = [0.0 for _ in teacher_ids]
        if interactions_df is not None and not interactions_df.empty:
            grouped = interactions_df.groupby("teacher_id").agg(
                count=("teacher_id", "count"),
                avg_rating=("rating", "mean")
            ).to_dict()
            # safer way - map by teacher id
            g = interactions_df.groupby("teacher_id").agg(count=("teacher_id", "count"), avg_rating=("rating", "mean"))
            counts_map = g["count"].to_dict()
            avg_map = g["avg_rating"].to_dict()
            id_to_index = {tid: i for i, tid in enumerate(teacher_ids)}
            for tid, cnt in counts_map.items():
                if tid in id_to_index:
                    pop_count[id_to_index[tid]] = int(cnt)
            for tid, ar in avg_map.items():
                if tid in id_to_index:
                    pop_avg_rating[id_to_index[tid]] = float(ar)

        # Normalize numeric features using min-max
        rating_normed, r_min, r_max = self._minmax_normalize(ratings)
        exp_normed, e_min, e_max = self._minmax_normalize(experiences)
        hr_normed, h_min, h_max = self._minmax_normalize(hourly_rates)
        tot_normed, t_min, t_max = self._minmax_normalize(total_students)
        pop_normed, p_min, p_max = self._minmax_normalize(pop_count)
        popavg_normed, pa_min, pa_max = self._minmax_normalize(pop_avg_rating)

        # Save normalization params
        self._norm_params = {
            "rating": (r_min, r_max),
            "experience_years": (e_min, e_max),
            "hourly_rate": (h_min, h_max),
            "total_students": (t_min, t_max),
            "pop_count": (p_min, p_max),
            "pop_avg_rating": (pa_min, pa_max),
        }

        # Build teacher meta + subject matrix
        subj_matrix = np.array(subj_vectors, dtype=float) if subj_vectors else np.zeros((0, len(self.subject_vocab)))
        self.teacher_subject_matrix = subj_matrix
        self.teacher_ids = teacher_ids
        self.teacher_meta = {}

        for i, tid in enumerate(teacher_ids):
            # find original row to get raw fields
            row = teachers_df[teachers_df["id"].astype(str) == str(tid)]
            raw = row.iloc[0].to_dict() if not row.empty else {}

            self.teacher_meta[tid] = {
                # raw fields (safe defaults)
                "id": tid,
                "subjects": self._clean_subjects_field(raw.get("subjects", "")),
                "teaching_style": raw.get("teaching_style", "") or "",
                "availability": self._clean_subjects_field(raw.get("availability", "")),
                "location_preference": raw.get("location_preference", "") or "",
                "hourly_rate": float(raw.get("hourly_rate") or 0.0),
                "experience_years": float(raw.get("experience_years") or 0.0),
                "rating": float(raw.get("rating") or 0.0),
                "total_students": int(raw.get("total_students") or 0),
                "specializations": self._clean_subjects_field(raw.get("specializations", "")),
                "gender": raw.get("gender", "") or "",
                "languages": self._clean_subjects_field(raw.get("languages", "")),
                # normalized signals (0..1)
                "rating_norm": float(rating_normed[i]) if rating_normed else 0.0,
                "experience_norm": float(exp_normed[i]) if exp_normed else 0.0,
                "hourly_norm": float(hr_normed[i]) if hr_normed else 0.0,
                "total_students_norm": float(tot_normed[i]) if tot_normed else 0.0,
                "pop_count": int(pop_count[i]) if pop_count else 0,
                "pop_count_norm": float(pop_normed[i]) if pop_normed else 0.0,
                "pop_avg_rating": float(pop_avg_rating[i]) if pop_avg_rating else 0.0,
                "pop_avg_rating_norm": float(popavg_normed[i]) if popavg_normed else 0.0,
            }

        # Persist after building
        out_path = save_path or DEFAULT_MODEL_PATH
        self.save(out_path)

    # ---------- Save / Load ----------
    def save(self, path: Optional[str] = None):
        path = path or DEFAULT_MODEL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "subject_vocab": self.subject_vocab,
            "teacher_ids": self.teacher_ids,
            "teacher_subject_matrix": self.teacher_subject_matrix,
            "teacher_meta": self.teacher_meta,
            "_norm_params": self._norm_params,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f)

    def load(self, path: Optional[str] = None) -> bool:
        path = path or DEFAULT_MODEL_PATH
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            payload = pickle.load(f)
        self.subject_vocab = payload.get("subject_vocab", [])
        self.teacher_ids = payload.get("teacher_ids", [])
        self.teacher_subject_matrix = payload.get("teacher_subject_matrix", np.zeros((0, len(self.subject_vocab))))
        self.teacher_meta = payload.get("teacher_meta", {})
        self._norm_params = payload.get("_norm_params", {})
        return True

    # ---------- Matching ----------
    def _student_to_subject_vector(self, subjects: List[str]) -> np.ndarray:
        vec = np.zeros(len(self.subject_vocab), dtype=float)
        if not subjects:
            return vec
        subj_clean = [s.strip().lower() for s in subjects if s and str(s).strip() != ""]
        for s in subj_clean:
            # exact match on vocab items; if not present ignore
            try:
                idx = self.subject_vocab.index(s)
                vec[idx] = 1.0
            except ValueError:
                continue
        return vec

    def find_matches(self, student: Student, top_k: int = 3, weights: Optional[Dict[str, float]] = None) -> List[MatchResult]:
        """
        Return top_k MatchResult for given student profile.
        weights default:
           sim=0.60, rating=0.15, exp=0.10, pop=0.05, avail=0.05, afford=0.05
        """
        if self.teacher_subject_matrix is None or self.teacher_subject_matrix.size == 0:
            return []

        # default weights
        if weights is None:
            weights = {"sim": 0.60, "rating": 0.15, "exp": 0.10, "pop": 0.05, "avail": 0.05, "afford": 0.05}

        # student subject vector
        s_vec = self._student_to_subject_vector(student.subjects or [])
        sims = self._cosine_sim_vectorized(self.teacher_subject_matrix, s_vec)  # shape (n_teachers,)

        results = []
        for i, tid in enumerate(self.teacher_ids):
            meta = self.teacher_meta.get(tid, {})
            sim = float(sims[i]) if len(sims) > i else 0.0

            # normalized signals (0..1)
            rnorm = float(meta.get("rating_norm", 0.0))
            expnorm = float(meta.get("experience_norm", 0.0))
            popnorm = float(meta.get("pop_count_norm", 0.0))

            # availability match
            avail_bonus = 0.0
            try:
                teacher_avail = set(meta.get("availability", []))
                student_avail = set([a.strip().lower() for a in (student.availability or []) if a.strip() != ""])
                if teacher_avail and student_avail and len(teacher_avail & student_avail) > 0:
                    avail_bonus = 1.0
            except Exception:
                avail_bonus = 0.0

            # affordability (student budget_max vs teacher hourly_rate)
            afford = 0.0
            teacher_hourly = float(meta.get("hourly_rate", 0.0) or 0.0)
            student_budget = float(getattr(student, "budget_max", 0.0) or 0.0)
            if teacher_hourly <= 0:
                afford = 1.0
            else:
                # fraction student can afford (cap to 1)
                afford = min(1.0, student_budget / (teacher_hourly + 1e-9))

            # final score (weighted sum)
            score = (
                weights["sim"] * sim +
                weights["rating"] * rnorm +
                weights["exp"] * expnorm +
                weights["pop"] * popnorm +
                weights["avail"] * avail_bonus +
                weights["afford"] * afford
            )

            # build reasons list
            reasons = []
            shared = set([s.lower() for s in meta.get("subjects", [])]) & set([s.lower() for s in (student.subjects or [])])
            if shared:
                reasons.append(f"Shared subjects: {', '.join(sorted(shared))}")
            if meta.get("rating"):
                reasons.append(f"Teacher rating: {meta.get('rating'):.2f}")
            if meta.get("experience_years"):
                reasons.append(f"Experience: {meta.get('experience_years')} yrs")
            if afford >= 1.0:
                reasons.append("Within student's budget")
            else:
                # indicate affordability hint
                if teacher_hourly > 0:
                    reasons.append(f"Hourly rate {teacher_hourly:.2f} vs budget {student_budget:.2f}")

            # confidence: scale score into 0..1 (already roughly in 0..1 but clamp)
            confidence = float(max(0.0, min(score, 1.0)))

            results.append(MatchResult(
                teacher_id=tid,
                student_id=student.id or "",
                compatibility_score=float(score),
                confidence=confidence,
                reasons=reasons
            ))

        # sort and return top_k
        results_sorted = sorted(results, key=lambda x: x.compatibility_score, reverse=True)
        return results_sorted[:top_k]
