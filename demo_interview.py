"""Live demo: watch a mock interview happen in your terminal.

Run:  .venv/bin/python demo_interview.py

Plays a scripted interview against the real HotSeat engine with a demo LLM
that asks realistic questions. Watch for the adaptive follow-up on the weak
answer — that's the heart of HotSeat.
"""

from __future__ import annotations

import asyncio
import json

from src.llm.client import LLMClient
from src.models.session import BriefType, SessionConfig, SessionMode
from src.tools import analyze_brief as ab
from src.tools import report as rp
from src.tools import session as se

QUESTIONS = {
    "staff engineer": [
        "Walk me through how you'd design a RAG pipeline that stays under 500ms p99 latency.",
        "How do you handle Bedrock model version upgrades without downtime?",
    ],
    "hiring manager": [
        "Tell me about a time you disagreed with your manager on a technical decision.",
        "Describe a project you led that failed. What did you learn?",
    ],
}

# Scripted candidate answers: strong, weak, strong-again.
ANSWERS = [
    "I designed a RAG pipeline on Bedrock with semantic caching and async fan-out. "
    "P99 went from 900ms to 380ms and inference cost dropped 35 percent.",
    "um, kinda, I guess it was fine",
    "I pushed back on my manager's plan to rewrite the service. I built a prototype "
    "proving the incremental path was 3x faster, and we shipped in 6 weeks with zero downtime.",
]


class DemoLLM(LLMClient):
    """Realistic demo brain: proper questions, JSON scores, no AWS needed."""

    def __init__(self) -> None:
        self.qi = 0

    async def complete(self, system, messages, max_tokens=1024, temperature=0.7) -> str:
        last = messages[-1]["content"]
        slow = system.lower()

        if "evaluator" in slow:  # scoring call -> JSON
            text = last.split("Transcript:")[-1]
            weak = len(text.split()) < 20
            return json.dumps({
                "dimension_scores": {
                    "star_structure": 2 if weak else 4,
                    "specificity": 2 if weak else 4,
                    "relevance": 3 if weak else 4,
                    "conciseness": 2 if weak else 4,
                    "confidence": 2 if weak else 4,
                },
                "overall": 2 if weak else 4,
                "strengths": [] if weak else ["concrete numbers", "clear structure"],
                "gaps": ["add a specific example with numbers"] if weak else [],
                "follow_up_needed": weak,
                "follow_up_hint": "Ask for a concrete example with numbers." if weak else None,
            })

        if "structured facts" in slow:  # brief analysis -> JSON
            return json.dumps({
                "title": "Senior AI Engineer",
                "summary": "Senior AI Engineer: Python, AWS, LangChain, Bedrock, RAG pipelines.",
                "seniority": "senior",
                "required_skills": ["Python", "AWS", "LangChain", "Bedrock"],
                "likely_topics": ["RAG design", "system design", "behavioral"],
                "audience": None, "key_points": [], "likely_objections": [], "ask": None,
            })

        if "session report" in slow:  # final report -> markdown
            return (
                "## Scores\n- Turn 1 (staff engineer): 4/5\n"
                "- Turn 2 (hiring manager): 2/5 -> follow-up answered: 4/5\n"
                "## Strengths\n- Strong technical storytelling with numbers\n"
                "## Gaps\n- Hedging language under pressure ('um, kinda')\n"
                "## Top 3 tips\n1. Open with the outcome, then the how.\n"
                "2. Replace 'I guess' with owned statements.\n"
                "3. Keep a 2-minute version of every story ready.\n"
            )

        for persona, qs in QUESTIONS.items():  # persona speaking
            if persona in slow:
                q = qs[self.qi % len(qs)]
                self.qi += 1
                return q
        return "Tell me about yourself."


async def main() -> None:
    llm = DemoLLM()

    print("=" * 64)
    print("STEP 1: analyze_brief  ->  job description becomes a brief card")
    print("=" * 64)
    card = await ab.analyze_brief(
        llm,
        "Senior AI Engineer needed. Must know Python, AWS, LangChain, Bedrock. "
        "Build RAG pipelines and multi-agent systems.",
        BriefType.JOB_POSTING,
    )
    print(f"  Title : {card.title}")
    print(f"  Skills: {', '.join(card.required_skills)}")
    print(f"  Topics: {', '.join(card.likely_topics)}")

    print("\n" + "=" * 64)
    print("STEP 2: start_session  ->  panel assembles, first interviewer speaks")
    print("=" * 64)
    cfg = SessionConfig(
        mode=SessionMode.INTERVIEW,
        personas=["staff_engineer", "hiring_manager"],
        max_turns=6,
    )
    sess = await se.start_session(llm, card, cfg)
    print(f"  [{sess.turns[0].speaker}] {sess.turns[0].text}")

    for i, answer in enumerate(ANSWERS, 1):
        print(f"\n--- Turn {i}: you answer ---")
        print(f"  [YOU] {answer}")
        result = await se.submit_answer(llm, sess.session_id, answer)
        score = result["score"]
        print(f"  [SCORE] {score.overall}/5  "
              f"(specificity={score.dimension_scores['specificity']}, "
              f"confidence={score.dimension_scores['confidence']})")
        tag = "FOLLOW-UP (adaptive!)" if result["type"] == "follow_up" else "next question"
        print(f"  [{tag} | {result['persona']}] {result['text']}")

    print("\n" + "=" * 64)
    print("STEP 3: get_session_report  ->  scores, gaps, tips")
    print("=" * 64)
    rep = await rp.get_session_report(llm, sess.session_id)
    print(rep["report_markdown"])
    print("Demo complete. The engine, scoring, and follow-up loop all ran for real.")


if __name__ == "__main__":
    asyncio.run(main())
