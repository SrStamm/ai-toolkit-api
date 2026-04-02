"""
Tool Registry con lazy registration.

Permite registrar tools en runtime en vez de al importar el módulo.
Esto evita side effects al import y permite testing más fácil.
"""

from dataclasses import dataclass, field
from typing import Callable, Any

from app.domain.exceptions import ToolNotFoundError


@dataclass
class ToolDefinition:
    """Definición de una tool para el agente."""

    name: str
    description: str
    parameters: dict
    handler: Callable
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ToolResponse:
    """Respuesta de una tool ejecutada."""

    output: str
    metadata: dict | None = None


class ToolRegistry:
    """
    Registry centralizado de tools para el agente.

    Usa lazy registration para evitar side effects al importar.
    """

    _tools: dict[str, ToolDefinition] = {}
    _initialized: bool = False

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
        dependencies: list[str] | None = None,
    ) -> Callable:
        """
        Registra una tool.

        Puede usarse como decorador o como función directa.

        Usage:
            # Como decorador
            @ToolRegistry.register(name="my_tool", ...)
            def my_tool_handler(...):
                ...

            # Como función directa
            def my_handler(...):
                ...
            ToolRegistry.register(name="my_tool", handler=my_handler, ...)
        """

        def decorator(func: Callable) -> Callable:
            cls._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                dependencies=dependencies or [],
            )
            return func

        # Si se usa como decorador, func viene del argumento
        # Si se usa directamente, handler es el argumento
        if handler is not None:
            # Se llamó como función directa
            if callable(handler):
                cls._tools[name] = ToolDefinition(
                    name=name,
                    description=description,
                    parameters=parameters,
                    handler=handler,
                    dependencies=dependencies or [],
                )
            return handler

        # Se usó como decorador
        return decorator

    @classmethod
    def get(cls, name: str) -> ToolDefinition:
        """Obtiene una tool por nombre."""
        if name not in cls._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")
        return cls._tools[name]

    @classmethod
    def list_tools(cls) -> dict[str, ToolDefinition]:
        """Lista todas las tools registradas."""
        return cls._tools.copy()

    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a tool exists."""
        return name in cls._tools

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Desregistra una tool. Returns True si existía."""
        if name in cls._tools:
            del cls._tools[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Limpia todas las tools registradas. Útil para testing."""
        cls._tools.clear()
        cls._initialized = False

    @classmethod
    def initialize(cls) -> None:
        """
        Inicializa el registry con las tools default.

        Se llama explícitamente cuando se necesita,
        no al importar el módulo.
        """
        if cls._initialized:
            return

        # Importar las tools lazily
        from .direct import register_direct_tool
        from .rag import register_rag_tool

        register_direct_tool()
        register_rag_tool()

        cls._initialized = True


# Alias para backwards compatibility
TOOL_REGISTRY = ToolRegistry


def register_tool(
    name: str,
    description: str,
    parameters: dict,
    handler: Callable,
    dependencies: list[str] | None = None,
) -> Callable:
    """
    Decorador/función para registrar tools.

    Deprecated: Usar ToolRegistry.register() directamente.
    """
    return ToolRegistry.register(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
        dependencies=dependencies,
    )
