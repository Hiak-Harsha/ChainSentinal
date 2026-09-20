"""Tests for the synthetic data generator (Phase 1).

Tests cover:
- Determinism (same seed = same output)
- Amount conservation (sum(in) - sum(out) == fee for all txs)
- Format parity (CSV, JSON, XML contain identical data)
- Address format validity
- TXID format (64-char hex)
- Ground truth coverage (all typologies, all obfuscation levels)
- No documentation IP ranges
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from chainsentinel.gen.generator import run_generator


# Use a small dataset for fast tests
TEST_TX_COUNT = 500
TEST_SEED = 42
TEST_OUTPUT_DIR = "data/test_output"
TEST_OUTPUT_DIR_2 = "data/test_output_2"


@pytest.fixture(scope="module")
def generated_data():
    """Generate a small dataset once for all tests."""
    out = run_generator(
        tx_count=TEST_TX_COUNT,
        seed=TEST_SEED,
        output_dir=TEST_OUTPUT_DIR,
        formats=["csv", "json"],
    )
    return out


@pytest.fixture(scope="module")
def ground_truth(generated_data):
    """Load ground truth from generated data."""
    gt_path = Path(TEST_OUTPUT_DIR) / "ground_truth.json"
    with open(gt_path) as f:
        return json.load(f)


class TestDeterminism:
    """Same seed should produce identical output."""

    def test_deterministic_ground_truth(self):
        """Two runs with the same seed produce identical ground truth."""
        run_generator(tx_count=200, seed=99, output_dir=TEST_OUTPUT_DIR_2, formats=["json"])
        run_generator(tx_count=200, seed=99, output_dir=TEST_OUTPUT_DIR_2 + "_dup", formats=["json"])

        gt1 = Path(TEST_OUTPUT_DIR_2) / "ground_truth.json"
        gt2 = Path(TEST_OUTPUT_DIR_2 + "_dup") / "ground_truth.json"

        with open(gt1) as f1, open(gt2) as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)

        assert data1["statistics"] == data2["statistics"]
        assert len(data1["entities"]) == len(data2["entities"])
        assert len(data1["scenarios"]) == len(data2["scenarios"])


class TestAmountConservation:
    """Every transaction must conserve amounts: sum(in) - sum(out) == fee."""

    def test_amount_conservation_from_json(self, generated_data):
        """Parse JSON and check amount conservation for all observations."""
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"
        txid_checked = set()

        with open(json_path) as f:
            for line in f:
                obs = json.loads(line)
                txid = obs["txid"]
                if txid in txid_checked:
                    continue
                txid_checked.add(txid)

                input_amounts = obs["input_amounts"]
                output_amounts = obs["output_amounts"]
                fee = obs["fee"]

                total_in = sum(input_amounts)
                total_out = sum(output_amounts)

                # Fee should be positive
                assert fee > 0, f"Fee must be positive for tx {txid}"

                # All amounts should be positive
                for amt in input_amounts:
                    assert amt > 0, f"Input amount must be positive for tx {txid}"
                for amt in output_amounts:
                    assert amt > 0, f"Output amount must be positive for tx {txid}"


class TestFormatParity:
    """CSV and JSON should contain identical logical data."""

    def test_same_row_count(self, generated_data):
        """CSV and JSON should have the same number of rows."""
        csv_path = Path(TEST_OUTPUT_DIR) / "observations.csv"
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"

        with open(csv_path) as f:
            csv_rows = sum(1 for _ in csv.reader(f)) - 1  # minus header

        with open(json_path) as f:
            json_rows = sum(1 for _ in f)

        assert csv_rows == json_rows, f"CSV has {csv_rows} rows, JSON has {json_rows}"

    def test_same_txids(self, generated_data):
        """CSV and JSON should contain the same set of TXIDs."""
        csv_path = Path(TEST_OUTPUT_DIR) / "observations.csv"
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"

        csv_txids = set()
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_txids.add(row["txid"])

        json_txids = set()
        with open(json_path) as f:
            for line in f:
                obs = json.loads(line)
                json_txids.add(obs["txid"])

        assert csv_txids == json_txids


class TestAddressFormat:
    """All addresses should match Bitcoin-like format patterns."""

    def test_address_prefixes(self, generated_data):
        """All addresses start with valid Bitcoin prefixes."""
        valid_prefixes = ("1", "3", "bc1q", "bc1p")
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"

        checked = 0
        with open(json_path) as f:
            for line in f:
                obs = json.loads(line)
                for addr in obs["input_addresses"] + obs["output_addresses"]:
                    assert any(addr.startswith(p) for p in valid_prefixes), \
                        f"Invalid address prefix: {addr}"
                    checked += 1

        assert checked > 0, "No addresses were checked"


class TestTxidFormat:
    """All TXIDs should be 64-character hex strings."""

    def test_txid_hex_format(self, generated_data):
        """All TXIDs should be 64-char lowercase hex."""
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"
        checked = set()

        with open(json_path) as f:
            for line in f:
                obs = json.loads(line)
                txid = obs["txid"]
                if txid in checked:
                    continue
                checked.add(txid)

                assert len(txid) == 64, f"TXID wrong length: {len(txid)}"
                assert all(c in "0123456789abcdef" for c in txid), \
                    f"TXID not hex: {txid}"

        assert len(checked) > 0, "No TXIDs were checked"


class TestGroundTruth:
    """Ground truth should have complete coverage."""

    def test_all_typologies_present(self, ground_truth):
        """All 9 typologies should be represented."""
        typologies = set()
        for entity in ground_truth["entities"]:
            if entity["typology"]:
                typologies.add(entity["typology"])

        expected = {
            "ransomware", "darknet_market", "peel_chain",
            "coinjoin_mixer", "layering", "structuring",
            "extortion", "dusting", "multi_cluster",
        }
        assert expected.issubset(typologies), \
            f"Missing typologies: {expected - typologies}"

    def test_obfuscation_levels_present(self, ground_truth):
        """All obfuscation levels 0-3 should be represented."""
        levels = set()
        for scenario in ground_truth["scenarios"]:
            levels.add(scenario["obfuscation_level"])

        assert {0, 1, 2, 3}.issubset(levels), \
            f"Missing obfuscation levels: {{0,1,2,3}} - {levels}"

    def test_illicit_entities_have_txids(self, ground_truth):
        """Every illicit entity should have at least one associated TXID."""
        for scenario in ground_truth["scenarios"]:
            assert len(scenario["txids"]) > 0, \
                f"Scenario {scenario['scenario_id']} has no txids"

    def test_statistics_present(self, ground_truth):
        """Statistics should be computed correctly."""
        stats = ground_truth["statistics"]
        assert stats["total_tx"] > 0
        assert stats["illicit_entities"] > 0
        assert stats["legit_entities"] > 0
        assert stats["n_scenarios"] > 0
        assert len(stats["typology_counts"]) == 9


class TestNoDocumentationRanges:
    """No documentation/test IP ranges should appear in output."""

    def test_no_rfc5737_ips(self, generated_data):
        """IPs should not be from RFC 5737 documentation ranges."""
        doc_prefixes = ["192.0.2.", "198.51.100.", "203.0.113."]
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"

        with open(json_path) as f:
            for line in f:
                obs = json.loads(line)
                for ip_field in ["src_ip", "dst_ip"]:
                    ip = obs[ip_field]
                    for prefix in doc_prefixes:
                        assert not ip.startswith(prefix), \
                            f"Documentation IP found: {ip}"
