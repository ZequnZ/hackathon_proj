import functools
import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

from pydantic import BaseModel, create_model


class Tool:
    """Base class for LLM tools."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_model: type[BaseModel],
        function: Callable,
    ):
        # Tool metadata and callable
        self.name = name
        self.description = description
        self.parameters_model = parameters_model
        self.function = function

    def __call__(self, **kwargs):
        """Execute the tool with validated parameters."""
        validated_params = self.parameters_model(**kwargs)
        return self.function(**validated_params.model_dump())

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert the tool to OpenAI's function calling format."""
        schema = self.parameters_model.model_json_schema()

        # OpenAI expects a specific format
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    @classmethod
    def from_function(
        cls,
        function: Callable,
        name: str | None = None,
        description: str | None = None,
    ) -> "Tool":
        """Create a tool from a function with type hints."""
        if name is None:
            name = function.__name__

        if description is None:
            description = function.__doc__ or f"Tool for {name}"

        # Get type hints and signature from the function
        hints = get_type_hints(function)
        signature = inspect.signature(function)

        # Build Pydantic model fields from function signature
        fields = {}
        for param_name, param in signature.parameters.items():
            param_type = hints.get(param_name, Any)
            default = ... if param.default is inspect.Parameter.empty else param.default
            fields[param_name] = (param_type, default)

        # Create a Pydantic model for parameters
        parameters_model = create_model(f"{name.capitalize()}Parameters", **fields)

        return cls(name, description, parameters_model, function)


def create_tool(
    name: str, description: str, parameters_model: type[BaseModel]
) -> Callable[[Callable], Tool]:
    """Decorator to create a tool with a custom parameters model."""

    def decorator(func: Callable) -> Tool:
        # Wrap function as Tool with custom model
        tool = Tool(name, description, parameters_model, func)
        functools.update_wrapper(tool, func)
        return tool

    return decorator


class ToolRegistry:
    """Registry to keep track of all tools."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        """Register a tool in the registry."""
        self.tools[tool.name] = tool
        return tool

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools_by_schema(self) -> list[dict[str, Any]]:
        """List all registered tool schemas"""
        return [tool.to_openai_schema() for tool in self.tools.values()]

    def list_tools_by_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self.tools.keys())

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self.tools.values()]


# Create a global registry
registry = ToolRegistry()


def register_tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable], Tool]:
    """Decorator to create and register a tool from a function."""

    def decorator(func: Callable) -> Tool:
        # Create Tool from function and register it
        tool = Tool.from_function(func, name, description)
        registry.register(tool)
        return tool

    return decorator
