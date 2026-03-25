from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict 
    handler: Callable

@dataclass
class ToolResponse:
    output: str
    metadata: Optional[dict] = None


TOOL_REGISTRY: dict[str, ToolDefinition] = {}

def register_tool(name: str, description: str, parameters: dict):
    """Decorador para registrar tools"""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=func
        )
        return func
    return decorator
