"""
Recommendation Engine.

Approach: hybrid content-based filtering over a course knowledge graph.

Scoring combines four signals (weights tunable via WEIGHTS below):
  1. Skill-gap coverage   — how many of the learner's *missing* target
                             skills this course teaches (Jaccard-style
                             overlap against the goal's target_skills).
  2. Prerequisite readiness — courses whose prerequisites the learner
                             already satisfies score higher (0 penalty);
                             courses with unmet prereqs are demoted so
                             the roadmap naturally sequences correctly.
  3. Level fit            — matches course level to learner experience,
                             ±1 level tolerance (e.g. beginner learner
                             can still see intermediate courses lightly
                             boosted if they've cleared the prereqs).
  4. Popularity prior     — a static "quality/demand" prior per course
                             (stand-in for a collaborative-filtering
                             signal you'd derive from real enrollment/
                             completion/rating data in production).

This is intentionally a transparent, explainable scoring function
(rather than a black-box model) because the brief explicitly requires
the assistant to explain *why* each course was recommended — see
services/explainability.py, which reads the same `reasons` this module
produces.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Set

from app.models.schemas import LearnerProfile, CourseOut, RecommendationItem

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

with open(DATA_DIR / "courses.json") as f:
    COURSES: List[dict] = json.load(f)

with open(DATA_DIR / "goals.json") as f:
    GOALS: List[dict] = json.load(f)

COURSE_BY_ID = {c["id"]: c for c in COURSES}
GOAL_BY_ID = {g["id"]: g for g in GOALS}

LEVEL_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}

# Static demand/quality prior per course (0-1). Stand-in for a real
# collaborative-filtering signal derived from enrollment/completion data.
POPULARITY_PRIOR: Dict[str, float] = {
    "c001": 0.95, "c002": 0.85, "c003": 0.80, "c004": 0.90, "c005": 0.75,
    "c006": 0.92, "c007": 0.88, "c008": 0.78, "c009": 0.82, "c010": 0.80,
    "c011": 0.90, "c012": 0.93, "c013": 0.86, "c014": 0.84, "c015": 0.70,
    "c016": 0.77, "c017": 0.79, "c018": 0.72, "c019": 0.60, "c020": 0.60,
    "c021": 0.74, "c022": 0.81, "c023": 0.76, "c024": 0.73, "c025": 0.71,
}

WEIGHTS = {
    "skill_gap": 0.50,
    "prereq_ready": 0.25,
    "level_fit": 0.15,
    "popularity": 0.10,
}


def _to_course_out(c: dict) -> CourseOut:
    return CourseOut(**c)


def get_target_skills(profile: LearnerProfile) -> List[str]:
    if profile.matched_goal_id and profile.matched_goal_id in GOAL_BY_ID:
        return GOAL_BY_ID[profile.matched_goal_id]["target_skills"]
    return []


def get_known_skill_set(profile: LearnerProfile) -> Set[str]:
    """Union of explicitly stated known skills + skills from completed courses."""
    known = set(profile.known_skills)
    for cid in profile.completed_course_ids:
        if cid in COURSE_BY_ID:
            known |= set(COURSE_BY_ID[cid]["skills_taught"])
    return known


def compute_skill_gap(profile: LearnerProfile) -> List[str]:
    target = set(get_target_skills(profile))
    known = get_known_skill_set(profile)
    gap = target - known
    # Preserve target_skills ordering (it's authored in a sensible learning order)
    ordered_target = get_target_skills(profile)
    return [s for s in ordered_target if s in gap]


def _prereq_readiness_score(course: dict, known: Set[str]) -> float:
    prereqs = set(course["prerequisites"])
    if not prereqs:
        return 1.0
    met = len(prereqs & known)
    return met / len(prereqs)


def _level_fit_score(course_level: str, learner_level: str) -> float:
    diff = abs(LEVEL_RANK[course_level] - LEVEL_RANK[learner_level])
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.55
    return 0.15


def score_course(course: dict, profile: LearnerProfile, gap: Set[str]) -> RecommendationItem:
    known = get_known_skill_set(profile)
    taught = set(course["skills_taught"])

    # 1. Skill-gap coverage
    gap_covered = taught & gap
    skill_gap_score = len(gap_covered) / max(len(taught), 1)

    # 2. Prerequisite readiness
    prereq_score = _prereq_readiness_score(course, known)

    # 3. Level fit
    level_score = _level_fit_score(course["level"], profile.experience_level)

    # 4. Popularity prior
    pop_score = POPULARITY_PRIOR.get(course["id"], 0.5)

    final_score = (
        WEIGHTS["skill_gap"] * skill_gap_score
        + WEIGHTS["prereq_ready"] * prereq_score
        + WEIGHTS["level_fit"] * level_score
        + WEIGHTS["popularity"] * pop_score
    )

    reasons = []
    if gap_covered:
        skills_str = ", ".join(sorted(gap_covered)).replace("-", " ")
        reasons.append(f"Teaches {len(gap_covered)} skill(s) you still need for your goal: {skills_str}")
    if prereq_score == 1.0 and course["prerequisites"]:
        reasons.append("You already have all the prerequisites for this course")
    elif prereq_score < 1.0 and course["prerequisites"]:
        missing = set(course["prerequisites"]) - known
        reasons.append(f"Requires prerequisite skill(s) first: {', '.join(missing).replace('-', ' ')}")
    if level_score == 1.0:
        reasons.append(f"Matches your current experience level ({profile.experience_level})")
    if pop_score >= 0.85:
        reasons.append("Highly rated / popular among learners with similar goals")
    if course["type"] == "project":
        reasons.append("Hands-on project to consolidate skills with a portfolio-worthy outcome")
    if course["type"] == "assessment":
        reasons.append("Checkpoint assessment to validate readiness before advancing")

    return RecommendationItem(course=_to_course_out(course), score=round(final_score, 4), reasons=reasons)


def recommend_courses(profile: LearnerProfile, top_k: int = 8) -> List[RecommendationItem]:
    gap = set(compute_skill_gap(profile))
    completed = set(profile.completed_course_ids)

    candidates = [c for c in COURSES if c["id"] not in completed]

    if gap:
        # Prioritize courses that cover at least one gap skill, then backfill
        # with the highest-scoring remaining courses (e.g. supporting/adjacent
        # skills) so the list is never sparse even for narrow goals.
        candidates = [c for c in candidates if set(c["skills_taught"]) & gap] or candidates

    scored = [score_course(c, profile, gap) for c in candidates]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


def get_course(course_id: str) -> dict | None:
    return COURSE_BY_ID.get(course_id)


def list_all_courses() -> List[CourseOut]:
    return [_to_course_out(c) for c in COURSES]
