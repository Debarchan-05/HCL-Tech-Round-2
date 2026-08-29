from fastapi import APIRouter
from typing import List
from app.models.schemas import RecommendationItem, CourseOut
from app.services import profiling, recommendation

router = APIRouter(prefix="/api/recommendations", tags=["Recommendation Engine"])


@router.get("/{learner_id}", response_model=List[RecommendationItem])
def get_recommendations(learner_id: str, top_k: int = 8):
    profile = profiling.get_profile(learner_id)
    return recommendation.recommend_courses(profile, top_k=top_k)


@router.get("/catalog/all", response_model=List[CourseOut])
def get_full_catalog():
    """Browse the entire course catalog (useful for the UI's explore view)."""
    return recommendation.list_all_courses()
