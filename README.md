# LearnPath AI — Personalized Learning Path Recommender

An AI-powered assistant that turns a learner's free-text goal ("I want to become a data scientist, I know some Python, 6 hours a week") into a personalized, prerequisite-ordered learning roadmap — with explainable recommendations, a Q&A assistant, and a live progress dashboard.

Built for the **AI-Powered Personalized Learning Path Recommender** hackathon track.

---

## What's included

| Requirement | Where it lives |
|---|---|
| Conversational interface | `frontend/src/components/ChatView.jsx` + `backend/app/services/conversation.py` — **streams live, token-by-token**, over Server-Sent Events (`/api/chat/stream`) |
| Learner profiling engine | `backend/app/services/profiling.py` |
| Recommendation engine | `backend/app/services/recommendation.py` |
| Personalized path generator (prerequisites + milestones) | `backend/app/services/path_generator.py` |
| Explainability + learner Q&A | `backend/app/services/explainability.py` |
| Progress dashboard | `frontend/src/components/DashboardView.jsx` |
| **Interactive skill-graph visualization** *(beyond the brief — added for depth)* | `frontend/src/components/SkillGraphView.jsx` + `backend/app/routers/graph.py` |

## Real-time chat & the skill graph

**Streaming chat.** `/api/chat/stream` runs the same NLU/profiling logic as the standard endpoint, then streams the reply over Server-Sent Events instead of returning it in one block. With `ANTHROPIC_API_KEY` + `USE_LLM=true` set, it streams genuine model tokens; without a key, it streams the deterministic fallback reply at a natural reading pace — so the UI is live and responsive either way, and upgrades automatically the moment a key is added, with zero frontend changes.

**Skill graph.** `/api/graph/{learner_id}` exposes the learner's roadmap as a directed graph (nodes + edges) instead of a flat list, derived from the exact same sequencing as `/api/path` — never a second source of truth. The frontend renders it as an interactive SVG: hovering a course highlights every dependency edge touching it, and clicking pulls a live explanation from the same explainability engine used in the Recommendations tab.

## Architecture

```
┌─────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│   React Frontend     │ ◄──────────────────────► │   FastAPI Backend         │
│   (Vite, port 5173)  │        /api/*             │   (port 8000)             │
│                       │                           │                            │
│  ChatView             │                           │  conversation.py          │
│  RecommendationsView  │                           │  nlp_intent.py            │
│  PathView             │                           │  profiling.py             │
│  DashboardView        │                           │  recommendation.py        │
└─────────────────────┘                           │  path_generator.py        │
                                                     │  explainability.py        │
                                                     └──────────────────────────┘
                                                                │
                                                     ┌──────────────────────────┐
                                                     │  courses.json (25 courses)│
                                                     │  goals.json (9 goal maps) │
                                                     │  profiles_store.json      │
                                                     │  (auto-generated)         │
                                                     └──────────────────────────┘
```

**How it works end to end:**
1. Learner describes their goal in the chat. The NLU layer (`nlp_intent.py`) extracts goal, known skills, experience level, weekly hours, and pace — with negation handling, so "I'm *new to* machine learning" is not mistaken for "I know machine learning."
2. The profiling engine merges these signals into a persistent `LearnerProfile`.
3. The recommendation engine scores every course in the catalog against the learner's skill gap, prerequisite readiness, level fit, and a popularity prior — and attaches human-readable reasons to every score.
4. The path generator runs a topological sort (Kahn's algorithm) over the prerequisite graph to sequence the relevant courses into a valid, dependency-respecting roadmap grouped into milestones (Foundations → Core Skills → Applied Practice → Mastery).
5. Marking a course "completed" (or flagging it "too hard"/"too easy") updates the profile and **regenerates the path live** — this is the adaptivity loop.
6. The dashboard aggregates all of this into completion %, skills acquired/remaining, and a milestone timeline chart.

## AI/ML techniques used

- **Rule-based + fuzzy-matching NLU** for intent/entity extraction from free text (goal matching, skill extraction, experience-level detection, negation handling) — see `nlp_intent.py`.
- **Hybrid content-based recommendation** combining four weighted signals (skill-gap coverage, prerequisite readiness, level fit, popularity prior) — see `recommendation.py`.
- **Graph algorithm (topological sort / Kahn's algorithm)** over a course-prerequisite DAG to guarantee valid learning sequences — see `path_generator.py`.
- **Explainable-by-construction design**: every recommendation score is decomposed into the same human-readable reasons shown to the learner, rather than a black-box score — see `explainability.py`.
- **Pluggable LLM hook** (`llm_provider.py`): the conversational layer works fully offline by default (no API key needed to run/grade this), but if `ANTHROPIC_API_KEY` is set and `USE_LLM=true`, chat replies are generated by a real LLM call instead of templates, with automatic fallback on any failure.

---

## Local setup & execution

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Interactive API docs (auto-generated): `http://localhost:8000/docs`.

### 2. Frontend

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies all `/api/*` calls to the backend automatically (see `frontend/vite.config.js`).

### 3. Use it

Open `http://localhost:5173` in your browser and start chatting, e.g.:

> "I want to become a data scientist, I know some Python but I'm new to machine learning, and I have about 6 hours a week."

Once the assistant confirms it has enough information, the **Recommendations**, **Learning Path**, and **Dashboard** tabs unlock in the sidebar.

### Optional: enable real LLM-generated chat replies

```bash
# in backend/.env or your shell
export ANTHROPIC_API_KEY=your_key_here
export USE_LLM=true
```

Without this, the app runs fully offline using the deterministic template engine — no API key required to grade or demo it.

---

## Project structure

```
learnpath/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + router registration
│   │   ├── models/schemas.py       # Pydantic request/response models
│   │   ├── routers/                # chat, profile, recommendations, path, dashboard, explain
│   │   └── services/
│   │       ├── nlp_intent.py       # goal/skill/experience extraction from free text
│   │       ├── llm_provider.py     # optional real-LLM hook with graceful fallback
│   │       ├── profiling.py        # learner profile store + merge logic
│   │       ├── recommendation.py   # hybrid scoring engine
│   │       ├── path_generator.py   # topological sort → ordered roadmap
│   │       ├── explainability.py   # why-recommended + free-form Q&A
│   │       └── conversation.py     # multi-turn dialogue orchestration
│   ├── data/
│   │   ├── courses.json            # 25-course knowledge graph
│   │   └── goals.json              # 9 career-goal → target-skills templates
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # view routing + shared learner_id
│   │   ├── api.js                  # typed fetch wrapper for all backend endpoints
│   │   └── components/
│   │       ├── ChatView.jsx
│   │       ├── RecommendationsView.jsx
│   │       ├── PathView.jsx
│   │       └── DashboardView.jsx
│   ├── vite.config.js              # dev proxy to backend
│   └── package.json
└── docs/
    └── solution_documentation.pdf  # architecture, approach, challenges
```

## Extending the course catalog

Courses and goals are plain JSON (`backend/data/courses.json`, `backend/data/goals.json`) — no code changes needed to add new courses, skills, or career-goal templates. Every course needs: `id`, `title`, `domain`, `level`, `skills_taught`, `prerequisites` (skill IDs, not course IDs — this is what drives the dependency graph), `duration_hours`, `type`, `description`, `resource_url`.

## Known limitations / honest scope notes

- The course catalog (25 courses, 9 goals) is a curated demo dataset, not a live scrape of a real learning platform — in production this would be backed by a real course database/API.
- Persistence is a local JSON file (`profiles_store.json`), sufficient for demo/grading; a production build would use a real database.
- The popularity-prior scores in `recommendation.py` are static placeholders standing in for a real collaborative-filtering signal (which would need real enrollment/completion/rating data).
- Chat NLU is rule-based by default (see the LLM hook above to upgrade it) — it handles the demo phrasing patterns robustly (including negation) but is not a full general-purpose NLU system.
