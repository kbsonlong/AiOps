"""AIOps API package."""

from .health import router as health_router
from .skill_api import app

__all__ = [
    "health_router",
    "app",
]
