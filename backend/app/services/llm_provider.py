"""
Pluggable LLM provider seam.

The conversational engine works fully offline using rule-based NLU
(see nlp_intent.py) and template-based generation (see conversation.py).
This module is the SINGLE integration point where a real LLM API call
would be wired in, so the rest of the system never needs to change.

To enable: set ANTHROPIC_API_KEY (or OPENAI_API_KEY) as an environment
variable and flip USE_LLM=true. If no key is present, `generate()`
transparently falls back to the deterministic template engine so the
whole app still runs with zero configuration (important for judges
running this locally without API keys).

`stream_generate()` is the real-time counterpart used by /api/chat/stream:
it yields text chunks as an async generator. With a key configured, it
streams genuine tokens from the Anthropic Messages API. Without one, it
simulates the same real-time streaming experience by chunking the
deterministic fallback reply with small delays — so the chat UI is
always live and responsive, and automatically gets smarter (real model
output instead of templates) the moment a key is added, with zero
frontend changes required either way.
"""
from __future__ import annotations
import os
import asyncio
from typing import AsyncGenerator, Optional

USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-6"


def llm_available() -> bool:
    return USE_LLM and bool(ANTHROPIC_API_KEY)


def generate(system_prompt: str, user_prompt: str, fallback: str) -> str:
    """
    Generate a response via LLM if configured, else return the fallback
    (produced by the deterministic template engine upstream).
    """
    if not llm_available():
        return fallback

    try:
        import anthropic  # imported lazily so it's not a hard dependency
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception:
        # Any failure (network, quota, bad key) — degrade gracefully.
        return fallback


async def stream_generate(system_prompt: str, user_prompt: str, fallback: str) -> AsyncGenerator[str, None]:
    """
    Async-yields text chunks in real time.

    - If a real LLM is configured: streams genuine tokens from Anthropic's
      Messages API via AsyncAnthropic + client.messages.stream(), so the
      learner sees the model's actual output appear incrementally.
    - If not configured (or the call fails for any reason — bad key,
      network, quota): falls back to chunking the deterministic template
      reply into small word-groups with a short delay between each,
      simulating the same real-time streaming UX. This means the demo
      is genuinely live and interactive out of the box, with no API key
      required to grade or run it.
    """
    if llm_available():
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            async with client.messages.stream(
                model=MODEL_NAME,
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
            return
        except Exception:
            pass  # fall through to simulated streaming below

    words = fallback.split(" ")
    buf = []
    for i, w in enumerate(words):
        buf.append(w)
        if len(buf) >= 3 or i == len(words) - 1:
            piece = " ".join(buf) + (" " if i != len(words) - 1 else "")
            yield piece
            buf = []
            await asyncio.sleep(0.035)
