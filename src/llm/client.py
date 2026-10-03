"""LLM client interface.

Production: BedrockLLMClient (AWS Bedrock Converse API, Claude).
Local dev without AWS: MockLLMClient.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Return the model's text completion."""
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Deterministic stub for local dev — no AWS needed."""

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        return (
            "[MOCK] system_rules_applied. "
            f"Responding to: {last_user[:120]!r}. "
            "Wire up BedrockLLMClient for real output."
        )


class BedrockLLMClient(LLMClient):
    """AWS Bedrock (Claude) via the Converse API.

    Credentials come from the standard boto3 chain
    (env vars AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, ~/.aws/, IAM role).
    """

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
    ) -> None:
        import boto3

        self.model_id = model_id or os.environ.get(
            "BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6-v1:0"
        )
        self.region = region or os.environ.get("AWS_REGION", "us-east-2")
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        import asyncio

        converse_messages = [
            {
                "role": m["role"] if m["role"] in ("user", "assistant") else "user",
                "content": [{"text": m["content"]}],
            }
            for m in messages
        ]
        response = await asyncio.to_thread(
            self._client.converse,
            modelId=self.model_id,
            system=[{"text": system}],
            messages=converse_messages,
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        blocks = response["output"]["message"]["content"]
        return "".join(b["text"] for b in blocks if "text" in b).strip()


def make_client() -> LLMClient:
    """Strands agents on Bedrock when credentials are present, mock otherwise."""
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        from ..agents.strands_backend import StrandsBackend

        return StrandsLLMClient(StrandsBackend())
    return MockLLMClient()


class StrandsLLMClient(LLMClient):
    """LLMClient backed by Strands agents.

    The engine keeps calling complete(system, messages) exactly as before —
    but behind the interface, each distinct system prompt gets a real cached
    Strands Agent instead of a one-shot LLM call. Same contract, agent brains.
    """

    def __init__(self, backend=None) -> None:
        from ..agents.strands_backend import StrandsBackend, _text_of

        self.backend = backend or StrandsBackend()
        self._text_of = _text_of
        self._agents: dict[str, Agent] = {}

    def _agent_for(self, system: str):
        from strands import Agent

        if system not in self._agents:
            self._agents[system] = Agent(
                model=self.backend.model,
                system_prompt=system,
                name="hotseat-tool-agent",
            )
        return self._agents[system]

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        import asyncio

        agent = self._agent_for(system)
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        result = await asyncio.to_thread(agent, prompt)
        return self._text_of(result)
