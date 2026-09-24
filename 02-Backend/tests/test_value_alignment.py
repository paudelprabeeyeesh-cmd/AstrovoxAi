from agi_core.value_alignment import ValueAligner


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
