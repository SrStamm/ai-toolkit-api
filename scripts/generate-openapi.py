"""Generate the RAG-only OpenAPI schema committed at the repository root."""

import json
from pathlib import Path

from fastapi import FastAPI

from app.api.retrieval_engine.router import router

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "openapi.json"


def build_schema_app() -> FastAPI:
    """Return a schema-only app with no lifespan and only the RAG router."""
    app = FastAPI()
    app.include_router(router)
    return app


def main() -> None:
    schema = build_schema_app().openapi()
    OUTPUT_PATH.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
