from social_intelligence.persuasion_detector import PersuasionDetector, PersuasionFeatures


class TestPersuasionFeatures:
    def test_empty_text_sentence_count_zero(self):
        pf = PersuasionFeatures(text="")
        assert pf.sentence_count == 0
        assert pf.word_count == 0

    def test_persuasion_score_zero_without_sentences(self):
        pf = PersuasionFeatures(text="")
        assert pf.persuasion_score() == 0.0

    def test_exclamation_count(self):
        pf = PersuasionFeatures(text="Buy now!!")
        assert pf.exclamation_count >= 1


class TestPersuasionDetector:
    def setup_method(self):
        self.detector = PersuasionDetector()

    def test_analyze_returns_features(self):
        pf = self.detector.analyze("This is a test message.")
        assert isinstance(pf, PersuasionFeatures)

    def test_authority_signals(self):
        pf = self.detector.analyze("According to the expert doctor, this study shows...")
        assert pf.authority_signals >= 3

    def test_social_proof_signals(self):
        pf = self.detector.analyze("Everyone loves this bestselling product, millions bought it.")
        assert pf.social_proof_signals >= 3

    def test_scarcity_signals(self):
        pf = self.detector.analyze("Limited exclusive offer, only a few left, hurry!")
        assert pf.scarcity_signals >= 3

    def test_reciprocity_signals(self):
        pf = self.detector.analyze("Get a free bonus gift included with this offer.")
        assert pf.reciprocity_signals >= 3

    def test_consistency_signals(self):
        pf = self.detector.analyze("I promise to always guarantee consistency.")
        assert pf.consistency_signals >= 3

    def test_liking_signals(self):
        pf = self.detector.analyze("I love and admire this wonderful beautiful friend.")
        assert pf.liking_signals >= 3

    def test_persuasion_score_bounded(self):
        pf = self.detector.analyze("Expert says everyone wants this limited free gift.")
        score = pf.persuasion_score()
        assert 0.0 <= score <= 1.0

    def test_batch_analyze_length(self):
        results = self.detector.batch_analyze(["a", "b", "c"])
        assert len(results) == 3

    def test_batch_analyze_types(self):
        results = self.detector.batch_analyze(["text1", "text2"])
        assert all(isinstance(r, PersuasionFeatures) for r in results)
