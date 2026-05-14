import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Request
from starlette.responses import StreamingResponse

from .schemas import QueryAgentRequest
from .agent import create_agent

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/agent-loop/stream")
async def agent_loop_stream(query: QueryAgentRequest, request: Request):
    """Streaming version of agent-loop using Server-Sent Events."""
    agent = create_agent(
        provider=request.headers.get("x-llm-provider"),
        model=request.headers.get("x-llm-model"),
    )

    async def generate():
        async for event in agent.agent_loop_stream(
            query=query.text,
            session_id=query.session_id,
            file_uuid=query.file_uuid,
            filename=query.filename,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@router.post("/upload-file")
async def upload_agent_file(file: UploadFile = File(...)):
    """
    Upload a PDF file for the agent to ingest.

    Saves the file with a UUID name in the shared uploads directory.
    Returns the UUID and original filename so the frontend can include
    them in the next agent query.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "File must be a PDF"}

    # Generate UUID and ensure upload directory exists
    file_uuid = str(uuid.uuid4())
    upload_dir = Path("/backend/api_data") / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / f"{file_uuid}.pdf"

    # Save file to disk
    with upload_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"file_uuid": file_uuid, "filename": file.filename}


@router.get("/providers", summary="List available LLM providers and models")
def list_providers() -> dict:
    """
    List all available LLM providers and models configured in YAML.

    Returns a dictionary with a "providers" key containing a list of providers.
    Each provider includes:
    - name: Provider name
    - default_model: Default model for the provider (optional)
    - models: List of available models with name, max_tokens, and supports_tools
    """
    from ...core.settings import get_settings

    settings = get_settings()
    return {
        "providers": [
            {
                "name": provider.name,
                "default_model": provider.default_model,
                "models": [
                    {
                        "name": model.name,
                        "max_tokens": model.max_tokens,
                        "supports_tools": model.supports_tools,
                    }
                    for model in provider.models
                ],
            }
            for provider in settings.yaml_config.providers
        ]
    }
