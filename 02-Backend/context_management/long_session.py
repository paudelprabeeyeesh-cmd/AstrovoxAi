from typing import List, Optional


class ToolCall:
    def __init__(self, id: str, name: str, tokens: int, result: str = ""):
        self.id = id
        self.name = name
        self.tokens = tokens
        self.result = result


class SubAgentTask:
    def __init__(self, id: str, description: str, max_tokens: int = 1000):
        self.id = id
        self.description = description
        self.max_tokens = max_tokens
        self.context_tokens = 0
        self.result = ""

    def set_context(self, tokens: int):
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        self.context_tokens = min(tokens, self.max_tokens)

    def set_result(self, result: str):
        self.result = result


class LongSessionManager:
    def __init__(self, max_tool_calls: int = 50, eviction_threshold: int = 40):
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1")
        if eviction_threshold < 1 or eviction_threshold > max_tool_calls:
            raise ValueError("eviction_threshold must be between 1 and max_tool_calls")
        self.max_tool_calls = max_tool_calls
        self.eviction_threshold = eviction_threshold
        self.tool_calls: List[ToolCall] = []
        self.sub_agents: List[SubAgentTask] = []
        self.evicted_count = 0

    def add_tool_call(self, tool_call: ToolCall) -> Optional[SubAgentTask]:
        self.tool_calls.append(tool_call)
        if len(self.tool_calls) >= self.eviction_threshold:
            return self._evict_and_delegate()
        return None

    def _evict_and_delegate(self) -> SubAgentTask:
        to_evict = self.tool_calls[: len(self.tool_calls) - self.eviction_threshold // 2]
        self.evicted_count += len(to_evict)
        self.tool_calls = self.tool_calls[len(to_evict):]
        task = SubAgentTask(id=f"sub-{len(self.sub_agents)+1}", description="Evicted tool results")
        task.set_context(sum(t.tokens for t in to_evict))
        task.set_result(f"Evicted {len(to_evict)} tool calls")
        self.sub_agents.append(task)
        return task

    def get_active_tool_count(self) -> int:
        return len(self.tool_calls)

    def get_sub_agent_count(self) -> int:
        return len(self.sub_agents)

    def get_total_tokens(self) -> int:
        return sum(t.tokens for t in self.tool_calls)
