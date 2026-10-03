"""Session state models for HotSeat.

Both modes (interview + stakeholder) run on the same session engine;
`mode` and the persona/rubric configuration are what differ.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionMode(str, Enum):
    INTERVIEW = "interview"
    STAKEHOLDER = "stakeholder"


class BriefType(str, Enum):
    JOB_POSTING = "job_posting"
    MEETING_BRIEF = "meeting_brief"


class BriefCard(BaseModel):
    """Structured output of analyze_brief."""

    brief_type: BriefType
    title: str = Field(description="Role title or meeting objective")
    summary: str
    # interview-specific
    seniority: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    likely_topics: list[str] = Field(default_factory=list)
    # stakeholder-specific
    audience: str | None = None
    key_points: list[str] = Field(default_factory=list)
    likely_objections: list[str] = Field(default_factory=list)
    ask: str | None = Field(default=None, description="What the presenter needs from the room")


class TurnScore(BaseModel):
    """Evaluator output for a single spoken turn."""

    dimension_scores: dict[str, int] = Field(description="Rubric dimension -> 1-5")
    overall: int = Field(ge=1, le=5)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_hint: str | None = None


class SessionTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    speaker: str = Field(description="Persona name or 'user'")
    text: str
    score: TurnScore | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionConfig(BaseModel):
    mode: SessionMode
    personas: list[str] = Field(description="Persona keys, e.g. ['staff_engineer', 'hiring_manager']")
    difficulty: str = Field(default="standard", description="warm_up | standard | hard")
    max_turns: int = 12


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid4().hex)
    config: SessionConfig
    brief: BriefCard
    turns: list[SessionTurn] = Field(default_factory=list)
    follow_ups_used: dict[str, int] = Field(default_factory=dict)
    status: str = Field(default="active", description="active | completed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
