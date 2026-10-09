import pytest
from multi_agent.task124_hierarchical import HierarchicalAgent


class TestHierarchicalAgent:
    def test_context_window_depth(self):
        root = HierarchicalAgent("root", max_depth=4, base_window=16)
        assert root.context_window_at_depth(0) == 16
        assert root.context_window_at_depth(1) == 8
        assert root.context_window_at_depth(2) == 4

    def test_delegate_execution(self):
        root = HierarchicalAgent("root", max_depth=3, base_window=16)
        child = HierarchicalAgent("child")
        root.register("child", child)
        context = [1, 2, 3, 4, 5, 6, 7, 8]
        result = root.delegate("child", context, depth=0)
        assert isinstance(result, list)

    def test_max_depth_exceeded(self):
        root = HierarchicalAgent("root", max_depth=1, base_window=16)
        child = HierarchicalAgent("child")
        root.register("child", child)
        with pytest.raises(RuntimeError):
            root.delegate("child", [], depth=1)

    def test_compress_for_depth_list(self):
        root = HierarchicalAgent("root", max_depth=3, base_window=4)
        context = [10, 20, 30, 40, 50]
        compressed = root.compress_for_depth(context, depth=0)
        assert len(compressed) == 4

    def test_register_and_delegate_missing(self):
        root = HierarchicalAgent("root", max_depth=3, base_window=16)
        with pytest.raises(ValueError):
            root.delegate("missing", [])
