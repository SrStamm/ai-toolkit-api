"""
Tests para el ToolRegistry con auto-discovery.
"""

import pytest

import sys
import os

# Agregar el directorio padre (ai-toolkit-api/) al path para que app/ sea importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestToolRegistry:
    """Tests para el ToolRegistry."""

    def setup_method(self):
        """Limpiar el registry antes de cada test."""
        from app.api.agent.tools import ToolRegistry

        ToolRegistry.clear()

    def test_register_tool(self):
        """Debería registrar una tool correctamente."""
        from app.api.agent.tools import ToolRegistry, ToolDefinition

        def dummy_handler(query: str, **kwargs):
            return "result"

        ToolRegistry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=dummy_handler,
            dependencies=[],
        )

        assert ToolRegistry.exists("test_tool")

        tool = ToolRegistry.get("test_tool")
        assert isinstance(tool, ToolDefinition)
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"

    def test_get_nonexistent_tool_raises(self):
        """Debería lanzar excepción si la tool no existe."""
        from app.api.agent.tools import ToolRegistry
        from app.domain.exceptions import ToolNotFoundError

        with pytest.raises(ToolNotFoundError):
            ToolRegistry.get("nonexistent")

    def test_unregister_tool(self):
        """Debería desregistrar una tool."""
        from app.api.agent.tools import ToolRegistry

        def dummy_handler(query: str, **kwargs):
            return "result"

        ToolRegistry.register(
            name="temp_tool",
            description="A temp tool",
            parameters={"type": "object", "properties": {}},
            handler=dummy_handler,
            dependencies=[],
        )

        assert ToolRegistry.exists("temp_tool")

        ToolRegistry.unregister("temp_tool")

        assert not ToolRegistry.exists("temp_tool")

    def test_list_tools(self):
        """Debería listar todas las tools registradas."""
        from app.api.agent.tools import ToolRegistry

        def handler1(**kwargs):
            return "1"

        def handler2(**kwargs):
            return "2"

        ToolRegistry.register(
            name="tool1",
            description="Tool 1",
            parameters={"type": "object"},
            handler=handler1,
        )
        ToolRegistry.register(
            name="tool2",
            description="Tool 2",
            parameters={"type": "object"},
            handler=handler2,
        )

        tools = ToolRegistry.list_tools()

        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_decorator_registration(self):
        """Debería funcionar como función con argumentos."""
        from app.api.agent.tools import ToolRegistry

        def my_handler(**kwargs):
            return "decorated"

        # Register as function call
        ToolRegistry.register(
            name="decorated_tool",
            description="Decorated tool",
            parameters={"type": "object", "properties": {}},
            handler=my_handler,
        )

        assert ToolRegistry.exists("decorated_tool")
        tool = ToolRegistry.get("decorated_tool")
        assert tool.handler is my_handler

    def test_initialize_registers_default_tools(self):
        """Initialize debería registrar las tools automáticamente."""
        from app.api.agent.tools import ToolRegistry

        # Verificar que inicialmente no hay tools
        initial_count = len(ToolRegistry.list_tools())
        
        ToolRegistry.initialize()

        # Después de initialize, debe haber al menos una tool registrada
        # (las que están en el directorio tools/)
        final_count = len(ToolRegistry.list_tools())
        assert final_count > initial_count, "Initialize debe registrar al menos una tool"

        # Verificar que se registró la tool de retrieve_context
        # (asumiendo que existe en el directorio)
        from pathlib import Path
        tools_dir = Path(__file__).parent.parent / "app" / "api" / "agent" / "tools"
        py_files = [f.stem for f in tools_dir.glob("*.py") 
                    if not f.name.startswith("__") and f.name != "tools_registry.py"]
        
        # Al menos debe haberse registrado una tool del directorio
        assert final_count >= len(py_files), (
            f"Se esperaba al menos {len(py_files)} tools registradas, "
            f"pero hay {final_count}"
        )

    def test_clear_resets_registry(self):
        """Clear debería limpiar todas las tools."""
        from app.api.agent.tools import ToolRegistry

        def handler(**kwargs):
            return "result"

        ToolRegistry.register(
            name="temp",
            description="Temp",
            parameters={"type": "object"},
            handler=handler,
        )

        assert ToolRegistry.exists("temp")

        ToolRegistry.clear()

        assert not ToolRegistry.exists("temp")
        assert not ToolRegistry._initialized
