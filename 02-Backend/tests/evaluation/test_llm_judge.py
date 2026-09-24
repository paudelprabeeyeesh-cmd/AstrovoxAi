from evaluation.llm_judge import JudgmentScore, LLMJudge, JudgeConfig


def test_judgment_score_to_dict():
    score = JudgmentScore(item_id="item1", score=0.9, raw_output="great", metadata={"model": "gpt"})
    result = score.to_dict()
    assert result["item_id"] == "item1"
    assert result["score"] == 0.9
    assert result["raw_output"] == "great"
    assert result["metadata"] == {"model": "gpt"}


def test_llm_judge_register_human_label():
    judge = LLMJudge()
    judge.register_human_label("item1", 0.8)
    assert judge._human_labels["item1"] == 0.8


def test_llm_judge_register_human_label_clamps():
    judge = LLMJudge()
    judge.register_human_label("item1", -0.5)
    judge.register_human_label("item2", 1.5)
    assert judge._human_labels["item1"] == 0.0
    assert judge._human_labels["item2"] == 1.0


def test_llm_judge_register_prediction():
    judge = LLMJudge()
    judge.register_prediction("item1", 0.7)
    judge.register_prediction("item1", 0.8)
    assert len(judge._model_predictions["item1"]) == 2


def test_llm_judge_register_prediction_clamps():
    judge = LLMJudge()
    judge.register_prediction("item1", -0.1)
    judge.register_prediction("item1", 1.2)
    assert judge._model_predictions["item1"][0] == 0.0
    assert judge._model_predictions["item1"][1] == 1.0


def test_llm_judge_get_calibration_data_empty():
    judge = LLMJudge()
    assert judge.get_calibration_data() == []


def test_llm_judge_get_calibration_data():
    judge = LLMJudge()
    judge.register_human_label("item1", 0.9)
    judge.register_prediction("item1", 0.8)
    data = judge.get_calibration_data()
    assert len(data) == 1
    assert data[0]["human"] == 0.9
    assert data[0]["model"] == 0.8


def test_llm_judge_expected_calibration_error_empty():
    judge = LLMJudge()
    assert judge.expected_calibration_error() == 0.0


def test_llm_judge_calibration_report_empty():
    judge = LLMJudge()
    report = judge.calibration_report()
    assert report["ece"] == 0.0
    assert report["kendall_tau"] == 1.0
    assert report["sample_count"] == 0


def test_llm_judge_kendall_tau_insufficient():
    judge = LLMJudge()
    assert judge.kendall_tau() == 1.0


def test_judge_config_to_dict():
    config = JudgeConfig(model_name="gpt-4", temperature=0.5, max_tokens=128)
    result = config.to_dict()
    assert result["model_name"] == "gpt-4"
    assert result["temperature"] == 0.5
    assert result["max_tokens"] == 128
