
from product_polish.user_feedback_processor import UserFeedbackProcessor


def test_submit_and_get_feedback():
    processor = UserFeedbackProcessor()
    item = processor.submit_feedback(
        user_id="u1",
        source="web",
        content="Love the new design!",
        rating=5,
        category="ui",
        tags=["positive"],
    )
    assert item.user_id == "u1"
    assert item.rating == 5
    assert item.tags == ["positive"]

    fetched = processor.get_feedback(item.id)
    assert fetched is not None
    assert fetched.content == "Love the new design!"


def test_invalid_rating_raises():
    processor = UserFeedbackProcessor()
    try:
        processor.submit_feedback("u1", "web", "Bad rating", rating=6)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for rating out of range")


def test_list_feedback_with_filters():
    processor = UserFeedbackProcessor()
    processor.submit_feedback("u1", "web", "Slow bug", rating=2, category="bug")
    processor.submit_feedback("u2", "app", "Great app", rating=5, category="ui")
    processor.submit_feedback("u3", "web", "Another bug", rating=1, category="bug")

    bugs = processor.list_feedback(category="bug")
    assert len(bugs) == 2

    high_rated = processor.list_feedback(min_rating=4)
    assert len(high_rated) == 1
    assert high_rated[0].rating == 5


def test_analyze_returns_summary():
    processor = UserFeedbackProcessor()
    processor.submit_feedback("u1", "web", "This app is awesome", rating=5)
    processor.submit_feedback("u2", "app", "Slow and buggy issue", rating=2)

    analysis = processor.analyze()
    assert analysis["total_feedback"] == 2
    assert abs(analysis["average_rating"] - 3.5) < 1e-9
    assert "awesome" in analysis["positive_keywords"]
    assert "bug" in analysis["negative_keywords"]


def test_search_returns_ranked_results():
    processor = UserFeedbackProcessor()
    processor.submit_feedback("u1", "web", "Login bug login bug")
    processor.submit_feedback("u2", "app", "Fast login experience")

    results = processor.search("login")
    assert len(results) == 2
    assert results[0].user_id == "u1"
