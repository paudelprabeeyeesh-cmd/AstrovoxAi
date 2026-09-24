import pytest
import json
from agentic_loop.fine_grained_tool_call_streaming import (
    StreamingToolCaller,
    FineGrainedStreamingParser,
    StreamChunk,
)


def dummy_tool(x: int) -> int:
    return x + 1


def test_streaming_parser_partial_and_complete():
    parser = FineGrainedStreamingParser()
    chunk1 = parser.feed('{"tool')
    assert chunk1.error is None
    chunk2 = parser.feed('_name": "add", "arguments": {"x": 5}}')
    assert chunk2.is_complete is True
    assert chunk2.parsed_args == {"tool_name": "add", "arguments": {"x": 5}}


def test_streaming_parser_reset():
    parser = FineGrainedStreamingParser()
    parser.feed('{"partial": true')
    parser.reset()
    assert parser.buffer == ""


def test_streaming_tool_caller():
    tools = {"add": dummy_tool}
    caller = StreamingToolCaller(tools=tools)

    def stream_gen(prompt: str):
        yield '{"tool_name": "add", "arguments": {"x": 3}}'

    chunks = caller.stream_call(stream_gen)
    assert len(chunks) == 1
    assert chunks[0].is_complete is True
