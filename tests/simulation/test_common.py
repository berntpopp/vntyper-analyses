# tests/simulation/test_common.py
"""Tests for shared simulation utilities."""

import pytest
from pathlib import Path


# Determine paths
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "simulation"

# Add scripts dir to path for imports
import sys
sys.path.insert(0, str(SCRIPTS_DIR))


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_dict(self):
        from _common import load_config
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_load_config_has_required_keys(self):
        from _common import load_config
        cfg = load_config()
        assert "experiment1" in cfg
        assert "experiment2" in cfg
        assert "experiment3" in cfg
        assert "vntr" in cfg
        assert "read_simulation" in cfg
        assert "paths" in cfg

    def test_experiment1_seeds(self):
        from _common import load_config
        cfg = load_config()
        assert cfg["experiment1"]["seed_start"] == 3000
        assert cfg["experiment1"]["seed_end"] == 3099

    def test_experiment2_mutations_count(self):
        from _common import load_config
        cfg = load_config()
        assert len(cfg["experiment2"]["mutations"]) == 10


class TestGetExperimentPairs:
    """Tests for get_experiment_pairs function."""

    def test_exp1_full_returns_100_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=1, test_mode=False)
        assert len(pairs) == 100
        assert pairs[0] == {"seed": 3000, "mutation": "dupC"}
        assert pairs[99] == {"seed": 3099, "mutation": "dupC"}

    def test_exp1_test_returns_5_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=1, test_mode=True)
        assert len(pairs) == 5

    def test_exp2_full_returns_100_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=2, test_mode=False)
        assert len(pairs) == 100
        # First 10 pairs are insG
        assert all(p["mutation"] == "insG" for p in pairs[:10])

    def test_exp2_test_returns_5_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=2, test_mode=True)
        assert len(pairs) == 5
        mutations = [p["mutation"] for p in pairs]
        assert mutations == ["insG", "dupA", "delinsAT", "insCCCC", "insC_pos23"]


class TestGetResultsBase:
    """Tests for get_results_base function."""

    def test_production_path(self):
        from _common import load_config, get_results_base
        cfg = load_config()
        base = get_results_base(cfg, test_mode=False)
        assert base == Path("results/simulation")

    def test_test_path(self):
        from _common import load_config, get_results_base
        cfg = load_config()
        base = get_results_base(cfg, test_mode=True)
        assert base == Path("results/simulation_test")


class TestBuildParser:
    """Tests for build_common_parser function."""

    def test_parser_has_test_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--test"])
        assert args.test is True

    def test_parser_has_workers_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--workers", "8"])
        assert args.workers == 8

    def test_parser_has_experiment_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--experiment", "1"])
        assert args.experiment == "1"

    def test_parser_defaults(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args([])
        assert args.test is False
        assert args.experiment == "all"
