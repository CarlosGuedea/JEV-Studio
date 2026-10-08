"""Provider factory.

"auto" (default): real TypeSafe Jev when an API key is configured,
otherwise the mock — so development is never blocked.
"""
from ..config import get_settings
from .jev_base import JevProvider
from .jev_mock import MockJevProvider
from .jev_typesafe import TypeSafeJevProvider


def get_jev_provider(mode: str = "auto", model: str | None = None) -> JevProvider:
    settings = get_settings()
    if mode == "mock":
        return MockJevProvider()
    if mode == "typesafe":
        return TypeSafeJevProvider(model=model)
    # auto
    if settings.resolved_jev_api_key:
        return TypeSafeJevProvider(model=model)
    return MockJevProvider()


def jev_mode() -> str:
    return "typesafe" if get_settings().resolved_jev_api_key else "mock"
