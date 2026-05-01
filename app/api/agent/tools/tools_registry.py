"""
Tool Registry con auto-discovery.

Permite registrar tools en runtime y las descubre automáticamente
desde el directorio tools/, sin necesidad de modificar
initialize() cada vez que se agrega una tool nueva.
"""

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ....domain.exceptions import ToolNotFoundError

logger = logging.getLogger(__name__)


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
        Inicializa el registry con auto-discovery.

        Escanea el directorio tools/ buscando módulos que tengan
        funciones de registro (register_<module_name>_tool o register_tool)
        y las ejecuta automáticamente.

        No es necesario modificar este método para agregar nuevas tools.
        """
        if cls._initialized:
            return

        tools_dir = Path(__file__).parent

        for py_file in tools_dir.glob("*.py"):
            # Saltar archivos especiales y el propio registry
            if py_file.name.startswith("__") or py_file.name == "tools_registry.py":
                continue

            module_name = py_file.stem
            try:
                # Importar el módulo dinámicamente usando el package actual
                module = importlib.import_module(
                    f".{module_name}", package=__package__
                )

                # Buscar función de registro siguiendo convenciones
                registered = False

                # Convención 1: register_<module_name>_tool()
                register_func_specific = f"register_{module_name}_tool"
                if hasattr(module, register_func_specific):
                    getattr(module, register_func_specific)()
                    registered = True
                    logger.info(f"Registered tool from {module_name} via {register_func_specific}")

                # Convención 2: register_tool() genérico
                elif hasattr(module, "register_tool"):
                    module.register_tool()
                    registered = True
                    logger.info(f"Registered tool from {module_name} via register_tool")

                if not registered:
                    logger.debug(
                        f"Module {module_name} has no registration function, skipping"
                    )

            except Exception as e:
                logger.warning(f"Failed to load tool module {module_name}: {e}")

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
