import pytest
from complex_reasoning.modal_reasoning import KripkeModel, ModalFormula, ModalEngine


class TestKripkeModel:
    def test_add_world(self):
        model = KripkeModel(worlds=["w0"])
        model.add_world("w1")
        assert "w1" in model.worlds

    def test_add_atomic(self):
        model = KripkeModel()
        model.add_atomic("w0", "Rain", True)
        assert model.truth("Rain", "w0") is True

    def test_possible_worlds(self):
        model = KripkeModel()
        assert "w1" in model.possible_worlds("w0")

    def test_structure_mapping(self):
        model = KripkeModel()
        model.add_atomic("w0", "P", True)
        model.add_atomic("w1", "P", True)
        assert model.structure_mapping("w0", "w1") == pytest.approx(1.0)

    def test_counter(self):
        model = KripkeModel()
        model.add_atomic("w0", "P", True)
        model.add_atomic("w0", "Q", False)
        c = model.counter("w0")
        assert c["true"] == 1
        assert c["false"] == 1


class TestModalFormula:
    def test_box_truth(self):
        model = KripkeModel()
        model.add_atomic("w0", "P", True)
        model.add_atomic("w1", "P", True)
        f = ModalFormula("box", "P")
        assert f.truth_in_model(model, "w0") is True

    def test_diamond_truth(self):
        model = KripkeModel()
        model.add_atomic("w0", "P", False)
        model.add_atomic("w1", "P", True)
        f = ModalFormula("diamond", "P")
        assert f.truth_in_model(model, "w0") is True

    def test_necessary(self):
        model = KripkeModel()
        model.add_atomic("w0", "P", True)
        model.add_atomic("w1", "P", True)
        f = ModalFormula("box", "P")
        assert f.necessary(model, "w0") is True

    def test_possible(self):
        model = KripkeModel()
        model.add_atomic("w1", "P", True)
        f = ModalFormula("diamond", "P")
        assert f.possible(model, "w0") is True


class TestModalEngine:
    def test_add_world_and_knowledge(self):
        engine = ModalEngine()
        engine.add_world("w0")
        engine.add_knowledge("w0", "P", True)
        assert engine.effective_truth("P", "w0") is True

    def test_is_necessary(self):
        engine = ModalEngine()
        engine.add_world("w0")
        engine.add_world("w1")
        engine.add_knowledge("w0", "P", True)
        engine.add_knowledge("w1", "P", True)
        assert engine.is_necessary("P", "w0") is True

    def test_is_possible(self):
        engine = ModalEngine()
        engine.add_world("w0")
        engine.add_world("w1")
        engine.add_knowledge("w1", "P", True)
        assert engine.is_possible("P", "w0") is True
