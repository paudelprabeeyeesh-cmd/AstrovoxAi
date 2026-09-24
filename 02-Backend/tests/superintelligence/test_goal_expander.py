import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.goal_expander import (
    GoalExpander,
    GoalNode,
)


class TestGoalExpander:
    def test_expand_creates_root(self):
        expander = GoalExpander(max_depth=3, branching_factor=2)
        root = expander.expand("build system")
        assert isinstance(root, GoalNode)
        assert root.depth == 0
        assert root.description == "build system"

    def test_expand_creates_children(self):
        expander = GoalExpander(max_depth=3, branching_factor=2)
        root = expander.expand("build system")
        assert len(root.children) == 2

    def test_total_goals_count(self):
        expander = GoalExpander(max_depth=2, branching_factor=2)
        root = expander.expand("build system")
        count = expander.get_total_goals(root)
        assert count == 1 + 2 + 4

    def test_leaf_goals(self):
        expander = GoalExpander(max_depth=2, branching_factor=2)
        root = expander.expand("build system")
        leaves = expander.get_leaf_goals(root)
        assert len(leaves) == 4
        assert all(len(leaf.children) == 0 for leaf in leaves)

    def test_prioritize_goals(self):
        expander = GoalExpander(max_depth=2, branching_factor=2)
        root = expander.expand("build system")
        ordered = expander.prioritize_goals(root)
        assert len(ordered) == 7
        priorities = [node.priority for node in ordered]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_goal_tree(self):
        expander = GoalExpander(max_depth=2, branching_factor=2)
        root = expander.expand("build system")
        tree = expander.get_goal_tree(root)
        assert "id" in tree
        assert "children" in tree
        assert len(tree["children"]) == 2

    def test_expansion_stats(self):
        expander = GoalExpander(max_depth=2, branching_factor=2)
        expander.expand("build system")
        stats = expander.get_expansion_stats()
        assert stats["total_expansions"] == 6
        assert stats["max_depth"] == 2
        assert stats["branching_factor"] == 2
