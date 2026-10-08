"""MockJevProvider — SIMULATION, clearly labelled as such.

Lets you build and test Jev Studio workflows without a TypeSafe API key.
It does NOT call any external service: it picks an option with a lightweight
keyword heuristic over the context and reports simulated=True in the result
so the UI can show that the decision is simulated.

Replace with TypeSafeJevProvider in production (set TYPESAFE_API_KEY).
"""
import hashlib
import re

from .jev_base import JevDecision, JevProvider


def _keyword_score(context: str, option: str) -> float:
    ctx = context.lower()
    words = [w for w in re.split(r"[^a-záéíóúñü]+", option.lower()) if len(w) >= 3]
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in ctx)
    return hits / len(words)


class MockJevProvider(JevProvider):
    name = "mock"
    simulated = True

    def decide(self, context: str, question: str, options: list[str]) -> JevDecision:
        if not options:
            raise ValueError("Jev decision needs at least one option")

        scored = [(opt, _keyword_score(context, opt)) for opt in options]
        best, best_score = max(scored, key=lambda t: t[1])
        if best_score == 0:
            # deterministic default so runs are reproducible
            digest = int(hashlib.sha256(context.encode()).hexdigest(), 16)
            best = options[digest % len(options)]
            best_score = 0.34
        else:
            best_score = min(0.55 + best_score * 0.4, 0.97)

        raw = {
            "simulated": True,
            "provider": "MockJevProvider",
            "note": "Simulación local: ningún modelo de decisión fue consultado.",
            "question": question,
            "scores": {opt: round(s, 4) for opt, s in scored},
        }
        return JevDecision(selected=best, confidence=round(best_score, 4), raw=raw, simulated=True)
