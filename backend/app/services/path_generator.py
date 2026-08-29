"""
Personalized Learning Path Generator.

Takes the recommendation engine's scored candidates and the skill-gap
analysis, then sequences them into a valid, prerequisite-respecting
roadmap using topological sort over the course dependency graph
(courses are nodes; a directed edge exists when course A's output skill
is a prerequisite for course B). This guarantees learners are never
shown a course before they're ready for it.

Milestones group the path into stages (Foundations / Core Skills /
Applied Practice / Mastery) based on course level + type, which the
dashboard visualizes as a timeline.
"""
from __future__ import annotations
from typing import Dict, List, Set, Optional
from collections import deque

from app.models.schemas import LearnerProfile, PathStep, LearningPath
from app.services.recommendation import (
    COURSES, COURSE_BY_ID, get_target_skills, get_known_skill_set,
    compute_skill_gap, score_course, _to_course_out,
)

MILESTONE_RULES = [
    ("Foundations", lambda c: c["level"] == "beginner"),
    ("Core Skills", lambda c: c["level"] == "intermediate" and c["type"] == "course"),
    ("Applied Practice", lambda c: c["type"] in ("project", "assessment")),
    ("Mastery", lambda c: c["level"] == "advanced"),
]


def _milestone_for(course: dict) -> str:
    for name, rule in MILESTONE_RULES:
        if rule(course):
            return name
    return "Core Skills"


def _skills_provided_by(course_id: str) -> Set[str]:
    c = COURSE_BY_ID.get(course_id)
    return set(c["skills_taught"]) if c else set()


def _dominant_domain(profile: LearnerProfile) -> Optional[str]:
    """
    Determine the goal's primary domain by counting which domain teaches
    the most of the goal's target_skills. Used to disambiguate when
    multiple courses across different domains teach the same (often
    generic) skill tag — e.g. both "ML Capstone Project" (Data Science)
    and "Full-Stack Capstone" (Web Development) teach "project-experience".
    Without this, seed-course selection is domain-blind and can pull in
    an entire unrelated course chain (and its prerequisites) just because
    one course happened to appear earlier in the catalog file.
    """
    target = get_target_skills(profile)
    if not target:
        return None
    counts: Dict[str, int] = {}
    for skill in target:
        for c in COURSES:
            if skill in c["skills_taught"]:
                counts[c["domain"]] = counts.get(c["domain"], 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _build_relevant_course_set(profile: LearnerProfile, gap: Set[str]) -> List[dict]:
    """
    Select the minimal set of courses needed to close the skill gap,
    PLUS any transitive prerequisite courses not yet known, so the
    topological sort has everything it needs to build a complete chain.

    Domain-aware seeding: when several courses teach the same gap skill
    (common for generic tags like "project-experience"), only the
    course(s) matching the goal's dominant domain are seeded — see
    _dominant_domain. This prevents an out-of-domain course (and its
    entire prerequisite chain) from leaking into an otherwise
    correctly-scoped roadmap.
    """
    known = get_known_skill_set(profile)
    completed = set(profile.completed_course_ids)
    primary_domain = _dominant_domain(profile)

    # Seed: courses that directly teach a gap skill
    selected: Dict[str, dict] = {}
    queue = deque()
    for c in COURSES:
        if c["id"] in completed:
            continue
        matched_skills = set(c["skills_taught"]) & gap
        if not matched_skills:
            continue
        if primary_domain and c["domain"] != primary_domain:
            # Only admit an out-of-domain course if NO in-domain course
            # covers this same skill — otherwise it's pure noise pulled
            # in by a coincidentally-shared generic skill tag.
            in_domain_alternative_exists = any(
                primary_domain == other["domain"] and matched_skills & set(other["skills_taught"])
                for other in COURSES
                if other["id"] != c["id"]
            )
            if in_domain_alternative_exists:
                continue
        selected[c["id"]] = c
        queue.append(c)

    # Expand: pull in prerequisite-providing courses transitively
    while queue:
        current = queue.popleft()
        for prereq_skill in current["prerequisites"]:
            if prereq_skill in known:
                continue
            # find a course that teaches this missing prerequisite skill
            providers = [c for c in COURSES
                         if prereq_skill in c["skills_taught"] and c["id"] not in completed]
            if not providers:
                continue
            # pick the most foundational (lowest level) provider
            providers.sort(key=lambda c: {"beginner": 0, "intermediate": 1, "advanced": 2}[c["level"]])
            provider = providers[0]
            if provider["id"] not in selected:
                selected[provider["id"]] = provider
                queue.append(provider)

    return list(selected.values())


def _topological_order(course_list: List[dict], known: Set[str]) -> List[dict]:
    """
    Kahn's algorithm over the prerequisite DAG. A course's in-degree is
    the count of its prerequisite skills not already known AND not yet
    covered by an already-scheduled course in this batch.
    """
    remaining = {c["id"]: c for c in course_list}
    scheduled_skills: Set[str] = set(known)
    ordered: List[dict] = []

    def ready(course: dict) -> bool:
        return set(course["prerequisites"]).issubset(scheduled_skills)

    # Stable ordering: iterate deterministically (by id) each pass so ties
    # break consistently rather than depending on dict/set iteration order.
    guard = 0
    while remaining and guard < 200:
        guard += 1
        batch = [c for c in sorted(remaining.values(), key=lambda c: c["id"]) if ready(c)]
        if not batch:
            # Circular or unresolvable dependency (shouldn't happen with this
            # dataset, but fail safe): dump remaining in id order rather than
            # looping forever, so the API never hangs.
            ordered.extend(sorted(remaining.values(), key=lambda c: c["id"]))
            break
        # Within a ready batch, prefer lower level first (natural difficulty ramp)
        batch.sort(key=lambda c: ({"beginner": 0, "intermediate": 1, "advanced": 2}[c["level"]], c["id"]))
        for c in batch:
            ordered.append(c)
            scheduled_skills |= set(c["skills_taught"])
            del remaining[c["id"]]

    return ordered


def generate_path(profile: LearnerProfile, max_steps: int = 12) -> LearningPath:
    gap_list = compute_skill_gap(profile)
    gap = set(gap_list)
    known = get_known_skill_set(profile)

    relevant = _build_relevant_course_set(profile, gap)
    ordered = _topological_order(relevant, known)[:max_steps]

    steps: List[PathStep] = []
    unlocked_skills = set(known)
    for i, course in enumerate(ordered, start=1):
        unmet = set(course["prerequisites"]) - unlocked_skills
        status = "available" if not unmet else "locked"
        steps.append(PathStep(
            order=i,
            course=_to_course_out(course),
            milestone=_milestone_for(course),
            unlocked_by=sorted(set(course["prerequisites"]) & unlocked_skills),
            status=status,
        ))
        unlocked_skills |= set(course["skills_taught"])

    # First step is always immediately available (nothing blocks it if the
    # topological sort worked correctly) — guard in case gap is empty.
    if steps:
        steps[0].status = "available"

    total_hours = sum(s.course.duration_hours for s in steps)
    goal_title = profile.matched_goal_title or "General Skill Development"

    if not gap_list:
        summary = (
            f"You already know all the target skills for '{goal_title}'. "
            "Consider a capstone project or an adjacent goal to deepen expertise."
        )
    else:
        summary = (
            f"Based on your goal to become a {goal_title}, we identified "
            f"{len(gap_list)} skill(s) to develop: {', '.join(gap_list).replace('-', ' ')}. "
            f"This {len(steps)}-step path ({total_hours}h total) sequences courses so every "
            f"prerequisite is met before it's needed, ending with applied projects."
        )

    return LearningPath(
        learner_id=profile.learner_id,
        goal_title=goal_title,
        total_duration_hours=total_hours,
        steps=steps,
        skill_gap=gap_list,
        already_known=sorted(known),
        explanation_summary=summary,
    )


def build_skill_graph(profile: LearnerProfile):
    """
    Derives a visualizable graph (nodes + directed edges) from the SAME
    sequenced path returned by generate_path() — never recomputed
    independently, so the graph can never show a different order or
    status than the linear roadmap view. An edge A -> B means "course A
    must be taken before course B", labeled with the specific skill that
    creates the dependency, so the visualization can explain each
    connection on hover, not just draw an arrow.
    """
    from app.models.schemas import GraphNode, GraphEdge, SkillGraph  # local import avoids a circular import at module load time

    path = generate_path(profile)
    nodes = [
        GraphNode(
            id=s.course.id, title=s.course.title, milestone=s.milestone,
            status=s.status, level=s.course.level, type=s.course.type,
            duration_hours=s.course.duration_hours, order=s.order,
        )
        for s in path.steps
    ]

    # For each step, find which EARLIER step(s) in this same path provide
    # the prerequisite skill(s) it needs, and draw an edge from provider -> course.
    edges: List[GraphEdge] = []
    skill_provided_by: Dict[str, str] = {}  # skill -> course_id of the step that first teaches it
    for s in path.steps:
        for prereq_skill in s.course.prerequisites:
            provider_id = skill_provided_by.get(prereq_skill)
            if provider_id:
                edges.append(GraphEdge(source=provider_id, target=s.course.id, via_skill=prereq_skill))
        for taught_skill in s.course.skills_taught:
            skill_provided_by.setdefault(taught_skill, s.course.id)

    return SkillGraph(
        learner_id=profile.learner_id,
        goal_title=path.goal_title,
        nodes=nodes,
        edges=edges,
    )
