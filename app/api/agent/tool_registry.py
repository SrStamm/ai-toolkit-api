from dataclasses import dataclass
from typing import Callable

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict 
    handler: Callable


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
