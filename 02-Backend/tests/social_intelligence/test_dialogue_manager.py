from social_intelligence.dialogue_manager import (
    DialogueManager,
    DialogueTurn,
    SpeakerRole,
    TopicStatus,
)


class TestDialogueManager:
    def setup_method(self):
        self.manager = DialogueManager(max_turns_per_topic=3)

    def test_add_turn_returns_turn(self):
        turn = self.manager.add_turn(SpeakerRole.USER, "Hello there")
        assert isinstance(turn, DialogueTurn)
        assert turn.text == "Hello there"

    def test_history_grows(self):
        self.manager.add_turn(SpeakerRole.USER, "Hi")
        self.manager.add_turn(SpeakerRole.AGENT, "Hello")
        assert len(self.manager.history) == 2

    def test_topic_created_on_first_turn(self):
        self.manager.add_turn(SpeakerRole.USER, "Price?", topic="pricing")
        assert "pricing" in self.manager.topics

    def test_active_topics_empty_initially(self):
        assert self.manager.get_active_topics() == []

    def test_get_topic_history_filters(self):
        self.manager.add_turn(SpeakerRole.USER, "A", topic="t1")
        self.manager.add_turn(SpeakerRole.AGENT, "B", topic="t2")
        assert len(self.manager.get_topic_history("t1")) == 1
        assert len(self.manager.get_topic_history("t2")) == 1

    def test_resolve_topic(self):
        self.manager.add_turn(SpeakerRole.USER, "X", topic="t1")
        self.manager.resolve_topic("t1")
        assert self.manager.topics["t1"].status == TopicStatus.RESOLVED

    def test_defer_after_max_turns(self):
        for i in range(3):
            self.manager.add_turn(SpeakerRole.USER, f"M{i}", topic="t1")
        assert self.manager.topics["t1"].status == TopicStatus.DEFERRED

    def test_summary_keys(self):
        self.manager.add_turn(SpeakerRole.USER, "Hi")
        summary = self.manager.get_summary()
        assert "total_turns" in summary
        assert "active_topics" in summary
        assert "resolved_topics" in summary

    def test_sentiment_positive(self):
        turn = self.manager.add_turn(SpeakerRole.USER, "Great thanks happy agree")
        assert turn.sentiment > 0.0

    def test_sentiment_negative(self):
        turn = self.manager.add_turn(SpeakerRole.USER, "Bad sorry no hate angry")
        assert turn.sentiment < 0.0

    def test_sentiment_neutral(self):
        turn = self.manager.add_turn(SpeakerRole.USER, "The quick brown fox")
        assert turn.sentiment == 0.0
