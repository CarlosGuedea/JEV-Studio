"""JevProvider tests: interface, mock behaviour, TypeSafe wire format."""
import pytest

from app.providers.jev_base import JevDecision
from app.providers.jev_mock import MockJevProvider
from app.providers.jev_typesafe import TypeSafeJevProvider


class TestMockJevProvider:
    def setup_method(self):
        self.provider = MockJevProvider()

    def test_returns_one_of_the_options(self):
        decision = self.provider.decide("analiza datos con python", "¿ruta?", ["SQL", "PYTHON", "LLM"])
        assert decision.selected in ["SQL", "PYTHON", "LLM"]

    def test_keyword_match_prefers_python(self):
        decision = self.provider.decide("necesito un script python", "¿ruta?", ["SQL", "PYTHON", "LLM"])
        assert decision.selected == "PYTHON"
        assert decision.confidence > 0.5

    def test_is_marked_as_simulation(self):
        decision = self.provider.decide("texto sin palabras clave zz", "¿ruta?", ["A", "B"])
        assert decision.simulated is True
        assert decision.raw["simulated"] is True
        assert "MockJevProvider" in decision.raw["provider"]

    def test_deterministic_default(self):
        d1 = self.provider.decide("sin coincidencias", "q", ["A", "B"])
        d2 = self.provider.decide("sin coincidencias", "q", ["A", "B"])
        assert d1.selected == d2.selected

    def test_no_options_raises(self):
        with pytest.raises(ValueError):
            self.provider.decide("ctx", "q", [])


class TestTypeSafeJevProvider:
    def test_requires_api_key(self):
        provider = TypeSafeJevProvider(api_key=None)
        provider.api_key = None
        with pytest.raises(RuntimeError):
            provider.decide("ctx", "q", ["A"])

    def test_wire_format(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"model": "jev-1.13.0",
                        "answers": {"decision": {"choice": "PYTHON", "confidence": 0.91}},
                        "usage": {}}

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return FakeResponse()

        import httpx
        monkeypatch.setattr(httpx, "Client", FakeClient)

        provider = TypeSafeJevProvider(api_key="secret", base_url="https://api.typesafe.ai")
        decision = provider.decide("ctx texto", "¿ruta?", ["SQL", "PYTHON"])

        assert captured["url"] == "https://api.typesafe.ai/v1/systemone"
        assert captured["headers"]["Authorization"] == "Bearer secret"
        body = captured["json"]
        assert body["state"] == "ctx texto"
        assert body["model"]
        q = body["questions"]["decision"]
        assert q["type"] == "choice"
        assert q["criteria"]["PYTHON"] == "PYTHON"

        assert isinstance(decision, JevDecision)
        assert decision.selected == "PYTHON"
        assert decision.confidence == pytest.approx(0.91)
        assert decision.simulated is False


def test_interface_contract():
    from app.providers.jev_base import JevProvider
    assert hasattr(JevProvider, "decide")
