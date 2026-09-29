"""Formal test suite executing validation against the complete 9-fixture test suite (A through I)."""

import json
from pathlib import Path
import pytest

from chainsentinel.ingest.parsers.json_parser import JsonStreamingParser
from chainsentinel.ingest.validator import RecordValidator, QuarantineReason

ObservationValidator = RecordValidator


FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures"


@pytest.fixture
def manifest():
    manifest_path = FIXTURES_DIR / "fixtures_manifest.json"
    assert manifest_path.exists(), "fixtures_manifest.json must exist"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_all_records(file_path):
    parser = JsonStreamingParser(file_path)
    records = []
    for chunk in parser.iter_chunks():
        records.extend(chunk)
    return records


def test_fixture_a_clean(manifest):
    """Fixture A: Clean dataset should yield 100% valid records and 0 quarantined."""
    fpath = FIXTURES_DIR / "clean_observations.jsonl"
    validator = ObservationValidator()

    records = _load_all_records(fpath)
    assert len(records) == manifest["fixtures"]["A_clean"]["input_rows"]

    valid_count = 0
    quarantine_count = 0

    for obs in records:
        res = validator.validate(obs)
        if res.is_valid:
            valid_count += 1
        else:
            quarantine_count += 1

    assert valid_count == manifest["fixtures"]["A_clean"]["expected_valid"]
    assert quarantine_count == manifest["fixtures"]["A_clean"]["expected_quarantined"]


def test_fixture_b_malformed(manifest):
    """Fixture B: Malformed dataset should trigger specific quarantine reasons."""
    fpath = FIXTURES_DIR / "malformed_observations.jsonl"
    validator = ObservationValidator()

    records = _load_all_records(fpath)
    assert len(records) == manifest["fixtures"]["B_malformed"]["input_rows"]

    quarantined_reasons = []
    for obs in records:
        res = validator.validate(obs)
        assert not res.is_valid, f"Expected invalid observation: {obs}"
        quarantined_reasons.append(res.reason_code)

    # All 5 rows must be quarantined
    assert len(quarantined_reasons) == 5
    assert QuarantineReason.INVALID_IP in quarantined_reasons
    assert QuarantineReason.INVALID_TXID in quarantined_reasons
    assert QuarantineReason.EMPTY_INPUTS_OR_OUTPUTS in quarantined_reasons


def test_fixture_c_duplicates(manifest):
    """Fixture C: Duplicate dataset should contain identical observations."""
    fpath = FIXTURES_DIR / "duplicate_observations.jsonl"
    records = _load_all_records(fpath)
    assert len(records) == manifest["fixtures"]["C_duplicate"]["input_rows"]

    seen_hashes = set()
    dup_count = 0
    for obs in records:
        h = f"{obs.get('txid')}:{obs.get('timestamp')}:{obs.get('src_ip')}"
        if h in seen_hashes:
            dup_count += 1
        else:
            seen_hashes.add(h)

    assert dup_count == manifest["fixtures"]["C_duplicate"]["expected_duplicate_count"]
    assert len(seen_hashes) == manifest["fixtures"]["C_duplicate"]["unique_records"]


def test_fixture_d_quarantine_reasons(manifest):
    """Fixture D: Quarantine suite should trigger individual quarantine categories."""
    fpath = FIXTURES_DIR / "quarantine_observations.jsonl"
    validator = ObservationValidator()

    records = _load_all_records(fpath)
    assert len(records) == manifest["fixtures"]["D_quarantine"]["input_rows"]

    observed_reasons = set()
    for obs in records:
        res = validator.validate(obs)
        assert not res.is_valid
        observed_reasons.add(res.reason_code)

    assert QuarantineReason.INVALID_TXID in observed_reasons
    assert QuarantineReason.INVALID_IP in observed_reasons
    assert QuarantineReason.TIMESTAMP_ANOMALY in observed_reasons


def test_fixture_e_mixed_dataset(manifest):
    """Fixture E: Mixed dataset must produce exactly 18 valid and 2 quarantined records."""
    fpath = FIXTURES_DIR / "mixed_observations.jsonl"
    validator = ObservationValidator()

    records = _load_all_records(fpath)
    assert len(records) == manifest["fixtures"]["E_mixed"]["input_rows"]

    valid_count = 0
    quarantine_count = 0
    quarantine_reasons = []

    for obs in records:
        res = validator.validate(obs)
        if res.is_valid:
            valid_count += 1
        else:
            quarantine_count += 1
            quarantine_reasons.append(res.reason_code)

    assert valid_count == manifest["fixtures"]["E_mixed"]["expected_valid"]
    assert quarantine_count == manifest["fixtures"]["E_mixed"]["expected_quarantined"]
    assert QuarantineReason.INVALID_TXID in quarantine_reasons
    assert (
        QuarantineReason.CHECKSUM_MISMATCH in quarantine_reasons
        or QuarantineReason.AMOUNT_MISMATCH in quarantine_reasons
    )


def test_fixture_f_graph_structure(manifest):
    """Fixture F: Graph fixture structure contains valid nodes, edges and entity classifications."""
    fpath = FIXTURES_DIR / "small_graph_fixture.json"
    with open(fpath, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    assert len(nodes) == manifest["fixtures"]["F_graph"]["expected_node_count"]
    assert len(edges) == manifest["fixtures"]["F_graph"]["expected_edge_count"]

    node_types = {n["type"] for n in nodes}
    for t in manifest["fixtures"]["F_graph"]["entity_types"]:
        assert t in node_types


def test_fixture_g_trace_path(manifest):
    """Fixture G: Trace path fixture verifies multi-hop decay and stop condition."""
    fpath = FIXTURES_DIR / "trace_path_fixture.json"
    with open(fpath, "r", encoding="utf-8") as f:
        trace = json.load(f)

    assert trace["origin"] == manifest["fixtures"]["G_trace"]["origin"]
    assert len(trace["hops"]) == manifest["fixtures"]["G_trace"]["expected_hops"]
    terminal_hop = trace["hops"][-1]
    assert terminal_hop["stop_reason"] == manifest["fixtures"]["G_trace"]["terminal_stop_reason"]
    assert trace["hops"][0]["decay_factor"] > trace["hops"][-1]["decay_factor"]


def test_fixture_h_alerts_and_shap(manifest):
    """Fixture H: Alerts fixture includes conformal grades and explainability features."""
    fpath = FIXTURES_DIR / "alert_fixture.json"
    with open(fpath, "r", encoding="utf-8") as f:
        alerts = json.load(f)

    assert len(alerts) == manifest["fixtures"]["H_alerts"]["expected_alerts"]
    grades = [a["confidence"]["grade"] for a in alerts]
    for g in manifest["fixtures"]["H_alerts"]["expected_grades"]:
        assert g in grades

    for a in alerts:
        assert "explanation" in a
        assert len(a["explanation"]) > 0
        for exp in a["explanation"]:
            assert "feature" in exp
            assert "contribution" in exp


def test_fixture_i_case_dossier(manifest):
    """Fixture I: Case dossier includes sealed audit trail and forensic evidence hash."""
    fpath = FIXTURES_DIR / "case_fixture.json"
    with open(fpath, "r", encoding="utf-8") as f:
        case = json.load(f)

    assert case["case_id"] == manifest["fixtures"]["I_case"]["expected_case_id"]
    assert case["status"] == manifest["fixtures"]["I_case"]["status"]
    assert len(case["timeline"]) == manifest["fixtures"]["I_case"]["expected_timeline_events"]
    assert "defensible_audit_hash" in case["evidence"]
