"""Root API router plus providers info endpoint."""
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/ping")
def ping() -> dict:
    return {"pong": True}


@api_router.get("/providers")
def providers_info() -> dict:
    from ..providers import jev_mode, registry

    mode = jev_mode()
    return {
        "jev": mode,
        "jev_mock": mode == "mock",
        "llm_providers": sorted(registry().keys()),
    }


# Endpoint modules register their routes on import.
from . import executions, workflows  # noqa: E402,F401
