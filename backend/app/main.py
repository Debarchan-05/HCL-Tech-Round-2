"""
AI-Powered Personalized Learning Path Recommender — Backend API

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Interactive API docs (auto-generated): http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, profile, recommendations, path, dashboard, explain, graph

app = FastAPI(
    title="AI-Powered Personalized Learning Path Recommender",
    description=(
        "Backend API for a conversational, AI-driven learning path assistant. "
        "Provides a learner profiling engine, hybrid recommendation engine, "
        "prerequisite-aware path generator, explainability layer, and progress dashboard."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relaxed for local dev / demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(profile.router)
app.include_router(recommendations.router)
app.include_router(path.router)
app.include_router(dashboard.router)
app.include_router(explain.router)
app.include_router(graph.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "service": "learning-path-recommender-api",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "healthy"}
