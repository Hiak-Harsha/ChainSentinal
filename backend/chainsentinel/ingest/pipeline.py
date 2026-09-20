"""Ingestion pipeline orchestrator: streaming parse, schema mapping, validation, quarantine, enrichment, and storage."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from pathlib import Path
import time
from typing import Any

from chainsentinel.ingest.enrichment import enrich_record
from chainsentinel.ingest.parsers import (
    BaseStreamingParser,
    CsvStreamingParser,
    JsonStreamingParser,
    XmlStreamingParser,
)
from chainsentinel.ingest.qc_report import DataQualityReport
from chainsentinel.ingest.schema_mapper import CANONICAL_FIELDS, SchemaMapper
from chainsentinel.ingest.validator import RecordValidator
from chainsentinel.storage.db import DatabaseManager


def detect_parser(file_path: str | Path, format_hint: str | None = None) -> BaseStreamingParser:
    """Detect and instantiate appropriate streaming parser for file."""
    path = Path(file_path)
    fmt = (format_hint or path.suffix.lstrip(".")).lower()

    if fmt == "csv":
        return CsvStreamingParser(path)
    elif fmt in ("json", "ndjson"):
        return JsonStreamingParser(path)
    elif fmt == "xml":
        return XmlStreamingParser(path)
    else:
        # Default probe
        with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
            first = f.read(100).strip()
            if first.startswith("<"):
                return XmlStreamingParser(path)
            elif first.startswith("{") or first.startswith("["):
                return JsonStreamingParser(path)
        return CsvStreamingParser(path)


class IngestPipeline:
    """Orchestrates end-to-end ingestion, validation, and storage."""

    def __init__(self, db: DatabaseManager | None = None, batch_size: int = 5_000):
        self.db = db or DatabaseManager()
        self.batch_size = batch_size
        self.validator = RecordValidator()

    def run(
        self,
        file_path: str | Path,
        format_hint: str | None = None,
        mapping_override: dict[str, str] | None = None,
        job_id: str | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> DataQualityReport:
        """Execute streaming ingestion pipeline on dataset file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        start_time = time.time()
        job_id = job_id or f"job_{int(start_time * 1000)}"

        # 1. Initialize job in DB
        parser = detect_parser(path, format_hint)
        detected_fmt = format_hint or path.suffix.lstrip(".") or "unknown"
        self.db.create_ingest_job(job_id=job_id, file_path=str(path), format_=detected_fmt, started_at=start_time)

        # 2. Schema auto-detection
        headers = parser.get_headers()
        mapper = SchemaMapper.auto_detect(headers)
        if mapping_override:
            mapper.mapping.update(mapping_override)

        # 3. Running state
        qc = DataQualityReport()
        seen_obs_hashes: set[str] = self.db.get_existing_obs_ids()
        seen_txids: set[str] = set()
        seen_addrs: set[str] = set()
        seen_ips: set[str] = set()
        field_presence_counts: dict[str, int] = {f: 0 for f in CANONICAL_FIELDS}

        obs_batch: list[dict[str, Any]] = []
        tx_batch: list[dict[str, Any]] = []
        in_batch: list[dict[str, Any]] = []
        out_batch: list[dict[str, Any]] = []
        addr_map: dict[str, dict[str, Any]] = {}
        quarantine_batch: list[dict[str, Any]] = []

        def flush_batches() -> None:
            if obs_batch:
                self.db.insert_observations_batch(obs_batch)
                obs_batch.clear()
            if tx_batch:
                self.db.insert_transactions_batch(tx_batch)
                tx_batch.clear()
            if in_batch:
                self.db.insert_inputs_batch(in_batch)
                in_batch.clear()
            if out_batch:
                self.db.insert_outputs_batch(out_batch)
                out_batch.clear()
            if addr_map:
                self.db.upsert_addresses_batch(list(addr_map.values()))
                addr_map.clear()
            if quarantine_batch:
                self.db.insert_quarantined_batch(quarantine_batch)
                quarantine_batch.clear()

        # 4. Stream and process
        for chunk in parser.iter_chunks():
            for raw_row in chunk:
                qc.total_rows_processed += 1

                # Map record to canonical schema
                mapped = mapper.apply(raw_row)

                # Track completeness
                for canon_f in CANONICAL_FIELDS:
                    if mapped.get(canon_f) is not None and mapped.get(canon_f) != "":
                        field_presence_counts[canon_f] += 1

                # Validate
                val = self.validator.validate(mapped)
                now_ts = time.time()

                if not val.is_valid:
                    qc.quarantined_rows += 1
                    reason = val.reason_code or "UNKNOWN"
                    qc.error_breakdown[reason] = qc.error_breakdown.get(reason, 0) + 1

                    q_obs_id = hashlib.sha256(f"quarantine:{qc.total_rows_processed}:{now_ts}".encode()).hexdigest()[:24]
                    quarantine_batch.append({
                        "obs_id": q_obs_id,
                        "raw_data": raw_row,
                        "reason_code": reason,
                        "error_details": val.error_details,
                        "ingested_at": now_ts,
                    })
                    continue

                # Valid record processing
                rec = val.cleaned_record or {}
                txid = rec["txid"]
                ts = rec["timestamp"]
                src_ip = rec["src_ip"]

                obs_key = f"{txid}:{ts:.3f}:{src_ip}"
                obs_id = hashlib.sha256(obs_key.encode()).hexdigest()[:24]

                if obs_id in seen_obs_hashes:
                    qc.duplicate_rows += 1
                    continue
                seen_obs_hashes.add(obs_id)

                # Network enrichment
                enriched = enrich_record(rec)

                # Append to observation batch
                obs_batch.append({
                    "obs_id": obs_id,
                    "ts": ts,
                    "src_ip": src_ip,
                    "dst_ip": enriched.get("dst_ip", "127.0.0.1"),
                    "src_port": enriched.get("src_port", 8333),
                    "dst_port": enriched.get("dst_port", 8333),
                    "txid": txid,
                    "src_country": enriched.get("src_country", "ZZ"),
                    "src_asn": enriched.get("src_asn", "AS0"),
                    "src_asn_org": enriched.get("src_asn_org", "Unknown"),
                    "is_anonymizer": enriched.get("is_anonymizer", False),
                    "sensor_id": enriched.get("sensor_id", "sensor_0"),
                })

                is_new_tx = txid not in seen_txids
                seen_txids.add(txid)
                script_type = enriched.get("script_type") or "p2wpkh"

                # Append to transaction, inputs, outputs batch only on first observation
                if is_new_tx:
                    tx_batch.append({
                        "txid": txid,
                        "first_seen_ts": ts,
                        "fee_sat": enriched["fee"],
                        "vsize": 250,
                        "fee_rate": round(enriched["fee"] / 250, 2),
                        "n_in": enriched["n_in"],
                        "n_out": enriched["n_out"],
                        "total_in": enriched["total_in"],
                        "total_out": enriched["total_out"],
                        "script_types": [script_type],
                    })

                    # Append inputs
                    for idx, (in_addr, in_amt) in enumerate(zip(enriched["input_addresses"], enriched["input_amounts"])):
                        in_batch.append({
                            "txid": txid,
                            "idx": idx,
                            "address": in_addr,
                            "amount": in_amt,
                        })
                        seen_addrs.add(in_addr)
                        if in_addr not in addr_map:
                            addr_map[in_addr] = {"address": in_addr, "first_seen": ts, "last_seen": ts, "script_type": script_type}
                        else:
                            addr_map[in_addr]["first_seen"] = min(addr_map[in_addr]["first_seen"], ts)
                            addr_map[in_addr]["last_seen"] = max(addr_map[in_addr]["last_seen"], ts)

                    # Append outputs
                    for idx, (out_addr, out_amt) in enumerate(zip(enriched["output_addresses"], enriched["output_amounts"])):
                        out_batch.append({
                            "txid": txid,
                            "idx": idx,
                            "address": out_addr,
                            "amount": out_amt,
                            "script_type": script_type,
                        })
                        seen_addrs.add(out_addr)
                        if out_addr not in addr_map:
                            addr_map[out_addr] = {"address": out_addr, "first_seen": ts, "last_seen": ts, "script_type": script_type}
                        else:
                            addr_map[out_addr]["first_seen"] = min(addr_map[out_addr]["first_seen"], ts)
                            addr_map[out_addr]["last_seen"] = max(addr_map[out_addr]["last_seen"], ts)


                # Metrics update
                qc.valid_rows += 1
                qc.total_volume_satoshis += enriched["total_in"]
                qc.total_fees_satoshis += enriched["fee"]
                if enriched.get("is_anonymizer"):
                    qc.anonymizer_count += 1
                seen_txids.add(txid)
                seen_ips.add(src_ip)

                if len(obs_batch) >= self.batch_size:
                    flush_batches()
                    if progress_callback:
                        progress_callback({
                            "job_id": job_id,
                            "processed": qc.total_rows_processed,
                            "valid": qc.valid_rows,
                            "quarantined": qc.quarantined_rows,
                        })

        # Final flush
        flush_batches()

        # 5. Finalize QC Report
        qc.unique_transactions = len(seen_txids)
        qc.unique_addresses = len(seen_addrs)
        qc.unique_ips = len(seen_ips)
        qc.duration_seconds = round(time.time() - start_time, 2)

        total = max(1, qc.total_rows_processed)
        qc.completeness_scores = {
            k: round(cnt / total, 4) for k, cnt in field_presence_counts.items()
        }

        # 6. Update job status in DB
        self.db.update_ingest_job(
            job_id=job_id,
            status="completed",
            total_rows=qc.total_rows_processed,
            valid_rows=qc.valid_rows,
            quarantined_rows=qc.quarantined_rows,
            completed_at=time.time(),
            qc_report=qc.to_dict(),
        )

        return qc
