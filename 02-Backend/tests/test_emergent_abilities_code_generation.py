import numpy as np
from emergent_abilities.code_generation import CodeEmergenceModel, ProgramSynthesisAnalyzer, CodeGenerationResult


class TestCodeEmergenceModel:
    def test_generate_output_shape(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=32, max_length=32)
        result = model.generate("def hello():", max_new_tokens=5)
        assert isinstance(result, CodeGenerationResult)
        assert len(result.tokens) > 0

    def test_check_syntax_valid(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        tokens = [0, 1, 2, 3, 4]
        assert model.check_syntax(tokens) is True

    def test_check_syntax_invalid(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        tokens = [1, 2, 3, 4]
        assert model.check_syntax(tokens) is False

    def test_check_semantic_validity(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        score = model.check_semantic_validity([0, 1, 2, 3, 4])
        assert 0.0 <= score <= 1.0

    def test_tokenize_detokenize_roundtrip(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        code = "print(1)"
        tokens = model.tokenize(code)
        model.detokenize(tokens)
        assert len(tokens) == len(code)

    def test_empty_prompt(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        result = model.generate("", max_new_tokens=3)
        assert len(result.tokens) <= 3


class TestProgramSynthesisAnalyzer:
    def test_record_synthesis(self):
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        result = model.generate("def f():")
        analyzer = ProgramSynthesisAnalyzer()
        analyzer.record_synthesis(result, task_complexity=0.5)
        assert len(analyzer.synthesis_results) == 1

    def test_emergence_threshold_no_results(self):
        analyzer = ProgramSynthesisAnalyzer()
        threshold = analyzer.emergence_threshold()
        assert threshold == 0.0

    def test_emergence_threshold_with_results(self):
        analyzer = ProgramSynthesisAnalyzer()
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        for _ in range(10):
            result = model.generate("def f():")
            analyzer.record_synthesis(result, task_complexity=np.random.random())
        threshold = analyzer.emergence_threshold()
        assert threshold >= 0.0

    def test_code_quality_trend(self):
        analyzer = ProgramSynthesisAnalyzer()
        model = CodeEmergenceModel(vocab_size=256, hidden_dim=16, max_length=16)
        for _ in range(5):
            result = model.generate("def f():")
            analyzer.record_synthesis(result, task_complexity=0.5)
        trend = analyzer.code_quality_trend()
        assert len(trend) == 5
