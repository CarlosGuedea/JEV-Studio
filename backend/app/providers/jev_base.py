"""JevProvider abstraction.

Interface:
    decide(context, question, options) -> JevDecision

Concrete implementations adapt to the real API of Jev (TypeSafe System One):
POST {base_url}/v1/systemone  body {state, questions, model}  Bearer <key>.
Question types: choice | score | noul. Answers arrive in `answers[key]`
with a calibrated `confidence`.

Never invent the API: TypeSafeJevProvider follows the documented wire format.
MockJevProvider is a clearly-labelled simulation for development without a key.
"""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class JevDecision(BaseModel):
    selected: str                 # chosen option (exact option string)
    confidence: float | None      # calibrated confidence when provided
    raw: dict[str, Any]           # original provider response, unmodified
    simulated: bool = False       # True when produced by MockJevProvider


class JevProvider(ABC):
    """Decision provider interface. Implementations must be side-effect free
    apart from the network call to the decision API."""

    name: str = "abstract"
    simulated: bool = False

    @abstractmethod
    def decide(self, context: str, question: str, options: list[str]) -> JevDecision:
        """Pick one of `options` given free-text `context` and `question`."""
