"""
Tools para el agente.

Este módulo exporta las functions de registro y las clases del registry.
"""

from .tools_registry import ToolRegistry, ToolDefinition, ToolExecutionResult, register_tool

# Exports para backwards compatibility
__all__ = [
    "ToolRegistry",
    "ToolDefinition",
    "ToolExecutionResult",
    "register_tool",
]
