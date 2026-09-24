"""
Tests for product_polish.user_feedback_processor

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.user_feedback_processor import (  # noqa: E402
    FeedbackItem,
    UserFeedbackProcessor,
)


@pytest.fixture()
def processor():
    return UserFeedbackProcessor()


class TestFeedbackItemDataclass:
    def test_defaults(self):
        item = FeedbackItem(id="f1", user_id="u1", source="app", content="great!")
        assert item.category == "general"
        assert item.tags == []
        assert item.meta == {}
        assert item.rating is None
        assert item.created_at != ""

    def test_created_at_iso(self):
        item = FeedbackItem(id="f2", user_id="u2", source="web", content="ok")
        assert "T" in item.created_at

    def test_to_dict_keys(self):
        item = FeedbackItem(id="f3", user_id="u3", source="email", content="bad")
        d = item.to_dict()
        expected = {"id", "user_id", "source", "content", "rating", "category", "tags", "meta", "created_at"}
        assert set(d.keys()) == expected

    def test_custom_rating(self):
        item = FeedbackItem(id="f4", user_id="u4", source="app", content="", rating=4)
        assert item.rating == 4

    def test_custom_tags(self):
        item = FeedbackItem(id="f5", user_id="u5", source="app", content="", tags=["ui", "bug"])
        assert item.tags == ["ui", "bug"]


class TestUserFeedbackProcessorSubmit:
    def test_submit_returns_feedback_item(self, processor):
        item = processor.submit_feedback("u1", "app", "great!")
        assert isinstance(item, FeedbackItem)

    def test_submit_assigns_id(self, processor):
        item = processor.submit_feedback("u1", "app", "ok")
        assert item.id != ""

    def test_submit_rating_out_of_range_raises(self, processor):
        with pytest.raises(ValueError):
            processor.submit_feedback("u1", "app", "bad", rating=0)
        with pytest.raises(ValueError):
            processor.submit_feedback("u1", "app", "bad", rating=6)

    def test_submit_valid_rating(self, processor):
        item = processor.submit_feedback("u1", "app", "bad", rating=1)
        assert item.rating == 1


class TestUserFeedbackProcessorGet:
    def test_get_existing(self, processor):
        item = processor.submit_feedback("u1", "app", "great!")
        got = processor.get_feedback(item.id)
        assert got is not None
        assert got.content == "great!"

    def test_get_missing_returns_none(self, processor):
        assert processor.get_feedback("nonexistent") is None


class TestUserFeedbackProcessorList:
    def test_list_empty(self, processor):
        assert processor.list_feedback() == []

    def test_list_after_submit(self, processor):
        processor.submit_feedback("u1", "app", "great!")
        assert len(processor.list_feedback()) == 1

    def test_list_filter_by_category(self, processor):
        processor.submit_feedback("u1", "app", "ok", category="bug")
        processor.submit_feedback("u2", "app", "ok", category="feature")
        items = processor.list_feedback(category="bug")
        assert all(i.category == "bug" for i in items)

    def test_list_filter_by_min_rating(self, processor):
        processor.submit_feedback("u1", "app", "ok", rating=3)
        processor.submit_feedback("u2", "app", "ok", rating=5)
        items = processor.list_feedback(min_rating=4)
        assert all(i.rating >= 4 for i in items)

    def test_list_sorted_by_created_at_desc(self, processor):
        processor.submit_feedback("u1", "app", "first")
        import time
        time.sleep(0.01)
        processor.submit_feedback("u2", "app", "second")
        items = processor.list_feedback()
        assert items[0].content == "second"
        assert items[1].content == "first"


class TestUserFeedbackProcessorSearch:
    def test_search_returns_matches(self, processor):
        processor.submit_feedback("u1", "app", "the app is slow and buggy")
        results = processor.search("slow")
        assert len(results) == 1
        assert results[0].content == "the app is slow and buggy"

    def test_search_no_match_returns_empty(self, processor):
        processor.submit_feedback("u1", "app", "great!")
        assert processor.search("nonexistent") == []


class TestUserFeedbackProcessorAnalyze:
    def test_analyze_returns_total(self, processor):
        processor.submit_feedback("u1", "app", "ok")
        processor.submit_feedback("u2", "app", "ok")
        analysis = processor.analyze()
        assert analysis["total_feedback"] == 2

    def test_analyze_average_rating(self, processor):
        processor.submit_feedback("u1", "app", "ok", rating=3)
        processor.submit_feedback("u2", "app", "ok", rating=5)
        analysis = processor.analyze()
        assert analysis["average_rating"] == 4.0

    def test_analyze_by_category(self, processor):
        processor.submit_feedback("u1", "app", "ok", category="bug")
        processor.submit_feedback("u2", "app", "ok", category="bug")
        analysis = processor.analyze()
        assert analysis["by_category"]["bug"] == 2

    def test_analyze_empty_returns_none_average(self, processor):
        analysis = processor.analyze()
        assert analysis["average_rating"] is None
