"""
Abstract base class for LLM backends.

All backends must implement generate(). This lets the eval harness swap
MockBackend ↔ OpenAIBackend without touching pipeline logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.schema.models import SituationalReport


class LLMBackend(ABC):
    """Interface every backend must satisfy."""

    @abstractmethod
    def generate(
        self,
        event: dict[str, Any],
        retrieved_context: dict[str, list[dict[str, Any]]],
    ) -> SituationalReport:
        """
        Generate a SituationalReport for the given event.

        Args:
            event: The input event dict (event_id, shap_values, metadata, etc.)
            retrieved_context: Dict with keys 'regulations' and 'historicals',
                               each a list of retrieved chunk dicts.

        Returns:
            A SituationalReport — either confident or degraded.
        """
        ...
