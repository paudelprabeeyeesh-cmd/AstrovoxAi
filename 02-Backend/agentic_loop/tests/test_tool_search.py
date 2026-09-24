import pytest
import numpy as np
from agentic_loop.tool_search import ToolSearchRegistry, ToolMetadata


def test_tool_search_registration_and_search():
    registry = ToolSearchRegistry()
    registry.register(ToolMetadata(name="weather", description="Get weather information", tags=["api"]))
    registry.register(ToolMetadata(name="calculator", description="Perform math calculations", tags=["math"]))
    registry.register(ToolMetadata(name="search", description="Search the web", tags=["api", "web"]))

    results = registry.semantic_search("weather forecast", top_k=2)
    assert len(results) == 2
    assert results[0].name == "weather"

    results = registry.semantic_search("math calculations", top_k=1)
    assert len(results) == 1
    assert results[0].name == "calculator"


def test_semantic_search_ranking():
    registry = ToolSearchRegistry()
    registry.register(ToolMetadata(name="a", description="alpha beta", tags=["t1"]))
    registry.register(ToolMetadata(name="b", description="alpha gamma", tags=["t2"]))
    registry.register(ToolMetadata(name="c", description="beta gamma", tags=["t3"]))

    results = registry.semantic_search("alpha", top_k=3)
    assert results[0].name == "a"
    assert results[1].name == "b"
    assert results[2].name == "c"


def test_empty_search_returns_empty():
    registry = ToolSearchRegistry()
    assert registry.semantic_search("nonexistent", top_k=5) == []
