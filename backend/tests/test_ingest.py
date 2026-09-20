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

TEST_CSV = "data/samples/observations.csv"
TEST_JSON = "data/samples/observations.json"
TEST_NDJSON = "data/samples/observations.ndjson"
TEST_XML = "data/samples/observations.xml"


@pytest.fixture(scope="session", autouse=True)
def ensure_sample_data():
    csv_p = Path(TEST_CSV)
    if not csv_p.exists() or csv_p.stat().st_size == 0:
        from chainsentinel.gen.generator import Generator
        gen = Generator(target_txs=10, seed=42)
        gen.run(output_dir=str(csv_p.parent), formats=["csv", "json", "xml"])


class TestMultiFormatIngestion:
    """Ingest CSV, JSON, NDJSON, and XML into separate databases and verify data parity."""

    def test_format_parity_counts(self):
        db_csv = DatabaseManager(":memory:")
        db_json = DatabaseManager(":memory:")
        db_ndjson = DatabaseManager(":memory:")
        db_xml = DatabaseManager(":memory:")

        p_csv = IngestPipeline(db=db_csv)
        p_json = IngestPipeline(db=db_json)
        p_ndjson = IngestPipeline(db=db_ndjson)
        p_xml = IngestPipeline(db=db_xml)

        r_csv = p_csv.run(TEST_CSV)
        r_json = p_json.run(TEST_JSON)
        r_ndjson = p_ndjson.run(TEST_NDJSON)
        r_xml = p_xml.run(TEST_XML)

        # All 4 formats should produce identical valid row counts
        assert r_csv.valid_rows == r_json.valid_rows == r_ndjson.valid_rows == r_xml.valid_rows
        assert r_csv.valid_rows > 0

        # Unique transactions, addresses, and IPs should match
        assert r_csv.unique_transactions == r_json.unique_transactions == r_ndjson.unique_transactions == r_xml.unique_transactions
        assert r_csv.unique_addresses == r_json.unique_addresses == r_ndjson.unique_addresses == r_xml.unique_addresses

        # Database table counts should match across all 4 formats
        c_csv = db_csv.get_counts()
        c_json = db_json.get_counts()
        c_ndjson = db_ndjson.get_counts()
        c_xml = db_xml.get_counts()

        assert c_csv["observations"] == c_json["observations"] == c_ndjson["observations"] == c_xml["observations"]
        assert c_csv["transactions"] == c_json["transactions"] == c_ndjson["transactions"] == c_xml["transactions"]
        assert c_csv["tx_inputs"] == c_json["tx_inputs"] == c_ndjson["tx_inputs"] == c_xml["tx_inputs"]
        assert c_csv["tx_outputs"] == c_json["tx_outputs"] == c_ndjson["tx_outputs"] == c_xml["tx_outputs"]
        assert c_csv["addresses"] == c_json["addresses"] == c_ndjson["addresses"] == c_xml["addresses"]


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


class TestPhase2AcceptanceCriteria:
    """Comprehensive test suite enforcing Phase 2 non-negotiables."""

    def test_four_format_parity_and_checksum(self):
        """Format parity test: ingest CSV, JSON array, NDJSON, XML.
        Assert row counts, null counts, and checksums match across all 4 formats.
        """
        import hashlib
        db_csv = DatabaseManager(":memory:")
        db_json = DatabaseManager(":memory:")
        db_ndjson = DatabaseManager(":memory:")
        db_xml = DatabaseManager(":memory:")

        r_csv = IngestPipeline(db=db_csv).run(TEST_CSV)
        r_json = IngestPipeline(db=db_json).run(TEST_JSON)
        r_ndjson = IngestPipeline(db=db_ndjson).run(TEST_NDJSON)
        r_xml = IngestPipeline(db=db_xml).run(TEST_XML)

        # 1. Row counts match
        assert r_csv.valid_rows == r_json.valid_rows == r_ndjson.valid_rows == r_xml.valid_rows
        assert r_csv.valid_rows > 0

        # 2. Null counts / presence match
        for fld in ("txid", "src_ip", "dst_ip", "src_port", "dst_port"):
            assert r_csv.null_percentages[fld] == r_json.null_percentages[fld] == r_ndjson.null_percentages[fld] == r_xml.null_percentages[fld]

        # 3. Content checksums match
        def checksum(db: DatabaseManager) -> str:
            rows = db.conn.execute("SELECT txid, ts, src_ip, dst_ip, src_port, dst_port FROM observations ORDER BY txid, ts, src_ip").fetchall()
            return hashlib.sha256(str(rows).encode()).hexdigest()

        assert checksum(db_csv) == checksum(db_json) == checksum(db_ndjson) == checksum(db_xml)

    def test_safe_xml_xxe_defense(self, tmp_path):
        """Safe XML parsing: defusedxml blocks XXE and external entity expansion."""
        malicious_xml = tmp_path / "xxe_attack.xml"
        malicious_xml.write_text(
            '<?xml version="1.0"?>'
            '<!DOCTYPE test [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>'
            '<root><observation><txid>&xxe;</txid></observation></root>',
            encoding="utf-8"
        )
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)
        rep = pipeline.run(malicious_xml)

        # Attacking payload must be quarantined and never inserted into observations
        assert rep.valid_rows == 0
        assert rep.quarantined_rows >= 1
        assert "xxe_security_violation" in rep.error_breakdown

        counts = db.get_counts()
        assert counts["observations"] == 0
        assert counts["quarantine"] >= 1

    def test_quarantine_table_exact_reason_codes_and_zero_leakage(self, tmp_path):
        """Records failing validation go to quarantine with exact reason codes:
        negative_amount, timestamp_anomaly, invalid_address, invalid_ip, checksum_mismatch.
        Quarantined rows must never leak into downstream analytics.
        """
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)

        # Create records failing each specific rule
        bad_records = [
            # 1. negative_amount
            {
                "txid": "11" * 32, "timestamp": 1700000000.0, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8",
                "src_port": 8333, "dst_port": 8333, "input_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
                "input_amounts": [-1000], "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "output_amounts": [1000], "fee": 100
            },
            # 2. timestamp_anomaly (pre-2009)
            {
                "txid": "22" * 32, "timestamp": 100000000.0, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8",
                "src_port": 8333, "dst_port": 8333, "input_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
                "input_amounts": [50000], "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "output_amounts": [40000], "fee": 10000
            },
            # 3. invalid_address
            {
                "txid": "33" * 32, "timestamp": 1700000000.0, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8",
                "src_port": 8333, "dst_port": 8333, "input_addresses": ["NOT_A_BITCOIN_ADDRESS!!!"],
                "input_amounts": [50000], "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "output_amounts": [40000], "fee": 10000
            },
            # 4. invalid_ip
            {
                "txid": "44" * 32, "timestamp": 1700000000.0, "src_ip": "999.888.777.666", "dst_ip": "8.8.8.8",
                "src_port": 8333, "dst_port": 8333, "input_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
                "input_amounts": [50000], "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "output_amounts": [40000], "fee": 10000
            },
            # 5. checksum_mismatch (total_in - total_out != fee)
            {
                "txid": "55" * 32, "timestamp": 1700000000.0, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8",
                "src_port": 8333, "dst_port": 8333, "input_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
                "input_amounts": [50000], "output_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "output_amounts": [40000], "fee": 5000
            },
        ]

        test_bad_file = tmp_path / "bad_observations.json"
        with open(test_bad_file, "w") as f:
            json.dump(bad_records, f)

        rep = pipeline.run(test_bad_file)
        assert rep.quarantined_rows == 5
        assert rep.valid_rows == 0

        # Verify exact reason codes recorded in quarantine table
        reasons_in_db = [
            r[0] for r in db.conn.execute("SELECT quarantine_reason FROM quarantine").fetchall()
        ]
        assert "negative_amount" in reasons_in_db
        assert "timestamp_anomaly" in reasons_in_db
        assert "invalid_address" in reasons_in_db
        assert "invalid_ip" in reasons_in_db
        assert "checksum_mismatch" in reasons_in_db

        # ZERO LEAKAGE: down-stream analytics tables must have 0 rows
        counts = db.get_counts()
        assert counts["observations"] == 0
        assert counts["transactions"] == 0
        assert counts["tx_inputs"] == 0
        assert counts["tx_outputs"] == 0
        assert counts["addresses"] == 0

    def test_fuzzy_schema_mapping_and_confidence(self):
        """Schema mapping: fuzzy matching with confidence scores and preview."""
        headers = [
            "tx_hsah",           # typo for tx_hash (fuzzy)
            "seen_tstamp",       # typo for seen_time (fuzzy)
            "orig_ip",           # synonym for origin_ip (synonym)
            "dst_ip",            # exact match
            "inpt_addrs",        # typo for input_addrs (fuzzy)
            "input_amounts",     # exact match
            "output_addresses",  # exact match
            "output_amounts",    # exact match
            "fee",               # exact match
        ]
        mapper = SchemaMapper.auto_detect(headers)

        assert mapper.mapping["tx_hsah"] == "txid"
        assert mapper.confidence["tx_hsah"] >= 0.70

        assert mapper.mapping["orig_ip"] == "src_ip"
        assert mapper.confidence["orig_ip"] >= 0.90

        assert mapper.mapping["dst_ip"] == "dst_ip"
        assert mapper.confidence["dst_ip"] == 1.0

        sample_rows = [
            {"tx_hsah": "a" * 64, "seen_tstamp": 1700000000.0, "orig_ip": "1.1.1.1", "dst_ip": "8.8.8.8"}
        ]
        preview = mapper.preview(sample_rows, n=5)
        assert len(preview) == 1
        assert preview[0]["txid"] == "a" * 64
        assert preview[0]["src_ip"] == "1.1.1.1"

    def test_qc_report_comprehensive_metrics(self):
        """QC report generated automatically: row counts, null percentages, value distributions, quarantine rate, ingest throughput."""
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)
        rep = pipeline.run(TEST_CSV)

        rep_dict = rep.to_dict()
        assert "total_rows_processed" in rep_dict
        assert "valid_rows" in rep_dict
        assert "quarantine_rate" in rep_dict
        assert "throughput_rows_per_sec" in rep_dict
        assert "null_percentages" in rep_dict
        assert "value_distributions" in rep_dict

        # Value distributions contains fee and volume stats
        v_dist = rep_dict["value_distributions"]
        assert "fee_sat" in v_dist
        assert "volume_sat" in v_dist
        assert "top_countries" in v_dist
        assert "top_asns" in v_dist

    def test_vectorized_arrow_throughput_benchmark(self):
        """Vectorized ingestion: DuckDB Arrow streaming achieves >= 50,000 rows/sec."""
        import time, pyarrow as pa
        db = DatabaseManager(":memory:")

        N = 50_000
        tbl = pa.table({
            "obs_id": [f"obs_{i:08x}" for i in range(N)],
            "ts": [1700000000.0 + i for i in range(N)],
            "src_ip": ["1.1.1.1"] * N,
            "dst_ip": ["8.8.8.8"] * N,
            "src_port": [8333] * N,
            "dst_port": [8333] * N,
            "txid": [f"tx_{i:08x}" for i in range(N)],
            "src_country": ["US"] * N,
            "src_asn": ["AS13335"] * N,
            "src_asn_org": ["Cloudflare"] * N,
            "is_anonymizer": [False] * N,
            "sensor_id": ["sensor_0"] * N,
        })

        t0 = time.time()
        inserted = db.insert_observations_arrow(tbl)
        t1 = time.time()

        duration = max(0.0001, t1 - t0)
        throughput = inserted / duration
        print(f"Benchmark: {inserted} rows in {duration:.4f}s = {throughput:.1f} rows/sec")
        assert inserted == N
        assert throughput >= 50_000, f"Throughput {throughput:.1f} rows/s fell below 50,000 rows/s target"
