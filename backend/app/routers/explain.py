from fastapi import APIRouter
from pydantic import BaseModel
from app.models.schemas import WhyRequest, WhyResponse
from app.services import profiling, explainability

router = APIRouter(prefix="/api/explain", tags=["Explainability & Q&A"])


class AskRequest(BaseModel):
    learner_id: str
    question: str


class AskResponse(BaseModel):
    answer: str


@router.post("/why", response_model=WhyResponse)
def why_recommended(req: WhyRequest):
    """Explains why a specific course was recommended for this learner."""
    profile = profiling.get_profile(req.learner_id)
    return explainability.explain_recommendation(profile, req.course_id)


@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    """Free-form Q&A about the learner's current path."""
    profile = profiling.get_profile(req.learner_id)
    answer = explainability.answer_query(profile, req.question)
    return AskResponse(answer=answer)
