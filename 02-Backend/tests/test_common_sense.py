import pytest
import numpy as np
from agi_core.common_sense import CommonSenseEngine


class TestCommonSenseEngine:
    def test_add_fact(self):
        engine = CommonSenseEngine()
        f = engine.add_fact("water", "state_is", "liquid", 0.9)
        assert f.confidence == 0.9

    def test_query(self):
        engine = CommonSenseEngine()
        engine.add_fact("cat", "has", "whiskers", 0.9)
        results = engine.query("cat", "has")
        assert len(results) == 1

    def test_register_default(self):
        engine = CommonSenseEngine()
        da = engine.register_default("weather", "sunny", 0.8)
        assert engine.apply_default("weather") == "sunny"

    def test_detect_exception(self):
        engine = CommonSenseEngine()
        engine.register_default("weather", "sunny", 0.8, exception="rain")
        assert engine.detect_exception("weather", "rain")

    def test_consistency_check(self):
        engine = CommonSenseEngine()
        engine.add_fact("fire", "color_is", "red", 0.8)
        new_fact = engine.add_fact("fire", "color_is", "red", 0.8)
        consistency = engine.consistency_check(new_fact)
        assert consistency == 1.0
