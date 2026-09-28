import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.automation.pipeline import ExperimentConfig, ResearchPipeline


class TestResearchPipeline:
    def test_register_experiment(self):
        pipeline = ResearchPipeline()
        config = ExperimentConfig(name="exp1", model="tiny", dataset="corpus")
        pipeline.register_experiment(config)
        assert pipeline._experiments["exp1"].dataset == "corpus"

    def test_train(self):
        pipeline = ResearchPipeline()
        pipeline.register_experiment(ExperimentConfig(name="exp1", model="tiny", dataset="corpus"))
        result = pipeline.train("exp1")
        assert result["status"] == "completed"
        assert result["experiment"] == "exp1"

    def test_train_missing_experiment(self):
        pipeline = ResearchPipeline()
        try:
            pipeline.train("missing")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")

    def test_evaluate(self):
        pipeline = ResearchPipeline()
        pipeline.register_experiment(ExperimentConfig(name="exp1", model="tiny", dataset="corpus", metrics=["accuracy"]))
        results = pipeline.evaluate("exp1")
        assert len(results) == 1
        assert results[0].metric == "accuracy"

    def test_generate_graphs(self):
        pipeline = ResearchPipeline()
        results = []
        graphs = pipeline.generate_graphs("exp1", results)
        assert graphs == []

    def test_generate_paper(self):
        pipeline = ResearchPipeline()
        paper = pipeline.generate_paper("exp1", {"model": "tiny"}, [], [])
        assert "exp1" in paper
        assert "## Abstract" in paper

    def test_publish_leaderboard(self):
        pipeline = ResearchPipeline()
        results = []
        leaderboard = pipeline.publish_leaderboard("exp1", results)
        assert leaderboard["published"] is True
        assert leaderboard["experiment"] == "exp1"

    def test_hooks(self):
        pipeline = ResearchPipeline()
        events = []
        pipeline.add_hook("before_train", lambda ctx: events.append("before_train"))
        pipeline.add_hook("after_train", lambda ctx: events.append("after_train"))
        pipeline.register_experiment(ExperimentConfig(name="exp1", model="tiny", dataset="corpus"))
        pipeline.train("exp1")
        assert "before_train" in events
        assert "after_train" in events

    def test_full_pipeline(self):
        pipeline = ResearchPipeline()
        pipeline.register_experiment(ExperimentConfig(name="exp1", model="tiny", dataset="corpus", metrics=["accuracy"]))
        output = pipeline.run_full_pipeline("exp1")
        assert output["experiment"] == "exp1"
        assert "paper" in output
        assert "leaderboard" in output
