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

        # VNtyper 2.x format with ## comment lines
        tsv_content = (
            "## VNtyper Kestrel result\n"
            "## VNtyper Version: 2.0.1\n"
            "Motifs\tPOS\tREF\tALT\tSample\tMotif_sequence\tVariant\tDel\t"
            "Estimated_Depth_AlternateVariant\tEstimated_Depth_Variant_ActiveRegion\t"
            "ref_len\talt_len\tFrame_Score\tis_frameshift\tdirection\tframeshift_amount\t"
            "is_valid_frameshift\tDepth_Score\tConfidence\tdepth_confidence_pass\t"
            "haplo_count\talt_filter_pass\tmotif_filter_pass\tMotif_fasta\tPOS_fasta\tMotif\tFlag\n"
            "K-Q\t67\tG\tGG\t1:726:16689\tACGT\tInsertion\t1\t726\t16689\t"
            "1\t2\t0.333\tTrue\t1\t1\tTrue\t0.043\tHigh_Precision*\tTrue\t"
            "386\tTrue\tTrue\tK-Q\t67\tK\tNot flagged\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert result["kestrel_call"] == "Insertion"
        assert result["confidence"] == "High_Precision*"
        assert result["is_frameshift"] is True

    def test_parse_negative_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        # VNtyper 2.x negative result format
        tsv_content = (
            "## VNtyper Kestrel result\n"
            "## VNtyper Version: 2.0.1\n"
            "Motif\tVariant\tPOS\tREF\tALT\tMotif_sequence\t"
            "Estimated_Depth_AlternateVariant\tEstimated_Depth_Variant_ActiveRegion\t"
            "Depth_Score\tConfidence\n"
            "None\tNone\tNone\tNone\tNone\tNone\tNone\tNone\tNone\tNegative\n"
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
            "## VNtyper Kestrel result\n"
            "Motifs\tPOS\tREF\tALT\tSample\tMotif_sequence\tVariant\tDel\t"
            "Estimated_Depth_AlternateVariant\tEstimated_Depth_Variant_ActiveRegion\t"
            "ref_len\talt_len\tFrame_Score\tis_frameshift\tdirection\tframeshift_amount\t"
            "is_valid_frameshift\tDepth_Score\tConfidence\tdepth_confidence_pass\t"
            "haplo_count\talt_filter_pass\tmotif_filter_pass\tMotif_fasta\tPOS_fasta\tMotif\tFlag\n"
            "K-Q\t67\tG\tGCCCC\t1:3:100\tACGT\tInsertion\t0\t3\t100\t"
            "1\t5\t0.0\tFalse\t1\t0\tFalse\t0.3\tLow_Precision\tTrue\t"
            "1\tTrue\tTrue\tK-Q\t67\tK\tFalse_Positive_4bp_Insertion\n"
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
