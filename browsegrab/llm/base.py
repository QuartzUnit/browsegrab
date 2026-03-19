"""LLM Provider abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base for LLM providers (vLLM, Ollama, OpenAI-compatible)."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            The assistant's response text.
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider endpoint is reachable."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'vllm', 'ollama')."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model name being used."""

    async def plan_action(
        self,
        system_prompt: str,
        context: str,
        history: str,
        objective: str,
    ) -> dict[str, Any]:
        """Plan the next browser action given context.

        This is a convenience method that builds the message list
        and parses the JSON response.

        Args:
            system_prompt: System prompt with instructions.
            context: Current page snapshot.
            history: Compressed action history.
            objective: User's goal.

        Returns:
            Parsed action dict (e.g. {"action": "click", "ref": "e5"}).
        """
        from browsegrab.llm.parse import parse_action_json

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Objective: {objective}\n\nCurrent page:\n{context}\n\nHistory:\n{history}\n\nWhat action should I take next? Respond with JSON.",
            },
        ]
        response = await self.chat(messages)
        return parse_action_json(response)
