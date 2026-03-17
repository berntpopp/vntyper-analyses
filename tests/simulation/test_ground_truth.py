# tests/simulation/test_ground_truth.py
"""Tests for ground truth extraction logic."""

import pytest
import json
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestParseSimulationStats:
    """Tests for parsing simulation_stats.json files."""

    def test_parse_normal_sample(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        # MucOneUp 0.28.x JSON structure
        stats = {
            "mutation_info": {"mutation_name": "normal"},
            "provenance": {"seed": 3000},
            "haplotype_statistics": [
                {"repeat_count": 55, "mutation_details": []},
                {"repeat_count": 62, "mutation_details": []},
            ],
        }
        stats_file = tmp_path / "pair_3000.001.normal.simulation_stats.json"
        stats_file.write_text(json.dumps(stats))

        row = mod.parse_simulation_stats(stats_file)
        assert row["seed"] == 3000
        assert row["mutation"] == "normal"
        assert row["hap1_length"] == 55
        assert row["hap2_length"] == 62

    def test_parse_mutated_sample(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        stats = {
            "mutation_info": {"mutation_name": "dupC"},
            "provenance": {"seed": 3000},
            "haplotype_statistics": [
                {"repeat_count": 55, "mutation_details": []},
                {"repeat_count": 62, "mutation_details": [{"position": 3, "repeat": "X"}]},
            ],
        }
        stats_file = tmp_path / "pair_3000.001.mut.simulation_stats.json"
        stats_file.write_text(json.dumps(stats))

        row = mod.parse_simulation_stats(stats_file)
        assert row["mutation"] == "dupC"
        assert row["mutation_repeat_position"] == 3
        assert row["mutation_repeat_type"] == "X"


class TestParseVntrStructure:
    """Tests for parsing vntr_structure.txt files."""

    def test_parse_structure_file(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        content = "haplotype_1\t1-2-3-4-5-A-B-C-6p-7-8-9\nhaplotype_2\t1-2-3-4-5-D-E-F-G-6p-7-8-9\n"
        struct_file = tmp_path / "pair_3000.001.vntr_structure.txt"
        struct_file.write_text(content)

        hap1_chain, hap2_chain = mod.parse_vntr_structure(struct_file)
        assert "A-B-C" in hap1_chain
        assert "D-E-F-G" in hap2_chain
