
from app.evaluation.end_to_end_pipeline import EndToEndEvaluationPipeline


def test_end_to_end_pipeline():
    pipeline = EndToEndEvaluationPipeline()
    pipeline.build_default(lambda x: "answer")
    result = pipeline.run()
    assert result["stages"] == 4
    assert result["passed"] == 4
    assert result["pass_rate"] == 1.0


def test_end_to_end_pipeline_custom():
    pipeline = EndToEndEvaluationPipeline()
    pipeline.add_stage("custom", lambda: {"ok": True})
    result = pipeline.run()
    assert result["stages"] == 1
    assert result["passed"] == 1
