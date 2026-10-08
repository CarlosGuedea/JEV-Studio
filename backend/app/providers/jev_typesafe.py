"""TypeSafeJevProvider — real Jev integration (TypeSafe AI, System One model).

Official transport: POST {base_url}/v1/systemone
    headers: Authorization: Bearer <api key>
    body:    {"state": str, "questions": {...}, "model": "jev-latest"}
    question types: choice | score | noul

For a decision over options we send one `choice` question whose criteria map
each option to itself; the response's answers[key].choice carries the pick and
answers[key].confidence the calibrated confidence.
"""
import httpx

from ..config import get_settings
from .jev_base import JevDecision, JevProvider


class TypeSafeJevProvider(JevProvider):
    name = "typesafe"
    simulated = False

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.resolved_jev_api_key
        self.base_url = (base_url or settings.jev_base_url).rstrip("/")
        self.model = model or settings.jev_model
        self.timeout = timeout or settings.jev_timeout_seconds

    def decide(self, context: str, question: str, options: list[str]) -> JevDecision:
        if not self.api_key:
            raise RuntimeError(
                "TypeSafeJevProvider requires an API key. Set TYPESAFE_API_KEY "
                "or JEV_API_KEY in the environment (never inside a workflow)."
            )
        if not options:
            raise ValueError("Jev decision needs at least one option")

        key = "decision"
        payload = {
            "state": context,
            "model": self.model,
            "questions": {
                key: {
                    "type": "choice",
                    "instructions": question,
                    "criteria": {opt: opt for opt in options},
                }
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/v1/systemone",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        answers = data.get("answers") or {}
        ans = answers.get(key) or {}
        selected = ans.get("choice")
        if selected not in options:
            # Provider returned an unexpected label: fall back to best-effort match.
            selected = next((o for o in options if str(selected).strip().upper() == o.upper()), options[0])
        confidence = ans.get("confidence")
        return JevDecision(
            selected=selected,
           confidence=float(confidence) if confidence is not None else None,
            raw=data,
            simulated=False,
        )
