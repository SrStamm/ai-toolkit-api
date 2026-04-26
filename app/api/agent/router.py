from fastapi import APIRouter, Request, Depends
from .schemas import QueryAgentRequest
from .agent import create_agent
from ...core.settings import get_settings, YamlAppConfig


router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/agent-loop")
def agent_loop(query: QueryAgentRequest, request: Request):
    agent = create_agent(
        provider=request.headers.get("x-llm-provider"),
        model=request.headers.get("x-llm-model"),
    )
    return agent.agent_loop(
        query=query.text,
        session_id=query.session_id
    )


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