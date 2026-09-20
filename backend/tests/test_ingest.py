"""Tests for Phase 2: Ingestion & Storage.

Covers:
- Multi-format ingestion parity (CSV, JSON, XML)
- Schema-mapping wizard auto-detection & synonym mapping
- Validation & quarantine subsystem with reason codes
- Idempotent deduplication on (txid, ts, src_ip)
- GeoIP, ASN, and anonymizer enrichment
- Data-Quality Report generation
- Parquet export functionality
- FastAPI ingest endpoints
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.main import app
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.ingest.schema_mapper import SchemaMapper
from chainsentinel.ingest.validator import QuarantineReason, RecordValidator
from chainsentinel.storage.db import DatabaseManager

TEST_CSV = "data/cli_test/observations.csv"
TEST_JSON = "data/cli_test/observations.json"
TEST_XML = "data/cli_test/observations.xml"


class TestMultiFormatIngestion:
    """Ingest CSV, JSON, and XML into separate databases and verify data parity."""

    def test_format_parity_counts(self):
        db_csv = DatabaseManager(":memory:")
        db_json = DatabaseManager(":memory:")
        db_xml = DatabaseManager(":memory:")

        p_csv = IngestPipeline(db=db_csv)
        p_json = IngestPipeline(db=db_json)
        p_xml = IngestPipeline(db=db_xml)

        r_csv = p_csv.run(TEST_CSV)
        r_json = p_json.run(TEST_JSON)
        r_xml = p_xml.run(TEST_XML)

        # All formats should produce identical valid row counts
        assert r_csv.valid_rows == r_json.valid_rows == r_xml.valid_rows
        assert r_csv.valid_rows > 0

        # Unique transactions, addresses, and IPs should match
        assert r_csv.unique_transactions == r_json.unique_transactions == r_xml.unique_transactions
        assert r_csv.unique_addresses == r_json.unique_addresses == r_xml.unique_addresses

        # Database table counts should match across all 3 formats
        c_csv = db_csv.get_counts()
        c_json = db_json.get_counts()
        c_xml = db_xml.get_counts()

        assert c_csv["observations"] == c_json["observations"] == c_xml["observations"]
        assert c_csv["transactions"] == c_json["transactions"] == c_xml["transactions"]
        assert c_csv["tx_inputs"] == c_json["tx_inputs"] == c_xml["tx_inputs"]
        assert c_csv["tx_outputs"] == c_json["tx_outputs"] == c_xml["tx_outputs"]
        assert c_csv["addresses"] == c_json["addresses"] == c_xml["addresses"]


class TestSchemaMapping:
    """Test header synonym auto-detection and custom mapping overrides."""

    def test_synonym_auto_detection(self):
        heterogeneous_headers = [
            "tx_hash",
            "seen_time",
            "origin_ip",
            "sensor_ip",
            "sport",
            "dport",
            "vin_addresses",
            "vin_amounts",
            "vout_addresses",
            "vout_amounts",
            "mining_fee",
            "output_type",
            "vantage_point",
        ]
        mapper = SchemaMapper.auto_detect(heterogeneous_headers)
        m = mapper.mapping

        assert m.get("tx_hash") == "txid"
        assert m.get("seen_time") == "timestamp"
        assert m.get("origin_ip") == "src_ip"
        assert m.get("sensor_ip") == "dst_ip"
        assert m.get("sport") == "src_port"
        assert m.get("dport") == "dst_port"
        assert m.get("vin_addresses") == "input_addresses"
        assert m.get("vin_amounts") == "input_amounts"
        assert m.get("vout_addresses") == "output_addresses"
        assert m.get("vout_amounts") == "output_amounts"
        assert m.get("mining_fee") == "fee"
        assert m.get("output_type") == "script_type"
        assert m.get("vantage_point") == "sensor_id"

    def test_apply_mapping(self):
        mapper = SchemaMapper(mapping={"tx_hash": "txid", "time": "timestamp"})
        raw = {"tx_hash": "abc", "time": 12345, "extra": "foo"}
        mapped = mapper.apply(raw)
        assert mapped["txid"] == "abc"
        assert mapped["timestamp"] == 12345
        assert mapped["extra"] == "foo"

    def test_profile_persistence(self):
        db = DatabaseManager(":memory:")
        profile_name = "test_custom_feed"
        custom_mapping = {"custom_tx": "txid", "custom_time": "timestamp"}

        db.save_schema_profile(profile_name, custom_mapping, created_at=1700000000.0)
        retrieved = db.get_schema_profile(profile_name)

        assert retrieved == custom_mapping
        profiles = db.list_schema_profiles()
        assert any(p["profile_name"] == profile_name for p in profiles)


class TestValidationAndQuarantine:
    """Fuzz with invalid data and verify quarantine routing with exact reason codes."""

    def setup_method(self):
        self.validator = RecordValidator()
        self.valid_record = {
            "txid": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "timestamp": 1700000000.0,
            "src_ip": "1.1.1.1",
            "dst_ip": "8.8.8.8",
            "src_port": 8333,
            "dst_port": 8333,
            "input_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
            "input_amounts": [100000],
            "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "output_amounts": [95000],
            "fee": 5000,
        }

    def test_valid_record_passes(self):
        res = self.validator.validate(self.valid_record)
        assert res.is_valid is True
        assert res.reason_code is None
        assert res.cleaned_record is not None

    def test_invalid_txid_quarantined(self):
        bad = dict(self.valid_record, txid="not-a-64-char-hex")
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.INVALID_TXID

    def test_invalid_address_quarantined(self):
        bad = dict(self.valid_record, input_addresses=["invalid_bitcoin_addr!!!"])
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.INVALID_ADDRESS

    def test_amount_mismatch_quarantined(self):
        # 100000 in, 95000 out, but fee says 1000 (100000 - 95000 != 1000)
        bad = dict(self.valid_record, fee=1000)
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.AMOUNT_MISMATCH

    def test_negative_amount_quarantined(self):
        bad = dict(self.valid_record, input_amounts=[-500])
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.NEGATIVE_OR_ZERO_AMOUNT

    def test_timestamp_anomaly_quarantined(self):
        # Year 1990 is before Bitcoin genesis in 2009
        bad = dict(self.valid_record, timestamp=631152000.0)
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.TIMESTAMP_ANOMALY

    def test_invalid_ip_quarantined(self):
        bad = dict(self.valid_record, src_ip="999.999.999.999")
        res = self.validator.validate(bad)
        assert res.is_valid is False
        assert res.reason_code == QuarantineReason.INVALID_IP


class TestIdempotency:
    """Re-ingesting the exact same file must not duplicate records."""

    def test_idempotent_ingest(self):
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)

        # First run
        r1 = pipeline.run(TEST_CSV)
        counts1 = db.get_counts()

        # Second run with exact same dataset
        r2 = pipeline.run(TEST_CSV)
        counts2 = db.get_counts()

        # All rows in run 2 should be flagged as duplicates
        assert r2.duplicate_rows == r1.valid_rows + r1.duplicate_rows
        assert r2.valid_rows == 0
        # Total rows in DB should remain exactly identical
        assert counts1 == counts2


class TestEnrichmentAndParquetExport:
    """Verify GeoIP/ASN enrichment and Parquet export."""

    def test_enrichment_and_export(self, tmp_path):
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)
        rep = pipeline.run(TEST_JSON)

        # Verify enrichment fields exist in DuckDB
        rows = db.conn.execute("SELECT src_country, src_asn, is_anonymizer FROM observations LIMIT 50").fetchall()
        for country, asn, is_anon in rows:
            assert len(country) == 2
            assert asn.startswith("AS")
            assert isinstance(is_anon, bool)

        # Export Parquet
        export_dir = tmp_path / "parquet"
        file_map = db.export_parquet(export_dir)

        assert len(file_map) >= 6
        for name, path in file_map.items():
            p = Path(path)
            assert p.exists()
            assert p.stat().st_size > 0


class TestApiEndpoints:
    """Test FastAPI ingestion endpoints."""

    def test_detect_schema_endpoint(self):
        client = TestClient(app)
        with open(TEST_JSON, "rb") as f:
            res = client.post(
                "/api/ingest/detect-schema",
                files={"file": ("observations.json", f, "application/json")},
            )
        assert res.status_code == 200
        data = res.json()
        assert "headers" in data
        assert "detected_mapping" in data
        assert data["detected_mapping"].get("txid") == "txid"

    def test_profiles_endpoints(self):
        client = TestClient(app)
        save_res = client.post(
            "/api/ingest/save-profile",
            json={"profile_name": "api_test_prof", "mapping": {"col_a": "txid"}},
        )
        assert save_res.status_code == 200

        list_res = client.get("/api/ingest/profiles")
        assert list_res.status_code == 200
        profiles = list_res.json()
        assert any(p["profile_name"] == "api_test_prof" for p in profiles)

    def test_jobs_list_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/ingest/jobs")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
