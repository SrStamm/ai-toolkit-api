"""
ToolRunner: Ejecuta herramientas con manejo de dependencias.

Componente separado del Agent para manejar la ejecución de herramientas.
"""

import structlog
from typing import Any
from .schemas import AgentState
from .tools import ToolRegistry, ToolResponse
from ...domain.exceptions import ToolNotFoundError

log = structlog.get_logger()


class ToolRunner:
    """Ejecuta herramientas con resolución de dependencias."""

    def __init__(self, deps: dict[str, Any]):
        self.deps = deps
        ToolRegistry.initialize()
        self.tools = ToolRegistry.list_tools()
    
    def run(self, tool_name: str, args: dict | None = None, state: AgentState | None = None) -> ToolResponse:
        """Ejecuta una herramienta por nombre.
        
        Args:
            tool_name: Nombre de la herramienta a ejecutar
            args: Argumentos adicionales para la herramienta
            state: Estado del agente para mapeo de campos
            
        Returns:
            ToolResponse con el resultado de la ejecución
            
        Raises:
            ToolNotFoundError: Si la herramienta no existe
        """
        if tool_name not in self.tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")
        
        tool_def = self.tools[tool_name]
        
        # Resolver dependencias (explícitas)
        relevant_deps = {
            k: v for k, v in self.deps.items()
            if k in tool_def.dependencies
        }
        
        # Mapear state a tool params (explícito)
        state_params = {}
        if state:
            tool_params = tool_def.parameters.get("properties", {})
            for param_name in tool_params:
                if hasattr(state, param_name):
                    state_params[param_name] = getattr(state, param_name)
        
        # Construir kwargs: state_params + args override, luego deps
        final_kwargs = {
            **state_params,
            **(args or {}),
            **relevant_deps
        }
        
        # Ejecutar la herramienta
        result = tool_def.handler(**final_kwargs)
        
        # Log de trazabilidad: decisión del agente
        log.info(
            "agent_tool_executed",
            tool_name=tool_name,
            args=args or {},
            result_preview=result.content[:500] if len(result.content) > 500 else result.content,
            result_length=len(result.content),
        )
        
        return result
