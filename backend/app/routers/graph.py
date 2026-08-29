from fastapi import APIRouter
from app.models.schemas import SkillGraph
from app.services import profiling, path_generator

router = APIRouter(prefix="/api/graph", tags=["Skill Graph Visualization"])


@router.get("/{learner_id}", response_model=SkillGraph)
def get_skill_graph(learner_id: str):
    """
    Returns the learner's roadmap as a directed graph (nodes + edges)
    instead of a flat list, for the interactive visualization. Derived
    from the exact same sequencing as /api/path — never a separate
    source of truth.
    """
    profile = profiling.get_profile(learner_id)
    return path_generator.build_skill_graph(profile)
