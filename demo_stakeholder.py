"""Live demo: the lean Stakeholder Room. Run: .venv/bin/python demo_stakeholder.py

Watch the Skeptic (CFO) kill hand-wavy numbers and the Time-Crunched Exec
demand the 30-second version. Same engine as interviews — different room,
different scorecard (BLUF, objection handling, evidence, presence).
"""

from __future__ import annotations

import asyncio
import json

from src.llm.client import LLMClient
from src.models.session import BriefType, SessionConfig, SessionMode
from src.tools import analyze_brief as ab
from src.tools import report as rp
from src.tools import session as se

SKEPTIC_LINES = [
    "The floor is yours. Make it worth my budget.",
    "Exciting doesn't pay bills. What's the ROI — give me a number.",
    "Feelings aren't a budget line. Cost per month, before and after. Now.",
]

EXEC_LINES = [
    "You've got 30 seconds. Why should I care?",
    "Land the plane. What's the ask?",
]

# Scripted pitches: fluffy, vague, then BLUF-with-numbers, then crisp.
PITCHES = [
    "So this is a really exciting transformation initiative that will unlock "
    "synergies across the organization and position us well for the future of AI.",
    "Well, it's hard to put an exact number on transformation, but the team "
    "feels strongly this is the right strategic direction for us.",
    "Bottom line: migrating to Bedrock cuts our inference cost by thirty-five "
    "percent, saving eighteen thousand dollars every month. Payback in three "
    "months. I'm asking for fifty thousand dollars, one time, approved today.",
    "We cut inference spend thirty-five percent starting next quarter with zero "
    "downtime during migration. The one-pager with the full cost breakdown is "
    "already in your inbox for review.",
]

FLUFFY = ("exciting", "synerg", "feel", "transformation")


class DemoLLM(LLMClient):
    async def complete(self, system, messages, max_tokens=1024, temperature=0.7) -> str:
        last = messages[-1]["content"]
        slow = system.lower()
        if not hasattr(self, "_qi"):
            self._qi = 0

        if "evaluator" in slow:  # stakeholder scorecard
            text = last.split("Transcript:")[-1]
            weak = len(text.split()) < 20 or any(f in text.lower() for f in FLUFFY)
            dims = ["bluf_discipline", "objection_handling", "evidence",
                    "executive_presence", "room_awareness"]
            return json.dumps({
                "dimension_scores": {d: (2 if weak else 4) for d in dims},
                "overall": 2 if weak else 4,
                "strengths": [] if weak else ["led with the bottom line", "cited numbers"],
                "gaps": ["open with the ask, not the adjectives"] if weak else [],
                "follow_up_needed": weak,
                "follow_up_hint": "Demand one sourced number." if weak else None,
            })

        if "structured facts" in slow:
            return json.dumps({
                "title": "Bedrock migration budget pitch",
                "summary": "Pitch to leadership: migrate the RAG pipeline to Bedrock; asking $50K one-time budget.",
                "seniority": None, "required_skills": [], "likely_topics": [],
                "audience": "CFO (Skeptic), busy exec (Time-Crunched)",
                "key_points": ["35% inference cost cut", "$18K/month savings", "3-month payback"],
                "likely_objections": ["prove the ROI", "migration risk", "why now"],
                "ask": "$50K one-time budget approval",
            })

        if "session report" in slow:
            return (
                "## Scores\n- Skeptic rounds: 2/5, 2/5 → then 4/5 after numbers landed\n"
                "- Exec rounds: 4/5\n"
                "## Strengths\n- Recovered fast once you led with BLUF and sourced numbers\n"
                "## Gaps\n- Opened with adjectives ('exciting', 'synergies') — the Skeptic smelled it instantly\n"
                "## Top 3 tips\n1. First sentence = the ask + the why. Always.\n"
                "2. Every number needs a source before the CFO asks.\n"
                "3. If they say '30 seconds', give them 25.\n"
                "## BLUF Executive Summary\n**Ask:** Approve $50K one-time for Bedrock migration. "
                "**Why:** $18K/month savings, 3-month payback, zero-downtime migration. "
                "**Risk of inaction:** inference spend grows ~10%/quarter on current stack.\n"
            )

        if "cfo" in slow:
            line = SKEPTIC_LINES[self._qi % len(SKEPTIC_LINES)]
            self._qi += 1
            return line
        if "busy executive" in slow:
            line = EXEC_LINES[self._qi % len(EXEC_LINES)]
            self._qi += 1
            return line
        return "Go on."


async def main() -> None:
    llm = DemoLLM()

    print("=" * 64)
    print("STEP 1: analyze_brief  ->  meeting brief becomes a brief card")
    print("=" * 64)
    card = await ab.analyze_brief(
        llm,
        "Pitch to leadership: migrate our RAG pipeline to Amazon Bedrock. "
        "Need $50K one-time budget approval. Audience: CFO and a busy exec.",
        BriefType.MEETING_BRIEF,
    )
    print(f"  Ask     : {card.ask}")
    print(f"  Audience: {card.audience}")
    print(f"  Objections they'll raise: {', '.join(card.likely_objections)}")

    print("\n" + "=" * 64)
    print("STEP 2: start_session  ->  the room assembles (skeptic + exec)")
    print("=" * 64)
    cfg = SessionConfig(
        mode=SessionMode.STAKEHOLDER,
        personas=["skeptic", "time_crunched_exec"],
        max_turns=6,
    )
    sess = await se.start_session(llm, card, cfg)
    print(f"  [{sess.turns[0].speaker}] {sess.turns[0].text}")

    for i, pitch in enumerate(PITCHES, 1):
        print(f"\n--- Pitch {i}: you speak ---")
        print(f"  [YOU] {pitch}")
        result = await se.submit_answer(llm, sess.session_id, pitch)
        score = result["score"]
        print(f"  [SCORE] {score.overall}/5  "
              f"(bluf={score.dimension_scores['bluf_discipline']}, "
              f"evidence={score.dimension_scores['evidence']})")
        tag = "OBJECTION (adaptive!)" if result["type"] == "follow_up" else "next stakeholder"
        print(f"  [{tag} | {result['persona']}] {result['text']}")

    print("\n" + "=" * 64)
    print("STEP 3: get_session_report  ->  scores + BLUF executive summary")
    print("=" * 64)
    rep = await rp.get_session_report(llm, sess.session_id)
    print(f"  artifact: {rep['artifact']}")
    print(rep["report_markdown"])
    print("Demo complete. Same engine, different room — the scorecard changed, not the code.")


if __name__ == "__main__":
    asyncio.run(main())
