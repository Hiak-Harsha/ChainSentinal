from __future__ import annotations

import json
import logging
from pathlib import Path
import threading
import time
from typing import Any

import duckdb
import pyarrow as pa

from chainsentinel.storage.schema import SCHEMA_DDL

logger = logging.getLogger("chainsentinel.storage.db")


class DatabaseManager:
    """Manages DuckDB embedded database connections and operations."""

    _instance: DatabaseManager | None = None
    _lock = threading.RLock()
    _thread_local = threading.local()

    def __init__(self, db_path: str | Path = "data/chainsentinel.duckdb"):
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # duckdb allows in-memory with ":memory:" or file path
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.RLock()
        self._thread_local = threading.local()
        self.initialize()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get thread-isolated DuckDB cursor from the shared connection."""
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = duckdb.connect(str(self.db_path))
        if not hasattr(self._thread_local, "cursor") or self._thread_local.cursor is None:
            with self._lock:
                self._thread_local.cursor = self._conn.cursor()
        return self._thread_local.cursor

    def cursor(self) -> duckdb.DuckDBPyConnection:
        """Get a lightweight cursor for thread isolation."""
        return self.conn

    def initialize(self) -> None:
        """Initialize database schema tables and indexes."""
        with self._lock:
            if self._conn is None:
                self._conn = duckdb.connect(str(self.db_path))
            for statement in SCHEMA_DDL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    self._conn.execute(stmt)

    def close(self) -> None:
        """Close connection cleanly."""
        with self._lock:
            if hasattr(self._thread_local, "cursor"):
                self._thread_local.cursor = None
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def insert_observations_batch(self, rows_or_table: list[dict[str, Any]] | pa.Table) -> int:
        """Batch insert network observations with conflict ignore on obs_id using vectorized Arrow."""
        if isinstance(rows_or_table, pa.Table):
            tbl = rows_or_table
            if tbl.num_rows == 0:
                return 0
            self.conn.execute("INSERT OR IGNORE INTO observations SELECT * FROM tbl")
            return tbl.num_rows

        if not rows_or_table:
            return 0
        rows = rows_or_table
        tbl = pa.Table.from_pydict({
            "obs_id": [r["obs_id"] for r in rows],
            "ts": [float(r["ts"]) for r in rows],
            "src_ip": [str(r["src_ip"]) for r in rows],
            "dst_ip": [str(r["dst_ip"]) for r in rows],
            "src_port": [int(r["src_port"]) for r in rows],
            "dst_port": [int(r["dst_port"]) for r in rows],
            "txid": [str(r["txid"]) for r in rows],
            "src_country": [str(r.get("src_country") or "") for r in rows],
            "src_asn": [str(r.get("src_asn") or "") for r in rows],
            "src_asn_org": [str(r.get("src_asn_org") or "") for r in rows],
            "is_anonymizer": [bool(r.get("is_anonymizer", False)) for r in rows],
            "sensor_id": [str(r.get("sensor_id") or "") for r in rows],
        })
        self.conn.execute("INSERT OR IGNORE INTO observations SELECT * FROM tbl")
        return len(rows)

    def insert_observations_arrow(self, table: pa.Table) -> int:
        """Direct zero-copy Arrow streaming insertion for high-throughput batching."""
        tbl = table
        if tbl.num_rows == 0:
            return 0
        self.conn.execute("INSERT OR IGNORE INTO observations SELECT * FROM tbl")
        return tbl.num_rows

    def insert_transactions_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert transactions with conflict ignore on txid."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "txid": [r["txid"] for r in rows],
            "first_seen_ts": [float(r["first_seen_ts"]) for r in rows],
            "fee_sat": [int(r["fee_sat"]) for r in rows],
            "vsize": [int(r.get("vsize", 250)) for r in rows],
            "fee_rate": [float(r.get("fee_rate", 1.0)) for r in rows],
            "n_in": [int(r["n_in"]) for r in rows],
            "n_out": [int(r["n_out"]) for r in rows],
            "total_in": [int(r["total_in"]) for r in rows],
            "total_out": [int(r["total_out"]) for r in rows],
            "script_types": [r.get("script_types", ["p2wpkh"]) for r in rows],
        })
        self.conn.execute("INSERT OR IGNORE INTO transactions SELECT * FROM tbl")
        return len(rows)

    def insert_inputs_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert transaction inputs."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "txid": [r["txid"] for r in rows],
            "idx": [int(r["idx"]) for r in rows],
            "address": [str(r["address"]) for r in rows],
            "amount": [int(r["amount"]) for r in rows],
        })
        self.conn.execute("INSERT OR IGNORE INTO tx_inputs SELECT * FROM tbl")
        return len(rows)

    def insert_outputs_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert transaction outputs."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "txid": [r["txid"] for r in rows],
            "idx": [int(r["idx"]) for r in rows],
            "address": [str(r["address"]) for r in rows],
            "amount": [int(r["amount"]) for r in rows],
            "script_type": [str(r.get("script_type", "p2wpkh")) for r in rows],
        })
        self.conn.execute("INSERT OR IGNORE INTO tx_outputs SELECT * FROM tbl")
        return len(rows)

    def upsert_addresses_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch upsert addresses with first_seen and last_seen updates."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "address": [r["address"] for r in rows],
            "first_seen": [float(r["first_seen"]) for r in rows],
            "last_seen": [float(r["last_seen"]) for r in rows],
            "script_type": [str(r.get("script_type", "p2wpkh")) for r in rows],
        })
        self.conn.execute("""
            INSERT INTO addresses SELECT * FROM tbl
            ON CONFLICT (address) DO UPDATE SET
                first_seen = LEAST(addresses.first_seen, excluded.first_seen),
                last_seen = GREATEST(addresses.last_seen, excluded.last_seen)
        """)
        return len(rows)

    def insert_quarantined_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert quarantined invalid records into quarantine table."""
        if not rows:
            return 0
        reasons = [str(r.get("quarantine_reason") or r.get("reason_code") or "unknown") for r in rows]
        tbl = pa.Table.from_pydict({
            "obs_id": [r["obs_id"] for r in rows],
            "raw_data": [json.dumps(r.get("raw_data", {}), default=str) if isinstance(r.get("raw_data"), dict) else str(r.get("raw_data", "")) for r in rows],
            "quarantine_reason": reasons,
            "reason_code": reasons,
            "error_details": [str(r.get("error_details") or "") for r in rows],
            "ingested_at": [float(r["ingested_at"]) for r in rows],
        })
        self.conn.execute("INSERT OR IGNORE INTO quarantine SELECT * FROM tbl")
        return len(rows)

    def create_ingest_job(
        self,
        job_id: str,
        file_path: str,
        format_: str,
        status: str = "running",
        started_at: float = 0.0,
    ) -> None:
        """Record a new ingestion job."""
        self.conn.execute(
            """
            INSERT INTO ingest_jobs (job_id, file_path, format, status, started_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [job_id, file_path, format_, status, started_at],
        )

    def update_ingest_job(
        self,
        job_id: str,
        status: str,
        total_rows: int = 0,
        valid_rows: int = 0,
        quarantined_rows: int = 0,
        completed_at: float = 0.0,
        qc_report: dict[str, Any] | None = None,
    ) -> None:
        """Update job completion details and status."""
        qc_json = json.dumps(qc_report) if qc_report else None
        self.conn.execute(
            """
            UPDATE ingest_jobs SET
                status = ?,
                total_rows = ?,
                valid_rows = ?,
                quarantined_rows = ?,
                completed_at = ?,
                qc_report_json = ?
            WHERE job_id = ?
            """,
            [status, total_rows, valid_rows, quarantined_rows, completed_at, qc_json, job_id],
        )

    def get_ingest_job(self, job_id: str) -> dict[str, Any] | None:
        """Fetch details of an ingestion job."""
        res = self.conn.execute(
            "SELECT * FROM ingest_jobs WHERE job_id = ?", [job_id]
        ).fetchone()
        if not res:
            return None
        cols = [desc[0] for desc in self.conn.description]
        d = dict(zip(cols, res))
        if d.get("qc_report_json"):
            try:
                d["qc_report"] = json.loads(d["qc_report_json"])
            except Exception as err:
                logger.warning("Failed to parse qc_report_json for job %s: %s", job_id, err)
                d["qc_report"] = None
        return d

    def list_ingest_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        """List past ingestion jobs ordered by started_at DESC."""
        cursor = self.conn.execute(
            "SELECT * FROM ingest_jobs ORDER BY started_at DESC LIMIT ?", [limit]
        )
        cols = [desc[0] for desc in cursor.description]
        jobs = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            if d.get("qc_report_json"):
                try:
                    d["qc_report"] = json.loads(d["qc_report_json"])
                except Exception as err:
                    logger.warning("Failed to parse qc_report_json in job list: %s", err)
                    d["qc_report"] = None
            jobs.append(d)
        return jobs

    def get_existing_obs_ids(self) -> set[str]:
        """Fetch all known observation IDs from DuckDB."""
        cursor = self.conn.execute("SELECT obs_id FROM observations")
        return {r[0] for r in cursor.fetchall()}

    def save_schema_profile(self, profile_name: str, mapping: dict[str, str], created_at: float) -> None:
        """Save a custom schema mapping profile."""
        mapping_json = json.dumps(mapping)
        self.conn.execute(
            """
            INSERT INTO schema_mapping_profiles (profile_name, mapping_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT (profile_name) DO UPDATE SET mapping_json = excluded.mapping_json
            """,
            [profile_name, mapping_json, created_at],
        )

    def get_schema_profile(self, profile_name: str) -> dict[str, str] | None:
        """Retrieve a saved schema mapping profile."""
        res = self.conn.execute(
            "SELECT mapping_json FROM schema_mapping_profiles WHERE profile_name = ?", [profile_name]
        ).fetchone()
        if res and res[0]:
            return json.loads(res[0])
        return None

    def list_schema_profiles(self) -> list[dict[str, Any]]:
        """List all saved schema profiles."""
        cursor = self.conn.execute("SELECT profile_name, mapping_json, created_at FROM schema_mapping_profiles")
        profiles = []
        for name, m_json, created in cursor.fetchall():
            try:
                mapping = json.loads(m_json)
            except Exception as err:
                logger.warning("Failed to parse schema profile mapping for %s: %s", name, err)
                mapping = {}
            profiles.append({"profile_name": name, "mapping": mapping, "created_at": created})
        return profiles

    def insert_entities_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace resolved entities."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "entity_id": [r["entity_id"] for r in rows],
            "entity_type": [r.get("entity_type", "INDIVIDUAL") for r in rows],
            "member_count": [int(r.get("member_count", 1)) for r in rows],
            "resolution_conf": [float(r.get("resolution_conf", 1.0)) for r in rows],
            "first_seen": [float(r.get("first_seen", 0.0)) for r in rows],
            "last_seen": [float(r.get("last_seen", 0.0)) for r in rows],
            "total_received_sat": [int(r.get("total_received_sat", 0)) for r in rows],
            "total_sent_sat": [int(r.get("total_sent_sat", 0)) for r in rows],
            "created_at": [float(r.get("created_at", time.time())) for r in rows],
        })
        self.conn.register("_entity_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO entities SELECT * FROM _entity_chunk")
        self.conn.unregister("_entity_chunk")
        return len(rows)

    def insert_address_entity_map_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace address to entity resolution mappings."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "address": [r["address"] for r in rows],
            "entity_id": [r["entity_id"] for r in rows],
            "confidence": [float(r.get("confidence", 1.0)) for r in rows],
            "method": [str(r.get("method", "CIOH")) for r in rows],
        })
        self.conn.register("_aem_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO address_entity_map SELECT * FROM _aem_chunk")
        self.conn.unregister("_aem_chunk")
        return len(rows)

    def insert_graph_edges_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert graph edges."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "source": [r["source"] for r in rows],
            "target": [r["target"] for r in rows],
            "edge_type": [r["edge_type"] for r in rows],
            "weight": [float(r.get("weight", 1.0)) for r in rows],
            "metadata_json": [r.get("metadata_json", "{}") for r in rows],
        })
        self.conn.register("_edge_chunk", tbl)
        self.conn.execute("INSERT INTO graph_edges SELECT * FROM _edge_chunk")
        self.conn.unregister("_edge_chunk")
        return len(rows)

    def clear_graph_resolution(self) -> None:
        """Clear previous clustering and graph edges to permit re-running resolution."""
        self.conn.execute("DELETE FROM entities")
        self.conn.execute("DELETE FROM address_entity_map")
        self.conn.execute("DELETE FROM graph_edges")

    def get_clustering_data(self) -> dict[str, Any]:
        """Fetch transactions, inputs, outputs, and observations for graph clustering."""
        txs = self.conn.execute(
            "SELECT txid, first_seen_ts, fee_sat, vsize, fee_rate, n_in, n_out, total_in, total_out FROM transactions"
        ).fetchall()
        tx_cols = ["txid", "first_seen_ts", "fee_sat", "vsize", "fee_rate", "n_in", "n_out", "total_in", "total_out"]
        tx_list = [dict(zip(tx_cols, r)) for r in txs]

        inputs = self.conn.execute("SELECT txid, idx, address, amount FROM tx_inputs").fetchall()
        in_cols = ["txid", "idx", "address", "amount"]
        in_list = [dict(zip(in_cols, r)) for r in inputs]

        outputs = self.conn.execute("SELECT txid, idx, address, amount, script_type FROM tx_outputs").fetchall()
        out_cols = ["txid", "idx", "address", "amount", "script_type"]
        out_list = [dict(zip(out_cols, r)) for r in outputs]

        obs = self.conn.execute(
            "SELECT txid, ts, src_ip, dst_ip, src_port, dst_port, src_country, src_asn, is_anonymizer FROM observations"
        ).fetchall()
        obs_cols = ["txid", "ts", "src_ip", "dst_ip", "src_port", "dst_port", "src_country", "src_asn", "is_anonymizer"]
        obs_list = [dict(zip(obs_cols, r)) for r in obs]

        return {
            "transactions": tx_list,
            "inputs": in_list,
            "outputs": out_list,
            "observations": obs_list,
        }

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details of a specific entity."""
        res = self.conn.execute("SELECT * FROM entities WHERE entity_id = ?", [entity_id]).fetchone()
        if not res:
            return None
        cols = [desc[0] for desc in self.conn.description]
        return dict(zip(cols, res))

    def list_entities(
        self,
        limit: int = 50,
        offset: int = 0,
        entity_type: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """List entities ordered by member_count DESC, total_received_sat DESC with optional search."""
        where_clauses = []
        params = []
        if entity_type:
            where_clauses.append("entity_type = ?")
            params.append(entity_type)
        if search:
            where_clauses.append("(entity_id ILIKE ? OR entity_type ILIKE ?)")
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f"SELECT * FROM entities {where_sql} ORDER BY member_count DESC, total_received_sat DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = self.conn.execute(query, params)
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_entity_addresses(self, entity_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch addresses belonging to an entity."""
        cursor = self.conn.execute(
            """
            SELECT a.address, a.confidence, a.method, addr.first_seen, addr.last_seen, addr.script_type
            FROM address_entity_map a
            LEFT JOIN addresses addr ON a.address = addr.address
            WHERE a.entity_id = ?
            LIMIT ?
            """,
            [entity_id, limit],
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_ego_subgraph(self, center_id: str, hops: int = 2, max_edges: int = 150) -> dict[str, Any]:
        """Extract an ego subgraph centered on center_id (entity_id, address, or txid)."""
        visited_nodes: set[str] = {center_id}
        frontier: set[str] = {center_id}
        collected_edges: list[dict[str, Any]] = []

        for _ in range(hops):
            if not frontier:
                break
            frontier_list = list(frontier)
            placeholders = ",".join("?" for _ in frontier_list)
            q = f"""
                SELECT source, target, edge_type, weight, metadata_json
                FROM graph_edges
                WHERE source IN ({placeholders}) OR target IN ({placeholders})
                LIMIT ?
            """
            cursor = self.conn.execute(q, frontier_list + frontier_list + [max_edges])
            cols = [desc[0] for desc in cursor.description]
            next_frontier: set[str] = set()

            for row in cursor.fetchall():
                edge = dict(zip(cols, row))
                collected_edges.append(edge)
                for endpoint in (edge["source"], edge["target"]):
                    if endpoint not in visited_nodes:
                        visited_nodes.add(endpoint)
                        next_frontier.add(endpoint)
            frontier = next_frontier

        # Classify nodes
        nodes: list[dict[str, Any]] = []
        for n in visited_nodes:
            node_type = "UNKNOWN"
            if n.startswith("ENT_"):
                node_type = "Entity"
            elif len(n) == 64 and all(c in "0123456789abcdefABCDEF" for c in n):
                node_type = "Transaction"
            elif n.startswith(("1", "3", "bc1")):
                node_type = "Address"
            elif "." in n or ":" in n:
                node_type = "IP"
            nodes.append({"id": n, "label": n, "type": node_type})

        return {
            "center": center_id,
            "nodes": nodes,
            "edges": collected_edges,
        }

    def insert_tx_origins_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace first-seen transaction origin estimates."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "txid": [r["txid"] for r in rows],
            "origin_ip": [r["origin_ip"] for r in rows],
            "confidence": [float(r.get("confidence", 1.0)) for r in rows],
            "delta_t": [float(r.get("delta_t", 0.0)) for r in rows],
            "is_anonymizer": [bool(r.get("is_anonymizer", False)) for r in rows],
            "sensor_count": [int(r.get("sensor_count", 1)) for r in rows],
        })
        self.conn.register("_txo_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO tx_origins SELECT * FROM _txo_chunk")
        self.conn.unregister("_txo_chunk")
        return len(rows)

    def insert_ip_entity_links_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace IP to Entity attribution links."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "ip": [r["ip"] for r in rows],
            "entity_id": [r["entity_id"] for r in rows],
            "score": [float(r.get("score", 0.0)) for r in rows],
            "posterior_prob": [float(r.get("posterior_prob", 0.0)) for r in rows],
            "n_tx": [int(r.get("n_tx", 1)) for r in rows],
            "first_seen_ratio": [float(r.get("first_seen_ratio", 0.0)) for r in rows],
        })
        self.conn.register("_iel_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO ip_entity_links SELECT * FROM _iel_chunk")
        self.conn.unregister("_iel_chunk")
        return len(rows)

    def insert_shares_origin_links_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace multi-cluster shares_origin links."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "entity_a": [r["entity_a"] for r in rows],
            "entity_b": [r["entity_b"] for r in rows],
            "shared_ip": [r["shared_ip"] for r in rows],
            "co_occurrences": [int(r.get("co_occurrences", 1)) for r in rows],
            "p_value": [float(r.get("p_value", 1.0)) for r in rows],
        })
        self.conn.register("_sol_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO shares_origin_links SELECT * FROM _sol_chunk")
        self.conn.unregister("_sol_chunk")
        return len(rows)

    def insert_entity_network_signatures_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace entity behavioral network signatures."""
        if not rows:
            return 0
        tbl = pa.Table.from_pydict({
            "entity_id": [r["entity_id"] for r in rows],
            "non_standard_port_ratio": [float(r.get("non_standard_port_ratio", 0.0)) for r in rows],
            "ip_churn_rate": [float(r.get("ip_churn_rate", 0.0)) for r in rows],
            "asn_count": [int(r.get("asn_count", 0)) for r in rows],
            "anonymizer_ratio": [float(r.get("anonymizer_ratio", 0.0)) for r in rows],
            "circadian_entropy": [float(r.get("circadian_entropy", 0.0)) for r in rows],
            "geo_hop_count": [int(r.get("geo_hop_count", 0)) for r in rows],
        })
        self.conn.register("_ens_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO entity_network_signatures SELECT * FROM _ens_chunk")
        self.conn.unregister("_ens_chunk")
        return len(rows)

    def clear_correlation_data(self) -> None:
        """Clear previous correlation tables before re-running correlation engine."""
        self.conn.execute("DELETE FROM tx_origins")
        self.conn.execute("DELETE FROM ip_entity_links")
        self.conn.execute("DELETE FROM shares_origin_links")
        self.conn.execute("DELETE FROM entity_network_signatures")

    def get_entity_ip_attribution(self, entity_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get top-k attributed IPs for an entity with posterior scores and network details."""
        cursor = self.conn.execute(
            """
            SELECT l.ip, l.entity_id, l.score, l.posterior_prob, l.n_tx, l.first_seen_ratio,
                   COALESCE(o.src_country, '') as country,
                   COALESCE(o.src_asn, '') as asn,
                   COALESCE(o.src_asn_org, '') as asn_org,
                   COALESCE(o.is_anonymizer, false) as is_anonymizer
            FROM ip_entity_links l
            LEFT JOIN (
                SELECT src_ip, src_country, src_asn, src_asn_org, is_anonymizer
                FROM observations
                GROUP BY src_ip, src_country, src_asn, src_asn_org, is_anonymizer
            ) o ON l.ip = o.src_ip
            WHERE l.entity_id = ?
            ORDER BY l.posterior_prob DESC, l.score DESC
            LIMIT ?
            """,
            [entity_id, limit],
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def list_shares_origin_links(self, limit: int = 50, max_p_value: float = 0.05) -> list[dict[str, Any]]:
        """List statistically significant operator links across entities."""
        cursor = self.conn.execute(
            """
            SELECT entity_a, entity_b, shared_ip, co_occurrences, p_value
            FROM shares_origin_links
            WHERE p_value <= ?
            ORDER BY p_value ASC, co_occurrences DESC
            LIMIT ?
            """,
            [max_p_value, limit],
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_entity_network_signatures(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch network signature features for an entity."""
        res = self.conn.execute(
            "SELECT * FROM entity_network_signatures WHERE entity_id = ?", [entity_id]
        ).fetchone()
        if not res:
            return None
        cols = [desc[0] for desc in self.conn.description]
        return dict(zip(cols, res))

    def insert_alerts_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch insert or replace investigative alerts."""
        if not rows:
            return 0
        now = time.time()
        json_payloads = []
        for r in rows:
            raw = r.get("alert_json") if "alert_json" in r and r["alert_json"] is not None else r
            if isinstance(raw, dict):
                json_payloads.append(json.dumps(raw))
            else:
                json_payloads.append(str(raw or "{}"))

        tbl = pa.Table.from_pydict({
            "alert_id": [r["alert_id"] for r in rows],
            "entity_id": [r.get("entity_id") or "" for r in rows],
            "priority": [float(r.get("priority", 0.0)) for r in rows],
            "risk_score": [float(r.get("risk_score", 0.0)) for r in rows],
            "status": [str(r.get("status", "NEW")) for r in rows],
            "alert_json": json_payloads,
            "created_at": [float(r.get("created_at", now)) for r in rows],
        })
        self.conn.register("_alert_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO alerts SELECT * FROM _alert_chunk")
        self.conn.unregister("_alert_chunk")
        return len(rows)

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Fetch alert by alert_id."""
        res = self.conn.execute("SELECT * FROM alerts WHERE alert_id = ?", [alert_id]).fetchone()
        if not res:
            return None
        cols = [desc[0] for desc in self.conn.description]
        data = dict(zip(cols, res))
        if isinstance(data.get("alert_json"), str):
            try:
                parsed = json.loads(data["alert_json"])
                data["alert_data"] = parsed if isinstance(parsed, dict) else data
            except Exception as err:
                logger.warning("Failed to parse alert_json for %s: %s", alert_id, err)
                data["alert_data"] = data
        else:
            data["alert_data"] = data
        return data

    def list_alerts(
        self,
        min_priority: float = 0.0,
        min_risk: float = 0.0,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List alerts filtered by priority, risk score, and status."""
        query = "SELECT * FROM alerts WHERE priority >= ? AND risk_score >= ?"
        params: list[Any] = [min_priority, min_risk]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY priority DESC, risk_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = self.conn.execute(query, params)
        cols = [desc[0] for desc in cursor.description]
        results = []
        for r in cursor.fetchall():
            d = dict(zip(cols, r))
            if isinstance(d.get("alert_json"), str):
                try:
                    parsed = json.loads(d["alert_json"])
                    d["alert_data"] = parsed if isinstance(parsed, dict) else d
                except Exception as err:
                    logger.warning("Failed to parse alert_json in list_alerts: %s", err)
                    d["alert_data"] = d
            else:
                d["alert_data"] = d
            results.append(d)
        return results

    def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update an alert's status (NEW, INVESTIGATING, ESCALATED, CLOSED_FALSE_POSITIVE, RESOLVED)."""
        self.conn.execute(
            "UPDATE alerts SET status = ? WHERE alert_id = ?", [status, alert_id]
        )
        res = self.conn.execute(
            "SELECT status FROM alerts WHERE alert_id = ?", [alert_id]
        ).fetchone()
        return res is not None and res[0] == status

    def save_entity_features_batch(self, rows: list[dict[str, Any]]) -> int:
        """Batch save multimodal feature vectors per entity."""
        if not rows:
            return 0
        now = time.time()
        tbl = pa.Table.from_pydict({
            "entity_id": [r["entity_id"] for r in rows],
            "feature_vector_json": [
                json.dumps(r.get("features", {})) if isinstance(r.get("features"), dict) else str(r.get("feature_vector_json", "{}"))
                for r in rows
            ],
            "updated_at": [float(r.get("updated_at", now)) for r in rows],
        })
        self.conn.register("_feat_chunk", tbl)
        self.conn.execute("INSERT OR REPLACE INTO entity_features SELECT * FROM _feat_chunk")
        self.conn.unregister("_feat_chunk")
        return len(rows)

    def get_entity_features(self, entity_id: str) -> dict[str, Any] | None:
        """Get feature vector for a specific entity."""
        res = self.conn.execute(
            "SELECT entity_id, feature_vector_json, updated_at FROM entity_features WHERE entity_id = ?",
            [entity_id],
        ).fetchone()
        if not res:
            return None
        try:
            feats = json.loads(res[1])
        except Exception as err:
            logger.warning("Failed to parse entity feature vector for %s: %s", entity_id, err)
            feats = {}
        return {"entity_id": res[0], "features": feats, "updated_at": res[2]}

    def list_all_entity_features(self) -> list[dict[str, Any]]:
        """Retrieve all computed entity feature vectors."""
        cursor = self.conn.execute("SELECT entity_id, feature_vector_json, updated_at FROM entity_features")
        results = []
        for row in cursor.fetchall():
            try:
                feats = json.loads(row[1])
            except Exception as err:
                logger.warning("Failed to parse entity feature vector in list_all: %s", err)
                feats = {}
            results.append({"entity_id": row[0], "features": feats, "updated_at": row[2]})
        return results

    def save_model_metrics(self, model_name: str, metrics: dict[str, Any]) -> None:
        """Save or update evaluation metrics for an ML model."""
        now = time.time()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO model_metrics (model_name, metrics_json, evaluated_at)
            VALUES (?, ?, ?)
            """,
            [model_name, json.dumps(metrics), now],
        )

    def get_model_metrics(self, model_name: str) -> dict[str, Any] | None:
        """Fetch model metrics for a specific model."""
        res = self.conn.execute(
            "SELECT model_name, metrics_json, evaluated_at FROM model_metrics WHERE model_name = ?",
            [model_name],
        ).fetchone()
        if not res:
            return None
        try:
            metrics = json.loads(res[1])
        except Exception as err:
            logger.warning("Failed to parse model metrics for %s: %s", model_name, err)
            metrics = {}
        return {"model_name": res[0], "metrics": metrics, "evaluated_at": res[2]}

    def list_model_metrics(self) -> list[dict[str, Any]]:
        """Fetch all model evaluation entries."""
        cursor = self.conn.execute("SELECT model_name, metrics_json, evaluated_at FROM model_metrics")
        results = []
        for row in cursor.fetchall():
            try:
                m = json.loads(row[1])
            except Exception as err:
                logger.warning("Failed to parse model metrics in list_all: %s", err)
                m = {}
            results.append({"model_name": row[0], "metrics": m, "evaluated_at": row[2]})
        return results

    def save_taint_trace(
        self,
        trace_id: str,
        root_ref: str,
        direction: str,
        decay_model: str,
        max_hops: int,
        hops: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> None:
        """Save executed taint trace run."""
        now = time.time()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO taint_traces 
            (trace_id, root_ref, direction, decay_model, max_hops, hops_json, summary_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trace_id,
                root_ref,
                direction,
                decay_model,
                max_hops,
                json.dumps(hops),
                json.dumps(summary),
                now,
            ],
        )

    def get_taint_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Fetch taint trace by trace_id."""
        res = self.conn.execute(
            "SELECT trace_id, root_ref, direction, decay_model, max_hops, hops_json, summary_json, created_at FROM taint_traces WHERE trace_id = ?",
            [trace_id],
        ).fetchone()
        if not res:
            return None
        return {
            "trace_id": res[0],
            "root_ref": res[1],
            "direction": res[2],
            "decay_model": res[3],
            "max_hops": res[4],
            "hops": json.loads(res[5]) if res[5] else [],
            "summary": json.loads(res[6]) if res[6] else {},
            "created_at": res[7],
        }

    def list_taint_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recently executed taint traces."""
        cursor = self.conn.execute(
            "SELECT trace_id, root_ref, direction, decay_model, max_hops, summary_json, created_at FROM taint_traces ORDER BY created_at DESC LIMIT ?",
            [limit],
        )
        results = []
        for r in cursor.fetchall():
            results.append({
                "trace_id": r[0],
                "root_ref": r[1],
                "direction": r[2],
                "decay_model": r[3],
                "max_hops": r[4],
                "summary": json.loads(r[5]) if r[5] else {},
                "created_at": r[6],
            })
        return results

    def save_investigative_case(
        self,
        case_id: str,
        target_id: str,
        title: str,
        status: str,
        case_data: dict[str, Any],
    ) -> None:
        """Save or update an autonomous investigative case file."""
        now = time.time()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO investigative_cases
            (case_id, target_id, title, status, case_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [case_id, target_id, title, status, json.dumps(case_data), now],
        )

    def get_investigative_case(self, case_id: str) -> dict[str, Any] | None:
        """Retrieve full investigative case file."""
        res = self.conn.execute(
            "SELECT case_id, target_id, title, status, case_json, created_at FROM investigative_cases WHERE case_id = ?",
            [case_id],
        ).fetchone()
        if not res:
            return None
        return {
            "case_id": res[0],
            "target_id": res[1],
            "title": res[2],
            "status": res[3],
            "case_data": json.loads(res[4]) if res[4] else {},
            "created_at": res[5],
        }

    def list_investigative_cases(self, limit: int = 50) -> list[dict[str, Any]]:
        """List all investigative case files."""
        cursor = self.conn.execute(
            "SELECT case_id, target_id, title, status, case_json, created_at FROM investigative_cases ORDER BY created_at DESC LIMIT ?",
            [limit],
        )
        results = []
        for r in cursor.fetchall():
            c_data = json.loads(r[4]) if r[4] else {}
            results.append({
                "case_id": r[0],
                "target_id": r[1],
                "title": r[2],
                "status": r[3],
                "case_data": c_data,
                "created_at": r[5],
            })
        return results

    def export_parquet(self, output_dir: str | Path) -> dict[str, str]:
        """Export all primary tables to Parquet files in output_dir."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        tables = [
            "observations",
            "transactions",
            "tx_inputs",
            "tx_outputs",
            "addresses",
            "quarantine",
            "entities",
            "address_entity_map",
            "graph_edges",
            "tx_origins",
            "ip_entity_links",
            "shares_origin_links",
            "entity_network_signatures",
            "alerts",
            "entity_features",
            "model_metrics",
            "taint_traces",
            "investigative_cases",
        ]
        file_map = {}
        for table in tables:
            target_path = out / f"{table}.parquet"
            self.conn.execute(f"COPY {table} TO '{target_path.as_posix()}' (FORMAT PARQUET)")
            file_map[table] = str(target_path)
        return file_map

    def get_counts(self) -> dict[str, int]:
        """Get row count summary of all core tables."""
        tables = [
            "observations",
            "transactions",
            "tx_inputs",
            "tx_outputs",
            "addresses",
            "quarantine",
            "quarantined_observations",
            "entities",
            "address_entity_map",
            "graph_edges",
            "tx_origins",
            "ip_entity_links",
            "shares_origin_links",
            "entity_network_signatures",
            "alerts",
            "entity_features",
            "model_metrics",
            "taint_traces",
            "investigative_cases",
            "alert_feedback",
            "case_timeline_events",
        ]
        counts = {}
        for t in tables:
            try:
                res = self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                counts[t] = res[0] if res else 0
            except Exception:
                counts[t] = 0
        return counts

    def record_alert_feedback(
        self,
        feedback_id: str,
        alert_id: str,
        entity_id: str,
        analyst_verdict: str,
        notes: str = "",
        timestamp: float | None = None,
    ) -> bool:
        """Record analyst ground-truth verdict for active learning."""
        ts = timestamp or time.time()
        with self._lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO alert_feedback (feedback_id, alert_id, entity_id, analyst_verdict, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [feedback_id, alert_id, entity_id, analyst_verdict, notes, ts],
            )
        return True

    def list_alert_feedback(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recorded analyst verdicts."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT feedback_id, alert_id, entity_id, analyst_verdict, notes, timestamp FROM alert_feedback ORDER BY timestamp DESC LIMIT ?",
                [limit],
            )
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def record_case_timeline_event(
        self,
        event_id: str,
        case_id: str,
        event_type: str,
        target_id: str,
        details: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> bool:
        """Record forensic pivot or investigative action in case audit timeline."""
        ts = timestamp or time.time()
        details_json = json.dumps(details or {})
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO case_timeline_events (event_id, case_id, event_type, target_id, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [event_id, case_id, event_type, target_id, details_json, ts],
            )
        return True

    def get_case_timeline(self, case_id: str) -> list[dict[str, Any]]:
        """Get chronological investigation timeline for a case."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT event_id, case_id, event_type, target_id, details_json, timestamp FROM case_timeline_events WHERE case_id = ? ORDER BY timestamp ASC",
                [case_id],
            )
            cols = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                d = dict(zip(cols, row))
                try:
                    d["details"] = json.loads(d["details_json"])
                except Exception:
                    d["details"] = {}
                events.append(d)
            return events

