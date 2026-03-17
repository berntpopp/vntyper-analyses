# tests/simulation/test_metrics.py
"""Tests for performance metric calculations."""

import pytest
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestClassifySample:
    """Tests for sample classification (TP/TN/FP/FN)."""

    def test_true_positive(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "Insertion",
            "confidence": "High_Precision*",
            "flag": "Not flagged",
            "is_frameshift": True,
        }
        assert mod.classify_sample(row) == "TP"

    def test_true_negative(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "normal",
            "kestrel_call": "",
            "confidence": "Negative",
            "flag": "",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "TN"

    def test_false_positive(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "normal",
            "kestrel_call": "Insertion",
            "confidence": "High_Precision*",
            "flag": "Not flagged",
            "is_frameshift": True,
        }
        assert mod.classify_sample(row) == "FP"

    def test_false_negative(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "",
            "confidence": "Negative",
            "flag": "",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "FN"

    def test_flagged_positive_is_fn(self):
        """A mutated sample with only a flagged call should be FN."""
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "Insertion",
            "confidence": "Low_Precision",
            "flag": "False_Positive_4bp_Insertion",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "FN"


class TestWilsonCI:
    """Tests for Wilson confidence interval calculation."""

    def test_perfect_sensitivity(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(50, 50)
        assert low > 0.90
        assert high == 1.0

    def test_zero_sensitivity(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(0, 50)
        assert low == 0.0
        assert high < 0.10

    def test_fifty_percent(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(50, 100)
        assert low < 0.5
        assert high > 0.5

    def test_zero_total(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(0, 0)
        assert low == 0.0
        assert high == 0.0


class TestCalculateMetrics:
    """Tests for aggregate metric calculation."""

    def test_basic_metrics(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        classifications = ["TP"] * 45 + ["FN"] * 5 + ["TN"] * 50
        metrics = mod.calculate_metrics(classifications)

        assert metrics["tp"] == 45
        assert metrics["fn"] == 5
        assert metrics["tn"] == 50
        assert metrics["fp"] == 0
        assert metrics["sensitivity"] == pytest.approx(0.90)
        assert metrics["specificity"] == pytest.approx(1.0)
        assert metrics["sensitivity_ci_low"] < 0.90
        assert metrics["sensitivity_ci_high"] > 0.90
