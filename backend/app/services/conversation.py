"""
Conversational Interface Engine.

Drives the multi-turn dialogue: extracts intent from each learner
message (nlp_intent.py), merges it into their profile (profiling.py),
and decides what to say next — either a clarifying question (if the
profile isn't yet complete enough to generate a good path) or a
transition into showing recommendations.

This is template-based generation by default (deterministic, free to
run, good for demos) with an optional real-LLM upgrade path via
llm_provider.py — see that module's docstring for how to enable it.
"""
from __future__ import annotations
from typing import List

from app.models.schemas import LearnerProfile, ChatResponse
from app.services import nlp_intent, profiling
from app.services.llm_provider import generate as llm_generate

GREETING_HINTS = ["hi", "hello", "hey", "start", "begin"]

CLARIFYING_QUESTIONS = {
    "goal": "What's your learning goal? For example: 'I want to become a data scientist' or 'I'd like to become a full-stack web developer'.",
    "experience": "How would you describe your current experience level — beginner, intermediate, or advanced?",
    "skills": "Do you already know any relevant skills or tools (e.g. Python, SQL, JavaScript)? List anything you're comfortable with, or say 'none yet'.",
    "hours": "Roughly how many hours per week can you dedicate to learning?",
}


SYSTEM_PROMPT = (
    "You are a friendly, concise AI learning-path advisor. Given extracted "
    "signals about a learner, respond warmly, confirm what you understood, "
    "and if information is missing, ask ONE clarifying question. Keep it under 60 words."
)


def _next_missing_field(profile: LearnerProfile) -> str | None:
    if not profile.matched_goal_id:
        return "goal"
    if profile.experience_level is None:
        return "experience"
    if not profile.known_skills and profile.experience_level != "beginner":
        return "skills"
    if not profile.weekly_hours_available:
        return "hours"
    return None


def _template_reply(profile: LearnerProfile, extracted: dict, missing: str | None) -> str:
    parts = []

    if extracted.get("matched_goal_title"):
        parts.append(
            f"Got it — you're aiming to become a {extracted['matched_goal_title']}. "
            f"{extracted.get('goal_description', '')}"
        )
    if extracted.get("known_skills"):
        skills_str = ", ".join(extracted["known_skills"]).replace("-", " ")
        parts.append(f"Noted that you already know: {skills_str}.")
    if extracted.get("experience_level"):
        parts.append(f"I'll treat your experience level as {extracted['experience_level']}.")
    if extracted.get("weekly_hours"):
        parts.append(f"Planning around {extracted['weekly_hours']}h/week of study time.")

    if missing:
        parts.append(CLARIFYING_QUESTIONS[missing])
    else:
        parts.append(
            "I have enough to build your personalized learning path now — "
            "check the Recommendations tab, or ask me anything about it here."
        )

    if not parts or (len(parts) == 1 and missing == "goal"):
        return CLARIFYING_QUESTIONS["goal"]

    return " ".join(parts)


def prepare_reply(learner_id: str, message: str):
    """
    Shared core used by BOTH the standard (/api/chat) and streaming
    (/api/chat/stream) endpoints: runs NLU extraction, merges signals
    into the profile, and produces the deterministic fallback reply +
    missing-field state. Kept as a single function so the two entry
    points can never silently drift out of sync with each other —
    streaming only changes how the reply text is *delivered*, never
    how the profile is built.

    Returns: (profile, extracted: dict, missing: str | None, fallback_reply: str)
    """
    profile = profiling.get_profile(learner_id)

    msg_lower = message.strip().lower()
    is_greeting_only = msg_lower in GREETING_HINTS or (
        len(msg_lower.split()) <= 2 and any(g in msg_lower for g in GREETING_HINTS)
    )

    if is_greeting_only and not profile.matched_goal_id:
        fallback_reply = (
            "Hi! I'm your AI learning path assistant. Tell me what you're hoping to achieve — "
            "for example, \"I want to become a data scientist, I know some Python but I'm new to ML, "
            "and I have about 6 hours a week.\""
        )
        return profile, {}, "goal", fallback_reply

    extracted = nlp_intent.extract_intent(message)
    profile = profiling.merge_extracted_signals(profile, extracted)
    profiling.save_profile(profile)

    missing = _next_missing_field(profile)
    fallback_reply = _template_reply(profile, extracted, missing)
    return profile, extracted, missing, fallback_reply


def handle_message(learner_id: str, message: str, history: List[dict]) -> ChatResponse:
    profile, extracted, missing, fallback_reply = prepare_reply(learner_id, message)

    user_prompt = f"Learner message: {message}\nExtracted signals: {extracted}\nMissing field: {missing}"
    reply = llm_generate(SYSTEM_PROMPT, user_prompt, fallback=fallback_reply)

    return ChatResponse(
        reply=reply,
        extracted={k: v for k, v in extracted.items() if v not in (None, [], "")},
        profile=profile,
        ready_for_path=missing is None,
        suggested_next_question=CLARIFYING_QUESTIONS.get(missing) if missing else None,
    )
