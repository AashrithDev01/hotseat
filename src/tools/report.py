"""get_session_report tool.

Builds the end-of-session report: per-turn scores, strengths/gaps, tips,
plus the mode-specific artifact (thank-you email draft | BLUF exec summary).
"""

from __future__ import annotations

from ..llm.client import LLMClient
from ..models.session import Session, SessionMode
from .session import _SESSIONS

REPORT_SYSTEM = """\
You write the HotSeat session report. Given the brief and the full turn history
with scores, produce markdown with:
## Scores
Per-turn table (turn, persona, overall 1-5).
## Strengths
## Gaps
## Top 3 tips to improve
Then the artifact:
- interview mode: a concise post-interview thank-you email draft.
- stakeholder mode: a one-page BLUF executive summary of the proposal.
"""


async def get_session_report(llm: LLMClient, session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise KeyError(f"Unknown session: {session_id}")

    history = "\n".join(
        f"{t.speaker}: {t.text}"
        + (f" [score {t.score.overall}/5]" if t.score else "")
        for t in session.turns
    )
    report_md = await llm.complete(
        REPORT_SYSTEM,
        [
            {
                "role": "user",
                "content": (
                    f"Mode: {session.config.mode.value}\n"
                    f"Brief: {session.brief.summary}\nHistory:\n{history}"
                ),
            }
        ],
        max_tokens=1500,
        temperature=0.5,
    )
    if report_md.startswith("[MOCK]"):
        report_md = (
            f"# HotSeat report ({session.config.mode.value} mode)\n\n"
            f"Turns: {len(session.turns)}. "
            "Wire up BedrockLLMClient for the full scored report."
        )
    session.status = "completed"
    artifact = (
        "thank_you_email"
        if session.config.mode == SessionMode.INTERVIEW
        else "exec_summary"
    )
    return {"session_id": session_id, "artifact": artifact, "report_markdown": report_md}
