"""start_session + submit_answer tools.

The shared session engine for both modes. In-memory store for local dev;
DynamoDB-backed in production (week 2).
"""

from __future__ import annotations

from ..agents.evaluator import (
    FOLLOW_UP_THRESHOLD,
    MAX_FOLLOW_UPS_PER_QUESTION,
    rubric_for_mode,
)
from ..agents.personas import PERSONAS
from ..llm.client import LLMClient
from ..llm.json_utils import extract_json
from ..models.session import (
    BriefCard,
    Session,
    SessionConfig,
    SessionMode,
    SessionTurn,
    TurnScore,
)

# In-memory session store (local dev). TODO (week 2): DynamoDB.
_SESSIONS: dict[str, Session] = {}


async def start_session(
    llm: LLMClient, brief: BriefCard, config: SessionConfig
) -> Session:
    for key in config.personas:
        persona = PERSONAS.get(key)
        if persona is None or persona.mode != config.mode.value:
            raise ValueError(f"Unknown persona for mode {config.mode}: {key}")

    session = Session(config=config, brief=brief)
    opener = await _persona_utterance(llm, session, config.personas[0], opening=True)
    session.turns.append(SessionTurn(speaker=config.personas[0], text=opener))
    _SESSIONS[session.session_id] = session
    return session


async def submit_answer(
    llm: LLMClient, session_id: str, answer_text: str
) -> dict:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise KeyError(f"Unknown session: {session_id}")
    if session.status != "active":
        raise ValueError("Session already completed")

    session.turns.append(SessionTurn(speaker="user", text=answer_text))

    score = await _evaluate(llm, session, answer_text)
    session.turns[-1].score = score

    # Adaptive follow-up: weak dimension -> same persona probes once more.
    last_persona = session.turns[-2].speaker  # persona turn before user's answer
    used = session.follow_ups_used.get(last_persona, 0)
    if score.follow_up_needed and used < MAX_FOLLOW_UPS_PER_QUESTION:
        session.follow_ups_used[last_persona] = used + 1
        follow_up = await _persona_utterance(
            llm, session, last_persona, follow_up_hint=score.follow_up_hint
        )
        session.turns.append(SessionTurn(speaker=last_persona, text=follow_up))
        return {"type": "follow_up", "persona": last_persona, "text": follow_up, "score": score}

    # Otherwise advance: rotate to the next persona in the panel.
    next_persona = _next_persona(session)
    question = await _persona_utterance(llm, session, next_persona)
    session.turns.append(SessionTurn(speaker=next_persona, text=question))
    if len([t for t in session.turns if t.speaker == "user"]) >= session.config.max_turns:
        session.status = "completed"
    return {"type": "next_question", "persona": next_persona, "text": question, "score": score}


def _next_persona(session: Session) -> str:
    speakers = [t.speaker for t in session.turns if t.speaker != "user"]
    idx = session.config.personas.index(speakers[-1])
    return session.config.personas[(idx + 1) % len(session.config.personas)]


async def _persona_utterance(
    llm: LLMClient,
    session: Session,
    persona_key: str,
    opening: bool = False,
    follow_up_hint: str | None = None,
) -> str:
    persona = PERSONAS[persona_key]
    history = "\n".join(f"{t.speaker}: {t.text}" for t in session.turns[-6:])
    if opening:
        task = (
            "Open the session: interview mode -> ask your first question. "
            "Stakeholder mode -> invite them to pitch ('The floor is yours.')."
        )
    elif follow_up_hint:
        task = f"Ask ONE targeted follow-up based on this hint: {follow_up_hint}"
    else:
        task = "Ask your next question or raise your next objection."
    return await llm.complete(
        persona.system_prompt,
        [
            {"role": "user", "content": f"Brief: {session.brief.summary}\nHistory:\n{history}\nTask: {task}"},
        ],
        max_tokens=200,
        temperature=0.8,
    )


async def _evaluate(llm: LLMClient, session: Session, answer_text: str) -> TurnScore:
    from ..agents.evaluator import EVALUATOR_SYSTEM_PROMPT
    from ..llm.client import StrandsLLMClient

    # Agent path: typed TurnScore straight from the evaluator agent. No JSON parsing.
    if isinstance(llm, StrandsLLMClient):
        return await llm.backend.evaluate(
            session.config.mode.value, answer_text
        )

    rubric = rubric_for_mode(session.config.mode.value)
    rubric_text = "\n".join(f"- {k}: {v}" for k, v in rubric.items())
    probe = await llm.complete(
        EVALUATOR_SYSTEM_PROMPT + "\nRubric:\n" + rubric_text,
        [{"role": "user", "content": f"Transcript:\n{answer_text}"}],
        max_tokens=600,
        temperature=0.2,
    )
    if probe.startswith("[MOCK]"):
        # Deterministic mock score so the engine loop is testable locally.
        weak = len(answer_text.split()) < 20
        return TurnScore(
            dimension_scores={k: (2 if weak else 4) for k in rubric},
            overall=2 if weak else 4,
            strengths=["answered the prompt"] if not weak else [],
            gaps=["add specifics and structure"] if weak else [],
            follow_up_needed=weak,
            follow_up_hint="Ask for a concrete example with numbers." if weak else None,
        )
    data = extract_json(probe)
    return TurnScore.model_validate(data)
