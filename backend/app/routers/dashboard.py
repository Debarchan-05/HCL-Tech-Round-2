from fastapi import APIRouter
from app.models.schemas import DashboardResponse
from app.services import profiling, recommendation, path_generator

router = APIRouter(prefix="/api/dashboard", tags=["Progress Dashboard"])


@router.get("/{learner_id}", response_model=DashboardResponse)
def get_dashboard(learner_id: str):
    profile = profiling.get_profile(learner_id)
    path = path_generator.generate_path(profile)

    total = len(path.steps) + len(profile.completed_course_ids)
    completed = len(profile.completed_course_ids)
    pct = round((completed / total) * 100, 1) if total else 0.0

    known = recommendation.get_known_skill_set(profile)
    target = set(recommendation.get_target_skills(profile))
    skills_remaining = sorted(target - known)

    hours_completed = sum(
        recommendation.get_course(cid)["duration_hours"]
        for cid in profile.completed_course_ids
        if recommendation.get_course(cid)
    )
    hours_remaining = path.total_duration_hours

    next_actions = [s.course for s in path.steps if s.status == "available"][:3]

    # Build a simple milestone timeline: group path steps by milestone stage
    milestone_order = ["Foundations", "Core Skills", "Applied Practice", "Mastery"]
    timeline = []
    for m in milestone_order:
        steps_in_stage = [s for s in path.steps if s.milestone == m]
        if not steps_in_stage:
            continue
        timeline.append({
            "milestone": m,
            "course_count": len(steps_in_stage),
            "hours": sum(s.course.duration_hours for s in steps_in_stage),
            "courses": [s.course.title for s in steps_in_stage],
        })

    return DashboardResponse(
        learner_id=learner_id,
        goal_title=profile.matched_goal_title,
        total_courses=total,
        completed_courses=completed,
        completion_pct=pct,
        skills_acquired=sorted(known),
        skills_remaining=skills_remaining,
        hours_completed=hours_completed,
        hours_remaining=hours_remaining,
        next_actions=next_actions,
        milestone_timeline=timeline,
    )
