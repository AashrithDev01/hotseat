"""analyze_brief tool.

Turns a job description OR a meeting brief into a structured BriefCard.
LLM-backed in production; keyword-heuristic fallback for local dev.
"""

from __future__ import annotations

import re

from ..llm.client import LLMClient
from ..llm.json_utils import extract_json
from ..models.session import BriefCard, BriefType

ANALYZE_SYSTEM = """\
You extract structured facts from a brief. Given the brief text and its type,
return JSON matching this schema:
{
  "title": "<role title OR meeting objective>",
  "summary": "<2-3 sentence summary>",
  "seniority": "<junior|mid|senior|staff|null>",
  "required_skills": ["..."],
  "likely_topics": ["..."],
  "audience": "<who is in the room, or null>",
  "key_points": ["..."],
  "likely_objections": ["..."],
  "ask": "<what the presenter needs from the room, or null>"
}
Fill the fields relevant to the brief type; use null/[] for the others.
"""


def _heuristic_fallback(brief_text: str, brief_type: BriefType) -> BriefCard:
    skills = sorted(
        {
            s
            for s in re.findall(
                r"\b(Python|Java|AWS|GCP|Azure|Kubernetes|React|LangChain|"
                r"Bedrock|MCP|SQL|Spark|Terraform|FastAPI|Docker)\b",
                brief_text,
                re.IGNORECASE,
            )
        }
    )
    if brief_type == BriefType.JOB_POSTING:
        return BriefCard(
            brief_type=brief_type,
            title="Role (parsed locally)",
            summary=brief_text[:200],
            required_skills=skills,
            likely_topics=["background walkthrough", "technical deep-dive", "behavioral"],
        )
    return BriefCard(
        brief_type=brief_type,
        title="Meeting (parsed locally)",
        summary=brief_text[:200],
        key_points=[brief_text[:120]],
        likely_objections=["cost", "timeline", "feasibility"],
        ask="TBD",
    )


async def analyze_brief(
    llm: LLMClient, brief_text: str, brief_type: BriefType
) -> BriefCard:
    raw = await llm.complete(
        ANALYZE_SYSTEM,
        [
            {
                "role": "user",
                "content": f"Brief type: {brief_type.value}\nBrief:\n{brief_text[:4000]}",
            }
        ],
        max_tokens=800,
        temperature=0.2,
    )
    if raw.startswith("[MOCK]"):
        return _heuristic_fallback(brief_text, brief_type)
    data = extract_json(raw)
    data["brief_type"] = brief_type
    return BriefCard.model_validate(data)
