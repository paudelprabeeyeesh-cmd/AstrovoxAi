from evaluation.llm_judge import JudgmentScore, LLMJudge, JudgeConfig


def test_judgment_score_to_dict():
    score = JudgmentScore(item_id="1", score=0.8, raw_output="good", metadata={"source": "test"})
    d = score.to_dict()
    assert d["item_id"] == "1"
    assert d["score"] == 0.8


def test_llm_judge_register():
    judge = LLMJudge()
    judge.register_human_label("1", 1.0)
    judge.register_prediction("1", 0.9)
    data = judge.get_calibration_data()
    assert len(data) == 1
    assert data[0]["human"] == 1.0


def test_expected_calibration_error_no_data():
    judge = LLMJudge()
    assert judge.expected_calibration_error() == 0.0


def test_kendall_tau_insufficient():
    judge = LLMJudge()
    assert judge.kendall_tau() == 1.0


def test_calibration_report():
    judge = LLMJudge()
    report = judge.calibration_report()
    assert "ece" in report
    assert "kendall_tau" in report
    assert report["sample_count"] == 0


def test_judge_config_to_dict():
    config = JudgeConfig(model_name="gpt-4", temperature=0.0, max_tokens=128)
    d = config.to_dict()
    assert d["model_name"] == "gpt-4"
    assert d["temperature"] == 0.0
    assert d["max_tokens"] == 128
