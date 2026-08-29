import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse
from app.services.conversation import handle_message, prepare_reply, SYSTEM_PROMPT, CLARIFYING_QUESTIONS
from app.services.llm_provider import stream_generate

router = APIRouter(prefix="/api/chat", tags=["Conversational Interface"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main conversational endpoint. Send a free-text learner message;
    receive an assistant reply plus the updated profile and a flag
    indicating whether enough info has been gathered to generate a path.
    """
    history_dicts = [h.model_dump() for h in req.history]
    return handle_message(req.learner_id, req.message, history_dicts)


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """
    Real-time streaming counterpart to POST /api/chat.

    NLU extraction and profile merging run synchronously first (fast,
    deterministic — the profile must never depend on streaming timing),
    then the conversational reply streams to the client token-by-token
    over Server-Sent Events. The stream ends with a `type: done` frame
    carrying the same structured payload the non-streaming endpoint
    returns (profile, ready_for_path, etc.), so the frontend can update
    state once the reply finishes.

    Streams real model output when ANTHROPIC_API_KEY + USE_LLM=true are
    configured; otherwise streams the deterministic fallback reply at a
    natural reading pace, so the UI is real-time either way.
    """
    profile, extracted, missing, fallback_reply = prepare_reply(req.learner_id, req.message)
    user_prompt = f"Learner message: {req.message}\nExtracted signals: {extracted}\nMissing field: {missing}"

    async def event_stream():
        full_text = ""
        async for chunk in stream_generate(SYSTEM_PROMPT, user_prompt, fallback=fallback_reply):
            full_text += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

        final_payload = {
            "type": "done",
            "reply": full_text,
            "extracted": {k: v for k, v in extracted.items() if v not in (None, [], "")},
            "profile": profile.model_dump(),
            "ready_for_path": missing is None,
            "suggested_next_question": CLARIFYING_QUESTIONS.get(missing) if missing else None,
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
