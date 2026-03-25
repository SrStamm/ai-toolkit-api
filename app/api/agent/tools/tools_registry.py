from dataclasses import field, dataclass
from typing import Callable, Optional

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict 
    handler: Callable
    dependencies: list[str] = field(default_factory=list)

@dataclass
class ToolResponse:
    output: str
    metadata: Optional[dict] = None


TOOL_REGISTRY: dict[str, ToolDefinition] = {}

def register_tool(name: str, description: str, parameters: dict, dependencies: list):
    """Decorador para registrar tools"""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            dependencies=dependencies
        )
        return func
    return decorator
