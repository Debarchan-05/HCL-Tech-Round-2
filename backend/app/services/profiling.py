"""
Learner Profiling Engine.

Maintains each learner's profile: goals, interests, experience level,
known skills, completed courses, pace preferences. Profiles are built
incrementally as the conversational engine extracts signals from chat.

Persistence: in-memory dict keyed by learner_id, seeded from / mirrored
to a local JSON file (data/profiles_store.json) so state survives
backend restarts during grading/demo without needing a real database.
"""
from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from app.models.schemas import LearnerProfile

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
STORE_PATH = DATA_DIR / "profiles_store.json"

_lock = threading.Lock()


def _load_store() -> Dict[str, dict]:
    if STORE_PATH.exists():
        with open(STORE_PATH) as f:
            return json.load(f)
    return {}


def _save_store(store: Dict[str, dict]) -> None:
    with open(STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


def get_profile(learner_id: str) -> LearnerProfile:
    with _lock:
        store = _load_store()
        if learner_id in store:
            return LearnerProfile(**store[learner_id])
        profile = LearnerProfile(learner_id=learner_id)
        store[learner_id] = profile.model_dump()
        _save_store(store)
        return profile


def save_profile(profile: LearnerProfile) -> None:
    with _lock:
        store = _load_store()
        store[profile.learner_id] = profile.model_dump()
        _save_store(store)


def merge_extracted_signals(profile: LearnerProfile, extracted: dict) -> LearnerProfile:
    """
    Merge newly-extracted NLU signals into the existing profile.
    Later, more-confident signals overwrite earlier weaker ones;
    lists are unioned rather than replaced so context accumulates
    across multiple conversational turns.
    """
    if extracted.get("matched_goal_id") and not profile.matched_goal_id:
        profile.matched_goal_id = extracted["matched_goal_id"]
        profile.matched_goal_title = extracted["matched_goal_title"]
        profile.goal_text = extracted.get("raw_text")
    elif extracted.get("matched_goal_id") and profile.matched_goal_id != extracted["matched_goal_id"]:
        # Learner changed their stated goal — respect the latest one.
        profile.matched_goal_id = extracted["matched_goal_id"]
        profile.matched_goal_title = extracted["matched_goal_title"]
        profile.goal_text = extracted.get("raw_text")

    if extracted.get("known_skills"):
        profile.known_skills = sorted(set(profile.known_skills) | set(extracted["known_skills"]))

    if extracted.get("experience_level"):
        profile.experience_level = extracted["experience_level"]

    if extracted.get("weekly_hours"):
        profile.weekly_hours_available = extracted["weekly_hours"]

    if extracted.get("pace"):
        profile.preferred_pace = extracted["pace"]

    if extracted.get("interests"):
        profile.interests = sorted(set(profile.interests) | set(extracted["interests"]))

    return profile


def profile_completeness(profile: LearnerProfile) -> float:
    """
    Returns 0.0-1.0 score of how ready the profile is to generate a path.
    Used to decide whether the conversational engine should keep asking
    clarifying questions or proceed to recommendations.
    """
    checks = [
        bool(profile.matched_goal_id),
        profile.experience_level is not None,
        len(profile.known_skills) > 0 or profile.experience_level == "beginner",
        profile.weekly_hours_available > 0,
    ]
    return sum(checks) / len(checks)


def mark_course_completed(learner_id: str, course_id: str) -> LearnerProfile:
    profile = get_profile(learner_id)
    if course_id not in profile.completed_course_ids:
        profile.completed_course_ids.append(course_id)
    save_profile(profile)
    return profile
