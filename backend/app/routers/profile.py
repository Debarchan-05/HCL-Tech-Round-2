from fastapi import APIRouter, HTTPException
from app.models.schemas import LearnerProfile
from app.services import profiling

router = APIRouter(prefix="/api/profile", tags=["Learner Profiling"])


@router.get("/{learner_id}", response_model=LearnerProfile)
def get_profile(learner_id: str):
    return profiling.get_profile(learner_id)


@router.put("/{learner_id}", response_model=LearnerProfile)
def update_profile(learner_id: str, profile: LearnerProfile):
    if profile.learner_id != learner_id:
        raise HTTPException(400, "learner_id mismatch between path and body")
    profiling.save_profile(profile)
    return profile


@router.post("/{learner_id}/reset", response_model=LearnerProfile)
def reset_profile(learner_id: str):
    fresh = LearnerProfile(learner_id=learner_id)
    profiling.save_profile(fresh)
    return fresh
