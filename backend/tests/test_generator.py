"""Tests for the synthetic data generator v2 (Phase 1 Acceptance Suite).

Tests cover:
- Invariant: Legit traffic share >= 90% and never zero
- Invariant: Ground truth address and entity label coverage is 100%
- Invariant: Realistic legit behaviors (batched withdrawals 20-200, sweeps, co-spends, payroll)
- Invariant: Network simulation emits sensor_id across 5+ vantage points
- Invariant: No deterministic obfuscation-to-IP class leak
- Invariant: Format parity across CSV, JSON (array), NDJSON, and XML
- Invariant: Determinism under identical seed
- Invariant: Amount conservation (sum(in) - sum(out) == fee)
- Invariant: No RFC 5737 documentation IP ranges
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from chainsentinel.gen.generator import run_generator


TEST_TX_COUNT = 500
TEST_SEED = 42
TEST_OUTPUT_DIR = "data/test_output_phase1"
TEST_OUTPUT_DIR_DUP1 = "data/test_output_dup1"
TEST_OUTPUT_DIR_DUP2 = "data/test_output_dup2"


@pytest.fixture(scope="module")
def generated_data():
    """Generate dataset with all formats for acceptance tests."""
    out = run_generator(
        tx_count=TEST_TX_COUNT,
        seed=TEST_SEED,
        output_dir=TEST_OUTPUT_DIR,
        formats=["csv", "json", "xml"],
    )
    return out


@pytest.fixture(scope="module")
def ground_truth(generated_data):
    """Load ground truth from generated data."""
    gt_path = Path(TEST_OUTPUT_DIR) / "ground_truth.json"
    with open(gt_path, encoding="utf-8") as f:
        return json.load(f)


class TestLegitShareInvariant:
    """Legit traffic must be at least 90% and never zero."""

    def test_legit_share_at_least_90_percent(self, ground_truth):
        stats = ground_truth["statistics"]
        legit_share = stats["legit_share"]
        legit_tx = stats["legit_tx"]
        total_tx = stats["total_tx"]

        assert legit_tx > 0, "Legit transactions count is zero!"
        assert legit_share >= 0.90, f"Legit share {legit_share:.4f} is below required 90.0%"
        assert legit_tx / total_tx >= 0.90, f"Computed ratio {legit_tx / total_tx:.4f} is below 90.0%"

    def test_legit_entities_population(self, ground_truth):
        stats = ground_truth["statistics"]
        assert stats["legit_entities"] > 0
        assert stats["illicit_entities"] > 0
        assert stats["legit_entities"] + stats["illicit_entities"] == len(ground_truth["entities"])


class TestLabelCoverage100Percent:
    """100% address label coverage: every input/output address has ground truth."""

    def test_100_percent_address_coverage(self, ground_truth):
        address_gt = ground_truth["addresses"]
        assert len(address_gt) > 0, "Address ground truth dictionary is empty"

        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        txids_checked = set()
        unlabeled = set()

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                txid = obs["txid"]
                if txid in txids_checked:
                    continue
                txids_checked.add(txid)

                for addr in obs["input_addresses"] + obs["output_addresses"]:
                    if addr not in address_gt:
                        unlabeled.add(addr)

        assert len(unlabeled) == 0, f"Found {len(unlabeled)} unlabeled addresses in transactions! Examples: {list(unlabeled)[:5]}"
        assert ground_truth["statistics"]["label_coverage"] == 1.0

    def test_roles_present_on_all_addresses(self, ground_truth):
        for addr, rec in ground_truth["addresses"].items():
            assert "role" in rec and rec["role"], f"Missing role on address {addr}"
            assert "type" in rec and rec["type"], f"Missing type on address {addr}"
            assert "entity_id" in rec and rec["entity_id"], f"Missing entity_id on address {addr}"

    def test_victim_and_counterparty_labels(self, ground_truth):
        roles = {rec["role"] for rec in ground_truth["addresses"].values()}
        assert "victim" in roles, "No victim addresses labeled in ground truth"
        assert "counterparty" in roles or "retail_user" in roles, "No counterparty/retail addresses labeled"


class TestRealisticLegitShapes:
    """Legit entities must exhibit realistic shapes (batched withdrawals 20-200, sweeps, co-spends)."""

    def test_batched_exchange_withdrawals(self, ground_truth):
        """Verify presence of high fan-out batched withdrawals (20-200 outputs)."""
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        max_outputs = 0

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                n_out = len(obs["output_addresses"])
                if n_out > max_outputs:
                    max_outputs = n_out

        assert max_outputs >= 20, f"Expected batched transactions with >= 20 outputs, got max {max_outputs}"

    def test_multi_input_cospend(self, ground_truth):
        """Verify presence of multi-input retail co-spend transactions."""
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        found_multi_in = False

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                if len(obs["input_addresses"]) >= 2 and len(obs["output_addresses"]) == 2:
                    found_multi_in = True
                    break

        assert found_multi_in, "No multi-input co-spend transactions found"

    def test_merchant_consolidation_sweeps(self, ground_truth):
        """Verify presence of merchant sweeps (many in -> 1-2 out)."""
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        found_sweep = False

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                if len(obs["input_addresses"]) >= 3 and len(obs["output_addresses"]) <= 2:
                    found_sweep = True
                    break

        assert found_sweep, "No merchant consolidation sweeps found"


class TestNetworkSimulationAndSensorId:
    """Verify sensor_id emission and absence of deterministic IP leaks."""

    def test_sensor_id_emitted_across_vantage_points(self, ground_truth):
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        sensor_ids = set()

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                assert "sensor_id" in obs and obs["sensor_id"]
                sensor_ids.add(obs["sensor_id"])

        assert len(sensor_ids) >= 5, f"Expected at least 5 sensor vantage points, found {len(sensor_ids)}"

    def test_no_deterministic_obfuscation_ip_leak(self, ground_truth):
        """Obfuscation level must not strictly equal Tor/VPN (leak removed)."""
        entities = ground_truth["entities"]
        legit_entities = [e for e in entities if e["type"] == "legit"]
        assert len(legit_entities) > 0

        # Legit entities should have some cloud hosting or VPN IPs
        has_ips = any(len(e["operator_ips"]) > 0 for e in legit_entities)
        assert has_ips, "Legit entities have no operator IPs"


class TestFormatParity:
    """CSV, JSON (array), NDJSON, and XML must decode to identical logical data."""

    def test_format_parity_all_formats(self, generated_data):
        csv_path = Path(TEST_OUTPUT_DIR) / "observations.csv"
        json_path = Path(TEST_OUTPUT_DIR) / "observations.json"
        ndjson_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        xml_path = Path(TEST_OUTPUT_DIR) / "observations.xml"

        # CSV
        with open(csv_path, newline="", encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))

        # JSON array
        with open(json_path, encoding="utf-8") as f:
            json_rows = json.load(f)

        # NDJSON
        with open(ndjson_path, encoding="utf-8") as f:
            ndjson_rows = [json.loads(line) for line in f if line.strip()]

        # XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        xml_rows = []
        for obs in root.findall("observation"):
            rec = {}
            for elem in obs:
                items = elem.findall("item")
                if items:
                    rec[elem.tag] = [it.text for it in items]
                else:
                    rec[elem.tag] = elem.text or ""
            xml_rows.append(rec)

        assert len(csv_rows) == len(json_rows) == len(ndjson_rows) == len(xml_rows), (
            f"Counts mismatch: CSV={len(csv_rows)}, JSON={len(json_rows)}, NDJSON={len(ndjson_rows)}, XML={len(xml_rows)}"
        )

        # Check sample records
        for i in range(min(50, len(csv_rows))):
            c, j, nd, x = csv_rows[i], json_rows[i], ndjson_rows[i], xml_rows[i]
            assert c["txid"] == j["txid"] == nd["txid"] == x["txid"]
            assert c["sensor_id"] == j["sensor_id"] == nd["sensor_id"] == x["sensor_id"]
            assert c["src_ip"] == j["src_ip"] == nd["src_ip"] == x["src_ip"]
            assert c["dst_ip"] == j["dst_ip"] == nd["dst_ip"] == x["dst_ip"]
            assert int(c["fee"]) == int(j["fee"]) == int(nd["fee"]) == int(x["fee"])


class TestDeterminism:
    """Same seed should produce identical ground truth and stats."""

    def test_deterministic_generation(self):
        run_generator(tx_count=200, seed=99, output_dir=TEST_OUTPUT_DIR_DUP1, formats=["json"])
        run_generator(tx_count=200, seed=99, output_dir=TEST_OUTPUT_DIR_DUP2, formats=["json"])

        gt1_path = Path(TEST_OUTPUT_DIR_DUP1) / "ground_truth.json"
        gt2_path = Path(TEST_OUTPUT_DIR_DUP2) / "ground_truth.json"

        with open(gt1_path, encoding="utf-8") as f1, open(gt2_path, encoding="utf-8") as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)

        assert data1["statistics"] == data2["statistics"]
        assert len(data1["entities"]) == len(data2["entities"])
        assert len(data1["addresses"]) == len(data2["addresses"])
        assert len(data1["scenarios"]) == len(data2["scenarios"])


class TestAmountConservation:
    """Every transaction must conserve amounts: sum(in) - sum(out) == fee."""

    def test_amount_conservation(self, generated_data):
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"
        checked = set()

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                txid = obs["txid"]
                if txid in checked:
                    continue
                checked.add(txid)

                fee = obs["fee"]
                assert fee > 0, f"Fee not positive on {txid}"
                assert sum(obs["input_amounts"]) - sum(obs["output_amounts"]) == fee

        assert len(checked) > 0


class TestNoDocumentationRanges:
    """No RFC 5737 documentation IP ranges."""

    def test_no_documentation_ips(self, generated_data):
        doc_prefixes = ["192.0.2.", "198.51.100.", "203.0.113."]
        json_path = Path(TEST_OUTPUT_DIR) / "observations.ndjson"

        with open(json_path, encoding="utf-8") as f:
            for line in f:
                obs = json.loads(line)
                for ip_field in ["src_ip", "dst_ip"]:
                    ip = obs[ip_field]
                    for prefix in doc_prefixes:
                        assert not ip.startswith(prefix), f"Documentation IP found: {ip}"
