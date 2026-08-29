from fastapi import APIRouter, HTTPException
from app.models.schemas import LearningPath, ProgressUpdate, LearnerProfile
from app.services import profiling, path_generator, recommendation

router = APIRouter(prefix="/api/path", tags=["Learning Path Generator"])


@router.get("/{learner_id}", response_model=LearningPath)
def get_path(learner_id: str):
    profile = profiling.get_profile(learner_id)
    return path_generator.generate_path(profile)


@router.post("/progress", response_model=LearningPath)
def update_progress(update: ProgressUpdate):
    """
    Record progress on a course and return the REGENERATED path.
    This is the adaptivity hook: completing a course updates known
    skills, which re-scores and re-sequences everything downstream —
    satisfying the requirement to "adapt suggestions based on user
    feedback and progress."
    """
    profile = profiling.get_profile(update.learner_id)

    if recommendation.get_course(update.course_id) is None:
        raise HTTPException(404, "course not found")

    if update.status == "completed":
        profile = profiling.mark_course_completed(update.learner_id, update.course_id)

    # Feedback-driven adaptation: shift pace/level signal based on how the
    # learner rated the difficulty of the course they just engaged with.
    if update.feedback == "too_hard":
        # Nudge experience level down a notch if not already beginner —
        # future recommendations will lean toward reinforcing fundamentals.
        if profile.experience_level == "advanced":
            profile.experience_level = "intermediate"
        elif profile.experience_level == "intermediate":
            profile.experience_level = "beginner"
    elif update.feedback == "too_easy":
        if profile.experience_level == "beginner":
            profile.experience_level = "intermediate"
        elif profile.experience_level == "intermediate":
            profile.experience_level = "advanced"

    profiling.save_profile(profile)
    return path_generator.generate_path(profile)
