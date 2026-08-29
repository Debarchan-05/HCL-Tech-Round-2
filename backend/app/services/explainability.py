"""
Explainability Engine.

Every recommendation must be explainable per the brief ("explain why
each recommendation was made and answer learner queries"). Rather than
a black-box model, the recommendation engine already produces
human-readable `reasons` alongside every score (see recommendation.py) —
this module formats those into a full explanation and also answers
free-form learner questions about the path (e.g. "why do I need SQL?",
"can I skip statistics?").
"""
from __future__ import annotations
from typing import List
import re

from app.models.schemas import LearnerProfile, WhyResponse
from app.services.recommendation import get_course, score_course, compute_skill_gap
from app.services.path_generator import generate_path


def explain_recommendation(profile: LearnerProfile, course_id: str) -> WhyResponse:
    course = get_course(course_id)
    if not course:
        return WhyResponse(course_id=course_id, course_title="Unknown course",
                            explanation="Course not found.", contributing_factors=[])

    gap = set(compute_skill_gap(profile))
    item = score_course(course, profile, gap)

    factors = item.reasons
    goal = profile.matched_goal_title or "your learning goal"
    narrative = (
        f"'{course['title']}' was recommended for your path toward {goal} "
        f"with a relevance score of {round(item.score * 100)}%. "
        + (" ".join(f"{r}." for r in factors) if factors else
           "It broadens your foundation in this domain.")
    )
    return WhyResponse(
        course_id=course_id,
        course_title=course["title"],
        explanation=narrative,
        contributing_factors=factors,
    )


# ---- Free-form Q&A about the path (rule-based intent matching) ----

QA_PATTERNS = [
    (r"\b(why|need|require).*\b(sql|python|statistics|react|docker|git)\b", "skill_reason"),
    (r"\bskip\b|\bcan i (avoid|miss)\b", "skip_question"),
    (r"\bhow long\b|\bhow much time\b|\bduration\b", "duration_question"),
    (r"\bwhat('s| is) next\b|\bnext step\b|\bwhat should i do\b", "next_step"),
    (r"\bstuck\b|\btoo hard\b|\bdifficult\b|\bconfus", "difficulty_help"),
    (r"\btoo easy\b|\bboring\b|\balready know\b", "too_easy"),
]


def _match_intent(text: str) -> str:
    text_l = text.lower()
    for pattern, intent in QA_PATTERNS:
        if re.search(pattern, text_l):
            return intent
    return "general"


def answer_query(profile: LearnerProfile, question: str) -> str:
    intent = _match_intent(question)
    path = generate_path(profile)

    if intent == "skill_reason":
        m = re.search(r"\b(sql|python|statistics|react|docker|git)\b", question.lower())
        skill = m.group(1) if m else None
        if skill:
            relevant_steps = [s for s in path.steps if skill in [x.lower() for x in s.course.skills_taught]]
            if relevant_steps:
                step = relevant_steps[0]
                return (f"{skill.title()} appears in your path because '{step.course.title}' teaches it, "
                        f"and it's one of the core skills required for {path.goal_title}. "
                        f"It unlocks {step.milestone.lower()}-stage courses later in your roadmap.")
        return f"That skill supports the target competencies needed for {path.goal_title}."

    if intent == "skip_question":
        locked = [s for s in path.steps if s.status == "locked"]
        if locked:
            return (f"Skipping ahead isn't recommended — '{locked[0].course.title}' currently requires "
                    f"skills you haven't covered yet ({', '.join(locked[0].unlocked_by) or 'earlier steps'}). "
                    "You're welcome to try, but you may find it harder without the foundation.")
        return "Your path is currently unblocked — you can attempt steps in a different order if you're confident, though the given sequence is optimized for a smoother learning curve."

    if intent == "duration_question":
        return (f"Your full path totals {path.total_duration_hours} hours across {len(path.steps)} steps. "
                f"At {profile.weekly_hours_available}h/week, that's roughly "
                f"{max(1, round(path.total_duration_hours / max(profile.weekly_hours_available,1)))} weeks "
                f"at a {profile.preferred_pace} pace.")

    if intent == "next_step":
        next_step = next((s for s in path.steps if s.status == "available"), None)
        if next_step:
            return f"Your next recommended step is '{next_step.course.title}' ({next_step.milestone} milestone, {next_step.course.duration_hours}h)."
        return "You've completed all currently available steps — great work! Check the dashboard for what unlocks next."

    if intent == "difficulty_help":
        return ("That's normal — many learners hit a wall around this stage. Try breaking the course into "
                "smaller daily sessions, revisit the prerequisite material if concepts feel shaky, and use "
                "the practice assessment steps in your path as checkpoints. I can also suggest an easier "
                "supplementary resource if you tell me which specific topic is tripping you up.")

    if intent == "too_easy":
        return ("Good to know — I can adapt your path to move faster. Mark the current course as completed "
                "and I'll re-rank your remaining recommendations toward more advanced material immediately.")

    return (f"I can help with questions about your path toward {path.goal_title}. "
            "Try asking things like 'why do I need SQL?', 'what's next?', or 'how long will this take?'")
