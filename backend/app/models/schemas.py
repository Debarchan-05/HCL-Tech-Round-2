"""
Pydantic schemas shared across the API.
These define the shape of every request/response so FastAPI can
validate input and auto-generate the OpenAPI docs.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field


# ---------- Learner Profile ----------

class LearnerProfile(BaseModel):
    learner_id: str
    name: Optional[str] = "Learner"
    goal_text: Optional[str] = None
    matched_goal_id: Optional[str] = None
    matched_goal_title: Optional[str] = None
    experience_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    known_skills: List[str] = Field(default_factory=list)
    completed_course_ids: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    weekly_hours_available: int = 5
    preferred_pace: Literal["relaxed", "steady", "intensive"] = "steady"


# ---------- Chat / Conversational Interface ----------

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    learner_id: str
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    extracted: Dict = Field(default_factory=dict)
    profile: LearnerProfile
    ready_for_path: bool = False
    suggested_next_question: Optional[str] = None


# ---------- Recommendations & Path ----------

class CourseOut(BaseModel):
    id: str
    title: str
    domain: str
    level: str
    type: str
    duration_hours: int
    description: str
    resource_url: str
    skills_taught: List[str]
    prerequisites: List[str]


class RecommendationItem(BaseModel):
    course: CourseOut
    score: float
    reasons: List[str]


class PathStep(BaseModel):
    order: int
    course: CourseOut
    milestone: str
    unlocked_by: List[str] = Field(default_factory=list)  # skills this step required
    status: Literal["locked", "available", "in_progress", "completed"] = "available"


class LearningPath(BaseModel):
    learner_id: str
    goal_title: str
    total_duration_hours: int
    steps: List[PathStep]
    skill_gap: List[str]
    already_known: List[str]
    explanation_summary: str


class ProgressUpdate(BaseModel):
    learner_id: str
    course_id: str
    status: Literal["in_progress", "completed"]
    feedback: Optional[Literal["too_easy", "too_hard", "just_right", "not_relevant"]] = None


class DashboardResponse(BaseModel):
    learner_id: str
    goal_title: Optional[str]
    total_courses: int
    completed_courses: int
    completion_pct: float
    skills_acquired: List[str]
    skills_remaining: List[str]
    hours_completed: int
    hours_remaining: int
    next_actions: List[CourseOut]
    milestone_timeline: List[Dict]


class GraphNode(BaseModel):
    id: str
    title: str
    milestone: str
    status: Literal["locked", "available", "in_progress", "completed"]
    level: str
    type: str
    duration_hours: int
    order: int


class GraphEdge(BaseModel):
    source: str  # course id
    target: str  # course id
    via_skill: str  # which skill this dependency is about


class SkillGraph(BaseModel):
    learner_id: str
    goal_title: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class WhyRequest(BaseModel):
    learner_id: str
    course_id: str


class WhyResponse(BaseModel):
    course_id: str
    course_title: str
    explanation: str
    contributing_factors: List[str]
