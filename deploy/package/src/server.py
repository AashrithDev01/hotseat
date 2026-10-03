"""HotSeat MCP server — MCPServer (SDK 2.x) + Streamable HTTP.

Exposes the four HotSeat tools over Streamable HTTP, satisfying the Alexa+
track requirement (MCP spec 2025-11-25+, Streamable HTTP transport).

Run: uvicorn src.server:app --host 0.0.0.0 --port 8000
MCP endpoint: http://localhost:8000/mcp
"""

from __future__ import annotations

import json
import os

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .agents.personas import PERSONAS
from .llm.client import make_client
from .models.session import BriefCard, BriefType, SessionConfig, SessionMode
from .tools import analyze_brief as analyze_brief_fn
from .tools import report as report_fn
from .tools import session as session_fn

# Bedrock when AWS credentials are present, mock otherwise.
_llm = make_client()

mcp = MCPServer(
    "hotseat",
    version="0.1.0",
    instructions=(
        "HotSeat: rehearse high-stakes conversations out loud. "
        "analyze_brief turns a JD or meeting brief into a brief card; "
        "start_session opens an interview or stakeholder session; "
        "submit_answer scores a spoken answer and returns a follow-up or next question; "
        "get_session_report produces the final report."
    ),
)


@mcp.tool()
async def analyze_brief(brief_text: str, brief_type: str) -> str:
    """Turn a job description or meeting brief into a structured brief card.

    brief_type: 'job_posting' or 'meeting_brief'.
    """
    card = await analyze_brief_fn.analyze_brief(
        _llm, brief_text, BriefType(brief_type)
    )
    return card.model_dump_json(indent=2)


@mcp.tool()
async def start_session(
    brief: dict,
    mode: str,
    personas: list[str],
    difficulty: str = "standard",
    max_turns: int = 12,
) -> str:
    """Start an interview or stakeholder session.

    brief: BriefCard JSON from analyze_brief. mode: 'interview' or 'stakeholder'.
    personas: e.g. ['staff_engineer', 'hiring_manager'] or ['skeptic', 'time_crunched_exec'].
    """
    brief_card = BriefCard.model_validate(brief)
    config = SessionConfig(
        mode=SessionMode(mode),
        personas=personas,
        difficulty=difficulty,
        max_turns=max_turns,
    )
    session = await session_fn.start_session(_llm, brief_card, config)
    opener = session.turns[0]
    return json.dumps(
        {
            "session_id": session.session_id,
            "persona": opener.speaker,
            "persona_style": PERSONAS[opener.speaker].style,
            "text": opener.text,
        },
        indent=2,
    )


@mcp.tool()
async def submit_answer(session_id: str, answer_text: str) -> str:
    """Submit a spoken answer; returns a score plus follow-up or next question."""
    result = await session_fn.submit_answer(_llm, session_id, answer_text)
    score = result.pop("score")
    result["score"] = json.loads(score.model_dump_json())
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_session_report(session_id: str) -> str:
    """Final report: scores, strengths, gaps, tips, plus email draft or exec summary."""
    result = await report_fn.get_session_report(_llm, session_id)
    return json.dumps(result, indent=2)


def _transport_security() -> TransportSecuritySettings | None:
    """Host allow-list for the MCP endpoint.

    Local dev: leave MCP_ALLOWED_HOSTS unset -> SDK defaults to localhost-only.
    Lambda: set MCP_ALLOWED_HOSTS to the Function URL host (no scheme, no port),
    e.g. "abc123.lambda-url.us-east-2.on.aws". The SDK also accepts "host:*"
    patterns; we add ":*" so any port matches.
    """
    raw = os.environ.get("MCP_ALLOWED_HOSTS", "").strip()
    if not raw:
        return None  # SDK default: localhost-only protection
    bare = [h.strip() for h in raw.split(",") if h.strip()]
    # Bare host (Lambda sends no port) AND host:* (SDK wildcard needs a port).
    hosts = bare + [f"{h}:*" for h in bare]
    origins = [f"https://{h}" for h in bare]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def create_app():
    """Build a fresh MCP app. Called once for uvicorn; per-invocation on Lambda
    (the SDK's session manager runs its lifespan exactly once per instance,
    and Mangum re-runs lifespan every invocation — so Lambda needs a new app
    each time)."""
    return mcp.streamable_http_app(
        transport_security=_transport_security(),
        # Lambda: stateless (each invocation independent). Local: stateful.
        stateless_http=os.environ.get("MCP_STATELESS", "").lower() in ("1", "true", "yes"),
    )


# The long-lived app for `uvicorn src.server:app`.
app = create_app()
