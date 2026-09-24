import json
import re
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class StreamChunk:
    content: str
    is_complete: bool
    parsed_args: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FineGrainedStreamingParser:
    def __init__(self):
        self.buffer = ""

    def feed(self, chunk: str) -> StreamChunk:
        self.buffer += chunk
        try:
            parsed = self._partial_parse()
            return StreamChunk(content=chunk, is_complete=self._is_complete(parsed), parsed_args=parsed)
        except Exception as e:
            return StreamChunk(content=chunk, is_complete=False, error=str(e))

    def _partial_parse(self) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(self.buffer)
        except json.JSONDecodeError:
            if '"tool_name"' in self.buffer and '"arguments"' in self.buffer:
                return {"tool_name": "", "arguments": {}}
            return None

    def _is_complete(self, parsed: Optional[Dict[str, Any]]) -> bool:
        return parsed is not None and "tool_name" in parsed and "arguments" in parsed

    def reset(self) -> None:
        self.buffer = ""


class StreamingToolCaller:
    def __init__(self, tools: Dict[str, Callable]):
        self.tools = tools
        self.parser = FineGrainedStreamingParser()

    def stream_call(self, stream_generator: Callable[[str], Any]) -> List[StreamChunk]:
        chunks: List[StreamChunk] = []
        self.parser.reset()
        for partial in stream_generator(""):
            chunk = self.parser.feed(partial)
            chunks.append(chunk)
            if chunk.is_complete and chunk.parsed_args:
                break
        return chunks
