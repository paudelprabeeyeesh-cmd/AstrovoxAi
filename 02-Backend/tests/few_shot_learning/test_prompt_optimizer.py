import pytest
from few_shot_learning.prompt_optimizer import PromptExample, PromptOptimizer


def test_add_example_and_stats():
    optimizer = PromptOptimizer()
    optimizer.add_example("apple is red", "fruit")
    optimizer.add_example("banana is yellow", "fruit")
    optimizer.add_example("carrot is orange", "vegetable")
    stats = optimizer.get_prompt_stats()
    assert stats["total_examples"] == 3
    assert stats["label_distribution"]["fruit"] == 2
    assert stats["label_distribution"]["vegetable"] == 1
    assert stats["num_labels"] == 2


def test_select_random():
    optimizer = PromptOptimizer()
    for i in range(10):
        optimizer.add_example(f"example {i}", str(i % 2))
    selected = optimizer.select_examples("query", n_examples=3, method="random")
    assert len(selected) == 3
    assert all(isinstance(ex, PromptExample) for ex in selected)


def test_select_diverse():
    optimizer = PromptOptimizer()
    optimizer.add_example("apple red", "fruit")
    optimizer.add_example("banana yellow", "fruit")
    optimizer.add_example("carrot orange", "vegetable")
    selected = optimizer.select_examples("query", n_examples=2, method="diverse")
    assert len(selected) == 2


def test_select_similar():
    optimizer = PromptOptimizer()
    optimizer.add_example("apple is red", "fruit")
    optimizer.add_example("banana is yellow", "fruit")
    optimizer.add_example("carrot is orange", "vegetable")
    selected = optimizer.select_examples("apple", n_examples=2, method="similar")
    assert len(selected) == 2


def test_format_examples():
    optimizer = PromptOptimizer()
    optimizer.add_example("hello world", "A")
    examples = optimizer.select_examples("hello", n_examples=1, method="random")
    formatted = optimizer.format_examples(examples)
    assert "Example 1:" in formatted
    assert "Query: hello world" in formatted
    assert "Label: A" in formatted


def test_optimize_prompt():
    optimizer = PromptOptimizer()
    optimizer.add_example("cat meows", "animal")
    optimizer.add_example("dog barks", "animal")
    prompt = optimizer.optimize_prompt("cat", n_examples=1, method="similar")
    assert "Query: cat" in prompt
    assert "Label:" in prompt


def test_evaluate_prompt():
    optimizer = PromptOptimizer()
    optimizer.add_example("cat meows", "animal")
    result = optimizer.evaluate_prompt("cat", expected_label="animal", n_examples=1, method="similar")
    assert result["correct"] is True
    assert result["accuracy"] == 1.0


def test_set_template():
    optimizer = PromptOptimizer()
    optimizer.set_template("{query} -> {label}")
    optimizer.add_example("x", "y")
    prompt = optimizer.optimize_prompt("test", n_examples=1, method="random")
    assert "test" in prompt


def test_unknown_method_raises():
    optimizer = PromptOptimizer()
    with pytest.raises(ValueError):
        optimizer.select_examples("query", n_examples=1, method="unknown")
