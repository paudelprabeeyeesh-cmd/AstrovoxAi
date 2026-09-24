import pytest
from active_learning.annotator_interface import AnnotatorInterface, AnnotationStatus


class TestAnnotatorInterface:
    def test_initialization(self):
        annotator = AnnotatorInterface("annotator_1")
        assert annotator.annotator_id == "annotator_1"
        assert annotator.total_annotated() == 0

    def test_submit_annotation(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(sample_id=0, label="positive", confidence=0.9)
        annotation = annotator.get_annotation(0)
        assert annotation is not None
        assert annotation["label"] == "positive"
        assert annotation["confidence"] == pytest.approx(0.9)
        assert annotation["status"] == AnnotationStatus.COMPLETED.value
        assert annotation["annotator_id"] == "a1"

    def test_skip_sample(self):
        annotator = AnnotatorInterface("a1")
        annotator.skip(sample_id=1)
        annotation = annotator.get_annotation(1)
        assert annotation["label"] is None
        assert annotation["confidence"] == 0.0
        assert annotation["status"] == AnnotationStatus.SKIPPED.value

    def test_completed_count(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos", 0.8)
        annotator.submit_annotation(1, "neg", 0.6)
        annotator.skip(2)
        assert annotator.completed_count() == 2
        assert annotator.skipped_count() == 1
        assert annotator.pending_count() == 0
        assert annotator.total_annotated() == 3

    def test_default_confidence(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos")
        annotation = annotator.get_annotation(0)
        assert annotation["confidence"] == pytest.approx(1.0)

    def test_get_all_annotations(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos")
        annotator.submit_annotation(1, "neg")
        all_ann = annotator.get_all_annotations()
        assert len(all_ann) == 2
        assert 0 in all_ann
        assert 1 in all_ann

    def test_average_confidence_empty(self):
        annotator = AnnotatorInterface("a1")
        assert annotator.average_confidence() == pytest.approx(0.0)

    def test_average_confidence(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos", confidence=0.8)
        annotator.submit_annotation(1, "neg", confidence=0.6)
        annotator.skip(2)
        assert annotator.average_confidence() == pytest.approx(0.7)

    def test_annotation_overwrite(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos", confidence=0.5)
        annotator.submit_annotation(0, "neg", confidence=0.9)
        annotation = annotator.get_annotation(0)
        assert annotation["label"] == "neg"
        assert annotation["confidence"] == pytest.approx(0.9)

    def test_timestamp_present(self):
        annotator = AnnotatorInterface("a1")
        annotator.submit_annotation(0, "pos")
        annotation = annotator.get_annotation(0)
        assert "timestamp" in annotation
        assert len(annotation["timestamp"]) > 0
