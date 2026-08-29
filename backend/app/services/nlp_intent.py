"""
Lightweight NLP intent-extraction engine for the conversational interface.

Design note:
This uses rule-based + keyword/fuzzy matching (no external LLM API key
required), which keeps the whole solution self-contained, free to run,
and deterministic for demo purposes. The architecture is provider-agnostic:
`extract_intent()` is the single seam you'd swap to call an LLM API
(OpenAI/Anthropic/local model) for production-grade NLU without touching
any other layer (see `services/llm_provider.py` for the pluggable hook).
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

with open(DATA_DIR / "goals.json") as f:
    GOALS = json.load(f)

with open(DATA_DIR / "courses.json") as f:
    COURSES = json.load(f)

ALL_SKILLS = sorted({s for c in COURSES for s in c["skills_taught"]})

EXPERIENCE_PATTERNS = {
    "beginner": [
        r"\bbeginner\b", r"\bnew to\b", r"\bnever coded\b", r"\bfrom scratch\b",
        r"\bno experience\b", r"\bjust starting\b", r"\bcomplete novice\b",
        r"\bnever (used|written|programmed)\b", r"\bstarting fresh\b"
    ],
    "intermediate": [
        r"\bintermediate\b", r"\bsome experience\b", r"\bfamiliar with\b",
        r"\bknow (the )?basics\b", r"\bworked with\b", r"\b\d+ (months?|years?) of experience\b",
        r"\bself[- ]taught\b"
    ],
    "advanced": [
        r"\badvanced\b", r"\bexperienced\b", r"\bexpert\b", r"\bproficient\b",
        r"\bprofessional(ly)?\b", r"\b\d+\+? years\b", r"\bsenior\b"
    ],
}

HOURS_PATTERN = re.compile(r"(\d{1,2})\s*(?:hrs?|hours?)\s*(?:a|per)?\s*week", re.I)

PACE_PATTERNS = {
    "relaxed": [r"\brelaxed\b", r"\bslow\b", r"\bpart[- ]time\b", r"\bno rush\b"],
    "intensive": [r"\bintensive\b", r"\bfast\b", r"\basap\b", r"\bcrash course\b", r"\bfull[- ]time\b", r"\bquickly\b"],
}


def _fuzzy_contains(text: str, phrase: str, threshold: float = 0.82) -> bool:
    """Fuzzy substring check so minor typos in goal phrasing still match."""
    text = text.lower()
    phrase = phrase.lower()
    if phrase in text:
        return True
    words = text.split()
    phrase_len = len(phrase.split())
    for i in range(max(1, len(words) - phrase_len + 1)):
        window = " ".join(words[i:i + phrase_len])
        if SequenceMatcher(None, window, phrase).ratio() >= threshold:
            return True
    return False


def match_goal(text: str) -> Optional[Dict]:
    """Match free text against known career-goal templates by keyword/fuzzy score."""
    text_l = text.lower()
    best, best_score = None, 0.0
    for goal in GOALS:
        for kw in goal["keywords"]:
            if kw in text_l:
                return goal  # exact keyword hit — high confidence, return immediately
            score = SequenceMatcher(None, kw, text_l).ratio()
            if _fuzzy_contains(text_l, kw) and score > best_score:
                best, best_score = goal, score
    return best


# Phrases that negate an otherwise-positive skill mention when they appear
# shortly before it — e.g. "new to machine learning" must NOT be extracted
# as a known skill even though "machine learning" matches ALL_SKILLS.
NEGATION_LEAD_INS = [
    r"new to", r"no experience (with|in)", r"never (used|tried|learned|studied)",
    r"not familiar with", r"unfamiliar with", r"beginner (with|in|at)",
    r"don'?t know", r"haven'?t (used|learned|tried|touched)", r"want(ing)? to learn",
    r"looking to learn", r"hoping to learn", r"need to learn", r"trying to learn",
    r"weak (in|at)", r"struggle with", r"struggling with",
    r"\bno\b(?!\s+(problem|issue|trouble)\b)",  # bare "no X" e.g. "no JavaScript frameworks yet" —
                                                  # excludes "no problem/issue/trouble with X" (double
                                                  # negative = DOES know it), which is the one common
                                                  # case where a bare "no" precedes a skill they DO know.
]
# How many characters back from the skill mention we scan for a negation cue.
# Short window keeps it from misfiring on unrelated earlier clauses.
NEGATION_LOOKBACK_CHARS = 40


def _mask_goal_span(text_l: str, goal: Optional[Dict]) -> str:
    """
    Blank out the substring of the text that matched the goal keyword so
    role phrasing (e.g. "devops engineer", "react developer", "NLP engineer")
    isn't re-scanned as a skill claim. Several catalog skill names — devops,
    react, nlp, mlops, machine-learning — are substrings of how their
    corresponding goal is phrased, so without this a learner saying "I want
    to become a DevOps engineer" would be wrongly recorded as already
    knowing devops. Masking (not deleting) preserves character offsets so
    NEGATION_LOOKBACK_CHARS windows elsewhere in the string stay correct.
    """
    if not goal:
        return text_l
    for kw in sorted(goal["keywords"] + [goal["title"].lower()], key=len, reverse=True):
        idx = text_l.find(kw)
        if idx != -1:
            return text_l[:idx] + (" " * len(kw)) + text_l[idx + len(kw):]
    return text_l


def extract_known_skills(text: str, goal: Optional[Dict] = None) -> List[str]:
    """
    Detect skill mentions like 'I know Python and SQL' or 'used React before'.
    Explicitly excludes:
      1. Skills mentioned in a negated/aspirational context, e.g. 'I'm new
         to machine learning' or 'want to learn React' — these describe a
         learning GOAL, not existing proficiency.
      2. Skill-name substrings that are actually part of how the learner
         phrased their ROLE goal, e.g. the "devops" in "devops engineer" or
         the "react" in "react developer" (see _mask_goal_span).
    Both would otherwise corrupt the skill-gap calculation and cause the
    recommender to skip courses the learner actually needs.
    """
    text_l = _mask_goal_span(text.lower(), goal)
    found = []
    for skill in ALL_SKILLS:
        skill_phrase = skill.replace("-", " ")
        pattern = r"\b" + re.escape(skill_phrase) + r"\b"
        for m in re.finditer(pattern, text_l):
            window_start = max(0, m.start() - NEGATION_LOOKBACK_CHARS)
            window = text_l[window_start:m.start()]
            negated = any(re.search(neg, window) for neg in NEGATION_LEAD_INS)
            if not negated:
                found.append(skill)
                break  # one confirmed positive mention is enough for this skill
    return found


def extract_experience_level(text: str) -> Optional[str]:
    text_l = text.lower()
    for level, patterns in EXPERIENCE_PATTERNS.items():
        for p in patterns:
            if re.search(p, text_l):
                return level
    return None


def extract_weekly_hours(text: str) -> Optional[int]:
    m = HOURS_PATTERN.search(text)
    if m:
        return int(m.group(1))
    return None


def extract_pace(text: str) -> Optional[str]:
    text_l = text.lower()
    for pace, patterns in PACE_PATTERNS.items():
        for p in patterns:
            if re.search(p, text_l):
                return pace
    return None


def extract_interests(text: str) -> List[str]:
    """Detect broad domain interests mentioned in free text."""
    domains = {
        "data science": ["data science", "data analysis", "analytics", "machine learning", "ai"],
        "web development": ["web dev", "website", "web app", "frontend", "backend", "full stack"],
        "cloud & devops": ["cloud", "devops", "kubernetes", "infrastructure"],
        "product design": ["design", "ux", "ui", "product design"],
    }
    text_l = text.lower()
    found = []
    for domain, kws in domains.items():
        if any(kw in text_l for kw in kws):
            found.append(domain)
    return found


def extract_intent(text: str) -> Dict:
    """
    Main entry point: parse a single user utterance into structured signals.
    Returns a dict the profiling engine merges into the LearnerProfile.
    """
    goal = match_goal(text)
    return {
        "matched_goal_id": goal["id"] if goal else None,
        "matched_goal_title": goal["title"] if goal else None,
        "goal_description": goal["description"] if goal else None,
        "known_skills": extract_known_skills(text, goal=goal),
        "experience_level": extract_experience_level(text),
        "weekly_hours": extract_weekly_hours(text),
        "pace": extract_pace(text),
        "interests": extract_interests(text),
        "raw_text": text,
    }
