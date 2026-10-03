"""Evaluator rubric for HotSeat.

The evaluator scores each spoken turn 1-5 on mode-specific dimensions.
If any dimension scores <= 2, the interviewer asks ONE targeted follow-up
on that dimension (max 2 follow-ups per question) before moving on.
"""

from __future__ import annotations

FOLLOW_UP_THRESHOLD = 2
MAX_FOLLOW_UPS_PER_QUESTION = 2

INTERVIEW_RUBRIC: dict[str, str] = {
    "star_structure": (
        "Situation, Task, Action, Result present and in order. "
        "5 = crisp STAR arc; 1 = no discernible structure."
    ),
    "specificity": (
        "Numbers, names, concrete outcomes vs. hand-waving. "
        "5 = quantified impact; 1 = pure adjectives."
    ),
    "relevance": (
        "Answers the question actually asked. "
        "5 = direct hit; 1 = dodged or misunderstood the question."
    ),
    "conciseness": (
        "No rambling; filler flagged. "
        "5 = tight, complete; 1 = circular or unfinished."
    ),
    "confidence": (
        "Hedging language detection ('kinda', 'I guess', 'maybe', excessive 'um'). "
        "5 = owned statements; 1 = constant hedging."
    ),
}

STAKEHOLDER_RUBRIC: dict[str, str] = {
    "bluf_discipline": (
        "Bottom line up front — point landed in the first 30 seconds. "
        "5 = opened with the ask and the why; 1 = buried the lede."
    ),
    "objection_handling": (
        "Acknowledge -> address -> bridge back. No defensiveness. "
        "5 = turned the objection into support; 1 = deflected or argued."
    ),
    "evidence": (
        "Data and specifics vs. adjectives. "
        "5 = cited numbers/sources; 1 = 'trust me' energy."
    ),
    "executive_presence": (
        "Hedging/filler detection, rambling flags. "
        "5 = calm, crisp; 1 = nervous filler throughout."
    ),
    "room_awareness": (
        "Adapting when the room signals impatience or confusion. "
        "5 = read the room and adjusted; 1 = plowed ahead regardless."
    ),
}

RUBRICS: dict[str, dict[str, str]] = {
    "interview": INTERVIEW_RUBRIC,
    "stakeholder": STAKEHOLDER_RUBRIC,
}


def rubric_for_mode(mode: str) -> dict[str, str]:
    return RUBRICS[mode]


EVALUATOR_SYSTEM_PROMPT = """\
You are the HotSeat evaluator. Score the speaker's turn 1-5 on each rubric
dimension provided. Return JSON with:
{
  "dimension_scores": {"<dimension>": <1-5>, ...},
  "overall": <1-5>,
  "strengths": ["..."],
  "gaps": ["..."],
  "follow_up_needed": <true|false>,
  "follow_up_hint": "<what the interviewer should probe, or null>"
}
Set follow_up_needed=true when any dimension scores <= 2, with a hint naming
the weakest dimension and what a good answer would include. Be honest and
specific — vague praise helps nobody. Base scores ONLY on the transcript given.
"""
