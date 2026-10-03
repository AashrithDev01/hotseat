"""Strands backend — personas and evaluator as real AI agents.

THE LESSON: what makes this an "agent" and not just a prompt?
  1. MODEL   — the brain (Bedrock Claude). Shared by all agents.
  2. SYSTEM PROMPT — the agent's identity and rules (our persona prompts).
  3. LOOP    — Strands runs think -> act -> observe until done. We don't
               write the loop; the Agent owns it.

  Before:  llm.complete(system_prompt, messages)   # one shot, we manage everything
  After:   agent(task)                              # the agent runs its loop

For the evaluator we use *structured output*: instead of begging the model
for JSON and parsing it ourselves, we hand Strands our pydantic TurnScore
and get a typed object back. No regex, no extract_json.
"""

from __future__ import annotations

import asyncio
import os

from strands import Agent
from strands.models import BedrockModel

from .evaluator import EVALUATOR_SYSTEM_PROMPT, rubric_for_mode
from .personas import PERSONAS
from ..models.session import TurnScore

DEFAULT_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"
)
DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-2")


def _text_of(result) -> str:
    """Pull plain text out of a Strands AgentResult."""
    message = result.message
    content = message.get("content", []) if isinstance(message, dict) else []
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and "text" in block
    ]
    return "".join(parts).strip()


class StrandsBackend:
    """Owns one shared Bedrock model and a family of cached agents."""

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, region: str = DEFAULT_REGION):
        # The shared brain. Every agent below thinks with this model.
        self.model = BedrockModel(model_id=model_id, region_name=region)
        self._persona_agents: dict[str, Agent] = {}
        self._evaluators: dict[str, Agent] = {}

    # -- personas -----------------------------------------------------
    def persona_agent(self, persona_key: str) -> Agent:
        """One cached agent per persona. The persona prompt IS the agent's identity."""
        if persona_key not in self._persona_agents:
            persona = PERSONAS[persona_key]
            self._persona_agents[persona_key] = Agent(
                model=self.model,
                system_prompt=persona.system_prompt,
                name=f"hotseat-{persona_key}",
            )
        return self._persona_agents[persona_key]

    async def persona_say(self, persona_key: str, task: str) -> str:
        agent = self.persona_agent(persona_key)
        result = await asyncio.to_thread(agent, task)
        return _text_of(result)

    # -- evaluator ----------------------------------------------------
    def evaluator_agent(self, mode: str) -> Agent:
        """Evaluator agent with the mode's rubric baked into its identity."""
        if mode not in self._evaluators:
            rubric = rubric_for_mode(mode)
            rubric_text = "\n".join(f"- {k}: {v}" for k, v in rubric.items())
            self._evaluators[mode] = Agent(
                model=self.model,
                system_prompt=EVALUATOR_SYSTEM_PROMPT + "\nRubric:\n" + rubric_text,
                name=f"hotseat-evaluator-{mode}",
            )
        return self._evaluators[mode]

    async def evaluate(self, mode: str, transcript: str) -> TurnScore:
        """Score a turn. Returns a typed TurnScore — no JSON parsing."""
        agent = self.evaluator_agent(mode)
        result = await asyncio.to_thread(
            agent,
            f"Score this transcript:\n{transcript}",
            structured_output_model=TurnScore,
        )
        scored = result.structured_output
        assert isinstance(scored, TurnScore), f"Expected TurnScore, got {type(scored)}"
        return scored
