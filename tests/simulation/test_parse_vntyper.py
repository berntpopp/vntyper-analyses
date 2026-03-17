# tests/simulation/test_parse_vntyper.py
"""Tests for VNtyper result parsing logic."""

import pytest
import json
import tempfile
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestParseKestrelResult:
    """Tests for parsing kestrel_result.tsv."""

    def test_parse_positive_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        # Create a minimal kestrel_result.tsv with a positive call
        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
            "chr1\t155192276\tG\tGC\tFrameshift\tc.27dupC\t"
            "High_Precision\t0.95\t2\tNot flagged\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert result["kestrel_call"] == "c.27dupC"
        assert result["confidence"] == "High_Precision"
        assert result["is_frameshift"] is True

    def test_parse_negative_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        # Empty result (header only)
        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert result["kestrel_call"] == ""
        assert result["confidence"] == "Negative"

    def test_parse_flagged_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
            "chr1\t155192276\tG\tGCCCC\tInsertion\tc.27_28insCCCC\t"
            "Low_Precision\t0.3\t1\tFalse_Positive_4bp_Insertion\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert "False_Positive" in result["flag"]


class TestParsePipelineSummary:
    """Tests for parsing pipeline_summary.json."""

    def test_extract_coverage_from_summary(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        summary = {
            "steps": [
                {
                    "step": "Coverage Calculation",
                    "parsed_result": {
                        "data": [{"mean": 145.2, "median": 142.0, "stdev": 20.1}]
                    }
                }
            ]
        }
        summary_file = tmp_path / "pipeline_summary.json"
        summary_file.write_text(json.dumps(summary))

        cov = mod.extract_coverage(summary_file)
        assert cov["vntr_coverage_mean"] == pytest.approx(145.2)
        assert cov["vntr_coverage_median"] == pytest.approx(142.0)
