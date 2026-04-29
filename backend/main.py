"""Container entrypoint — re-exports the FastAPI app for ``uvicorn main:app``.

The actual application factory lives at ``src.interfaces.api.main:create_app``
per the layered architecture in ``research.md`` §2.
"""

from src.interfaces.api.main import app

__all__ = ["app"]
