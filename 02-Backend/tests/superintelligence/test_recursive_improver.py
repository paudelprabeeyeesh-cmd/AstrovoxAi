import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.recursive_improver import (
    RecursiveDesignImprover,
    DesignSpec,
    ImprovementIteration,
)


class TestRecursiveDesignImprover:
    def test_improve_returns_design_spec(self):
        improver = RecursiveDesignImprover(max_iterations=10, quality_threshold=0.9)
        design = DesignSpec(name="alpha", description="test", complexity=1.0, quality=0.5)
        result = improver.improve(design)
        assert isinstance(result, DesignSpec)

    def test_quality_improves(self):
        improver = RecursiveDesignImprover(max_iterations=20, quality_threshold=0.95)
        design = DesignSpec(name="beta", description="sample", complexity=1.0, quality=0.3)
        result = improver.improve(design)
        assert result.quality >= design.quality

    def test_complexity_reduces(self):
        improver = RecursiveDesignImprover(max_iterations=20, quality_threshold=0.95)
        design = DesignSpec(name="gamma", description="sample", complexity=1.0, quality=0.3)
        result = improver.improve(design)
        assert result.complexity <= design.complexity

    def test_register_rule(self):
        improver = RecursiveDesignImprover()
        improver.register_rule("custom_rule")
        assert "custom_rule" in improver.refactor_rules

    def test_improvement_report(self):
        improver = RecursiveDesignImprover(max_iterations=10, quality_threshold=0.9)
        design = DesignSpec(name="delta", description="report", complexity=1.0, quality=0.3,
                            components=["a", "b", "c", "d", "e", "f", "g", "h", "i"])
        improver.improve(design)
        report = improver.get_improvement_report()
        assert "applied_count" in report
        assert report["total_iterations"] >= 1

    def test_convergence_measure(self):
        improver = RecursiveDesignImprover(max_iterations=5, quality_threshold=0.9)
        design = DesignSpec(name="epsilon", description="conv", complexity=1.0, quality=0.3)
        improver.improve(design)
        conv = improver.measure_convergence()
        assert isinstance(conv, float)
        assert conv >= 0.0
