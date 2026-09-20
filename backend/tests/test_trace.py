"""Unit tests for Phase 6 — Autonomous Investigation, Taint Tracing & Pathfinding."""

from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.storage.db import DatabaseManager
from chainsentinel.trace.agent import AutonomousInvestigator
from chainsentinel.trace.pathfinder import InvestigativePathfinder
from chainsentinel.trace.taint_tracker import TaintTracker

DATA_DIR = Path(__file__).parent.parent / "data" / "cli_test"
TEST_JSON = str(DATA_DIR / "observations.json")


@pytest.fixture(scope="module")
def prepared_db(tmp_path_factory):
    """Fixture providing a temporary DuckDB database fully ingested, clustered, and correlated."""
    tmp_dir = tmp_path_factory.mktemp("trace_test_db")
    db_file = tmp_dir / "test_trace.duckdb"
    db = DatabaseManager(db_file)

    # 1. Ingest
    ingest_pipe = IngestPipeline(db=db)
    ingest_pipe.run(TEST_JSON)

    # 2. Cluster
    resolver = EntityResolver(db=db, change_threshold=0.65)
    resolver.run()

    # 3. Correlate
    correlator = CorrelationEngine(db=db, time_window_sec=60.0)
    correlator.run()

    return db, tmp_dir


class TestTaintTracker:
    """Verify forward, backward, and decay-model taint tracking."""

    def test_forward_proportional_decay(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        # Get a high-degree or active entity
        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        assert entity_row is not None
        entity_id = entity_row[0]

        res = tracker.trace(
            root_ref=entity_id,
            direction="forward",
            decay_model="proportional",
            max_hops=4,
            min_taint_ratio=0.001,
        )

        assert "trace_id" in res
        assert res["trace_id"].startswith("TRC-")
        assert "summary" in res
        assert res["summary"]["decay_model"] == "proportional"
        assert res["summary"]["direction"] == "FORWARD"
        assert isinstance(res["hops"], list)

        # Check DB persistence
        stored = db.get_taint_trace(res["trace_id"])
        assert stored is not None
        assert stored["trace_id"] == res["trace_id"]
        assert stored["decay_model"] == "proportional"

    def test_forward_fifo_decay(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        entity_id = entity_row[0]

        res = tracker.trace(
            root_ref=entity_id,
            direction="forward",
            decay_model="fifo",
            max_hops=3,
        )

        assert res["summary"]["decay_model"] == "fifo"
        assert isinstance(res["hops"], list)

    def test_forward_poison_decay(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        entity_id = entity_row[0]

        res = tracker.trace(
            root_ref=entity_id,
            direction="forward",
            decay_model="poison",
            max_hops=3,
        )

        assert res["summary"]["decay_model"] == "poison"
        for hop in res["hops"]:
            assert hop["taint_pct"] == 100.0

    def test_backward_tracing(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        entity_id = entity_row[0]

        res = tracker.trace(
            root_ref=entity_id,
            direction="backward",
            decay_model="proportional",
            max_hops=3,
        )

        assert res["summary"]["direction"] == "BACKWARD"
        assert "source_entities" in res["summary"]

    def test_bidirectional_tracing(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        entity_id = entity_row[0]

        res = tracker.trace(
            root_ref=entity_id,
            direction="both",
            decay_model="proportional",
            max_hops=3,
        )

        assert res["summary"]["direction"] == "BOTH"
        assert "forward_hops" in res["summary"]
        assert "backward_hops" in res["summary"]

    def test_trace_from_txid(self, prepared_db):
        db, _ = prepared_db
        tracker = TaintTracker(db)

        tx_row = db.conn.execute("SELECT txid FROM transactions LIMIT 1").fetchone()
        assert tx_row is not None
        txid = tx_row[0]

        res = tracker.trace(
            root_ref=txid,
            direction="forward",
            max_hops=3,
        )

        assert "trace_id" in res
        assert res["summary"]["root_ref"] == txid


class TestInvestigativePathfinder:
    """Verify pathfinding across entity flow topology."""

    def test_resolve_entity(self, prepared_db):
        db, _ = prepared_db
        pathfinder = InvestigativePathfinder(db)

        # 1. Resolve entity ID
        ent = pathfinder.resolve_entity("ENT-TEST01")
        assert ent["entity_id"] == "ENT-TEST01"

        # 2. Resolve known address
        addr_row = db.conn.execute("SELECT address, entity_id FROM address_entity_map LIMIT 1").fetchone()
        assert addr_row is not None
        addr, expected_eid = addr_row[0], addr_row[1]

        resolved = pathfinder.resolve_entity(addr)
        assert resolved["entity_id"] == expected_eid

        # 3. Resolve TXID
        tx_row = db.conn.execute("SELECT txid FROM transactions LIMIT 1").fetchone()
        assert tx_row is not None
        tx_res = pathfinder.resolve_entity(tx_row[0])
        assert tx_res["entity_id"] is not None

    def test_shortest_path_and_highest_volume(self, prepared_db):
        db, _ = prepared_db
        pathfinder = InvestigativePathfinder(db)
        g = pathfinder.build_graph()

        # Find two connected entities
        edges = list(g.edges())
        if not edges:
            pytest.skip("No entity edges in graph")

        src, dst = edges[0][0], edges[0][1]

        # 1. Shortest path
        sp_res = pathfinder.find_shortest_path(source=src, target=dst)
        assert sp_res["found"] is True
        assert sp_res["hop_count"] >= 1
        assert len(sp_res["path"]) == sp_res["hop_count"] + 1
        assert sp_res["path"][0] == src
        assert sp_res["path"][-1] == dst
        assert len(sp_res["hops"]) == sp_res["hop_count"]
        assert len(sp_res["nodes"]) == len(sp_res["path"])

        # 2. Highest volume path
        hv_res = pathfinder.find_highest_volume_path(source=src, target=dst)
        assert hv_res["found"] is True
        assert hv_res["bottleneck_sat"] > 0
        assert hv_res["path"][0] == src
        assert hv_res["path"][-1] == dst

    def test_path_not_found(self, prepared_db):
        db, _ = prepared_db
        pathfinder = InvestigativePathfinder(db)

        res = pathfinder.find_shortest_path("ENT-NONEXISTENT1", "ENT-NONEXISTENT2")
        assert res["found"] is False
        assert "reason" in res

    def test_candidate_paths(self, prepared_db):
        db, _ = prepared_db
        pathfinder = InvestigativePathfinder(db)
        g = pathfinder.build_graph()
        edges = list(g.edges())
        if not edges:
            pytest.skip("No entity edges in graph")

        src, dst = edges[0][0], edges[0][1]
        candidates = pathfinder.find_all_candidate_paths(source=src, target=dst, cutoff=4, limit=3)
        assert isinstance(candidates, list)
        if candidates:
            assert candidates[0]["found"] is True


class TestAutonomousInvestigator:
    """Verify autonomous case file generation and Cytoscape format."""

    def test_investigate_entity(self, prepared_db):
        db, _ = prepared_db
        agent = AutonomousInvestigator(db)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        assert entity_row is not None
        entity_id = entity_row[0]

        case = agent.investigate(
            target=entity_id,
            max_hops=3,
            decay_model="proportional",
        )

        assert case["case_id"].startswith("CASE-")
        assert case["target_id"] == entity_id
        assert case["status"] == "OPEN"
        assert len(case["bundle_hash"]) == 64
        assert "narrative_report" in case
        assert "# Forensic Investigation Case File" in case["narrative_report"]

        # Cytoscape graph validation
        sub = case["cytoscape_subgraph"]
        assert "elements" in sub
        assert "nodes" in sub["elements"]
        assert "edges" in sub["elements"]

        # Check target node attributes
        target_node = next((n for n in sub["elements"]["nodes"] if n["data"]["id"] == entity_id), None)
        assert target_node is not None
        assert target_node["data"]["is_target"] is True

        # Check DB persistence
        stored_case = db.get_investigative_case(case["case_id"])
        assert stored_case is not None
        assert stored_case["case_id"] == case["case_id"]

        cases_list = db.list_investigative_cases(limit=10)
        assert any(c["case_id"] == case["case_id"] for c in cases_list)


class TestTraceAPI:
    """Verify FastAPI endpoints for trace, pathfinding, and investigative cases."""

    def test_api_trace_and_cases_flow(self, prepared_db, monkeypatch):
        db, _ = prepared_db
        monkeypatch.setattr(settings, "DB_PATH", db.db_path)
        client = TestClient(app)

        entity_row = db.conn.execute("SELECT entity_id FROM entities ORDER BY member_count DESC LIMIT 1").fetchone()
        assert entity_row is not None
        entity_id = entity_row[0]

        # 1. POST /api/trace/run
        resp = client.post(
            "/api/trace/run",
            json={
                "target": entity_id,
                "direction": "forward",
                "decay_model": "proportional",
                "max_hops": 3,
                "min_ratio": 0.01,
            },
        )
        assert resp.status_code == 200
        trace_data = resp.json()
        assert "trace_id" in trace_data
        trace_id = trace_data["trace_id"]

        # 2. GET /api/trace/{trace_id}
        resp_get = client.get(f"/api/trace/{trace_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["trace_id"] == trace_id

        # 3. GET /api/trace/history
        resp_hist = client.get("/api/trace/history")
        assert resp_hist.status_code == 200
        assert isinstance(resp_hist.json(), list)

        # 4. POST /api/trace/path
        edges = db.conn.execute("SELECT source, target FROM graph_edges WHERE edge_type = 'member_of' LIMIT 1").fetchone()
        if edges:
            resp_path = client.post(
                "/api/trace/path",
                json={
                    "source": edges[0],
                    "target": edges[1],
                    "strategy": "shortest",
                },
            )
            assert resp_path.status_code == 200

        # 5. POST /api/trace/investigate
        resp_inv = client.post(
            "/api/trace/investigate",
            json={
                "target": entity_id,
                "max_hops": 3,
                "decay_model": "proportional",
                "title": "API Test Case",
            },
        )
        assert resp_inv.status_code == 200
        case_data = resp_inv.json()
        assert "case_id" in case_data
        case_id = case_data["case_id"]

        # 6. GET /api/trace/cases
        resp_cases = client.get("/api/trace/cases")
        assert resp_cases.status_code == 200
        assert any(c["case_id"] == case_id for c in resp_cases.json())

        # 7. GET /api/trace/cases/{case_id}
        resp_single_case = client.get(f"/api/trace/cases/{case_id}")
        assert resp_single_case.status_code == 200
        assert resp_single_case.json()["case_id"] == case_id
