from alignment.value_alignment import ValueAligner


class TestValueAligner:
    def test_register_value(self):
        aligner = ValueAligner()
        pref = aligner.register_value("fairness", 0.7, "human")
        assert pref.alignment_score == 0.7

    def test_compute_alignment(self):
        aligner = ValueAligner()
        aligner.register_value("fairness")
        alignments = aligner.compute_alignment("fairness test", ["fairness"])
        assert "fairness" in alignments

    def test_update_preference(self):
        aligner = ValueAligner()
        aligner.update_preference("honesty", 0.9, 0.8)
        assert aligner.values["honesty"].alignment_score > 0.0

    def test_detect_conflicts(self):
        aligner = ValueAligner()
        aligner.register_value("freedom", 0.9)
        aligner.register_value("safety", 0.1)
        conflicts = aligner.detect_conflicts("balancing freedom and safety")
        assert isinstance(conflicts, list)

    def test_alignment_report(self):
        aligner = ValueAligner()
        report = aligner.get_alignment_report()
        assert "mean_alignment" in report

    def test_alignment_vector(self):
        aligner = ValueAligner()
        aligner.register_value("fairness")
        vector = aligner.alignment_vector("fairness test")
        assert isinstance(vector, list)

    def test_register_value_source(self):
        aligner = ValueAligner()
        pref = aligner.register_value("fairness", 0.7, "human")
        assert pref.source == "human"

    def test_compute_alignment_no_match(self):
        aligner = ValueAligner()
        aligner.register_value("fairness")
        alignments = aligner.compute_alignment("unrelated", ["fairness"])
        assert alignments == {}

    def test_update_preference_history(self):
        aligner = ValueAligner()
        aligner.update_preference("honesty", 0.9, 0.8)
        aligner.update_preference("honesty", 0.7, 0.9)
        assert len(aligner.values["honesty"].history) == 1

    def test_detect_conflicts_none(self):
        aligner = ValueAligner()
        aligner.register_value("freedom", 0.9)
        aligner.register_value("safety", 0.85)
        conflicts = aligner.detect_conflicts("balancing freedom and safety")
        assert conflicts == []

    def test_alignment_report_conflict_rate(self):
        aligner = ValueAligner()
        aligner.register_value("freedom", 0.9)
        aligner.register_value("safety", 0.1)
        aligner.compute_alignment("text", list(aligner.values.keys()))
        aligner.compute_alignment("text", list(aligner.values.keys()))
        report = aligner.get_alignment_report()
        assert "conflict_rate" in report

    def test_alignment_vector_empty(self):
        aligner = ValueAligner()
        vector = aligner.alignment_vector("anything")
        assert vector == []
