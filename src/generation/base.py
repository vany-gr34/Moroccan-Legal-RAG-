"""Abstract base for LLM generators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class GenerationResult:
    """Result from an LLM generation."""
    response: str
    tokens_generated: int
    generation_time_ms: float
    model_name: str


class BaseLLM(ABC):
    """Abstract interface for LLM generators."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> GenerationResult:
        """Generate a response from the LLM.

        Args:
            prompt: The full prompt to send.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.

        Returns:
            GenerationResult with response text and metadata.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this LLM."""
        pass
