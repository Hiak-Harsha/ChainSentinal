"""Unit tests for Phase 3 — Graph & Entity Resolution."""

from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from app.main import app
from chainsentinel.eval.cluster_eval import ClusterEvaluator
from chainsentinel.graph.change_detector import ChangeAddressDetector
from chainsentinel.graph.coinjoin_detector import CoinJoinDetector
from chainsentinel.graph.entity_classifier import EntityClassifier
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.graph.hetero_graph import HeteroGraph
from chainsentinel.graph.union_find import DisjointSet
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.storage.db import DatabaseManager

DATA_DIR = Path(__file__).parent.parent / "data" / "cli_test"
TEST_JSON = str(DATA_DIR / "observations.json")
GROUND_TRUTH = str(DATA_DIR / "ground_truth.json")


class TestUnionFind:
    """Test DisjointSet correctness, rank merging, and path compression."""

    def test_isolated_elements(self):
        dsu: DisjointSet[str] = DisjointSet()
        dsu.add("a")
        dsu.add("b")
        assert len(dsu) == 2
        assert not dsu.connected("a", "b")
        assert dsu.count_components() == 2

    def test_union_and_connected(self):
        dsu: DisjointSet[str] = DisjointSet()
        assert dsu.union("a", "b") is True
        assert dsu.union("b", "c") is True
        assert dsu.union("a", "c") is False  # Already in same set
        assert dsu.connected("a", "c") is True
        assert dsu.component_size("a") == 3
        assert dsu.count_components() == 1

    def test_multiple_disjoint_components(self):
        dsu: DisjointSet[str] = DisjointSet()
        dsu.union("a1", "a2")
        dsu.union("a2", "a3")
        dsu.union("b1", "b2")

        components = dsu.get_components()
        assert len(components) == 2
        sizes = sorted([len(c) for c in components.values()])
        assert sizes == [2, 3]


class TestCoinJoinDetector:
    """Verify identification of multi-party equal-output CoinJoin transactions."""

    def test_coinjoin_detected(self):
        detector = CoinJoinDetector(min_equal_outputs=3)
        inputs = [
            {"address": "bc1qa", "amount": 5010000},
            {"address": "bc1qb", "amount": 5012000},
            {"address": "bc1qc", "amount": 5009000},
        ]
        outputs = [
            {"address": "bc1q_mix1", "amount": 5000000},
            {"address": "bc1q_mix2", "amount": 5000000},
            {"address": "bc1q_mix3", "amount": 5000000},
            {"address": "bc1q_chg1", "amount": 8000},
            {"address": "bc1q_chg2", "amount": 10000},
        ]
        is_cj, conf, details = detector.analyze(inputs, outputs)
        assert is_cj is True
        assert conf >= 0.75
        assert details["equal_amount_sats"] == 5000000
        assert details["equal_count"] == 3

    def test_normal_payment_not_coinjoin(self):
        detector = CoinJoinDetector(min_equal_outputs=3)
        inputs = [{"address": "bc1qa", "amount": 10000000}]
        outputs = [
            {"address": "bc1q_merchant", "amount": 2500000},
            {"address": "bc1q_change", "amount": 7490000},
        ]
        is_cj, conf, _ = detector.analyze(inputs, outputs)
        assert is_cj is False
        assert conf == 0.0


class TestCoinJoinAntiCollapse:
    """CRITICAL TEST: Verify CoinJoin exclusion prevents mega-cluster collapse."""

    def test_two_entities_not_merged_by_coinjoin(self):
        db = DatabaseManager(":memory:")

        # Entity A: addrs A1, A2
        # Entity B: addrs B1, B2
        # Tx 1 (CIOH for A): A1 + A2 -> outA
        # Tx 2 (CIOH for B): B1 + B2 -> outB
        # Tx 3 (CoinJoin): A1 + B1 -> [5M sats, 5M sats, 5M sats, changeA, changeB]

        txs = [
            {"txid": "tx_a", "first_seen_ts": 100.0, "fee_sat": 1000, "vsize": 200, "fee_rate": 5.0, "n_in": 2, "n_out": 1, "total_in": 100000, "total_out": 99000},
            {"txid": "tx_b", "first_seen_ts": 110.0, "fee_sat": 1000, "vsize": 200, "fee_rate": 5.0, "n_in": 2, "n_out": 1, "total_in": 100000, "total_out": 99000},
            {"txid": "tx_cj", "first_seen_ts": 120.0, "fee_sat": 3000, "vsize": 400, "fee_rate": 7.5, "n_in": 2, "n_out": 4, "total_in": 15000000, "total_out": 14997000},
        ]
        db.insert_transactions_batch(txs)

        inputs = [
            {"txid": "tx_a", "idx": 0, "address": "bc1q_A1", "amount": 50000},
            {"txid": "tx_a", "idx": 1, "address": "bc1q_A2", "amount": 50000},
            {"txid": "tx_b", "idx": 0, "address": "bc1q_B1", "amount": 50000},
            {"txid": "tx_b", "idx": 1, "address": "bc1q_B2", "amount": 50000},
            {"txid": "tx_cj", "idx": 0, "address": "bc1q_A1", "amount": 7500000},
            {"txid": "tx_cj", "idx": 1, "address": "bc1q_B1", "amount": 7500000},
        ]
        db.insert_inputs_batch(inputs)

        outputs = [
            {"txid": "tx_a", "idx": 0, "address": "bc1q_outA", "amount": 99000, "script_type": "p2wpkh"},
            {"txid": "tx_b", "idx": 0, "address": "bc1q_outB", "amount": 99000, "script_type": "p2wpkh"},
            {"txid": "tx_cj", "idx": 0, "address": "bc1q_mix1", "amount": 5000000, "script_type": "p2wpkh"},
            {"txid": "tx_cj", "idx": 1, "address": "bc1q_mix2", "amount": 5000000, "script_type": "p2wpkh"},
            {"txid": "tx_cj", "idx": 2, "address": "bc1q_mix3", "amount": 5000000, "script_type": "p2wpkh"},
            {"txid": "tx_cj", "idx": 3, "address": "bc1q_chg", "amount": 4997000, "script_type": "p2wpkh"},
        ]
        db.insert_outputs_batch(outputs)

        resolver = EntityResolver(db=db, change_threshold=0.8, min_coinjoin_outputs=3)
        summary, _ = resolver.run()

        assert summary.coinjoin_txs_excluded >= 1

        # Check entity assignment for A1, A2 vs B1, B2
        res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        ent_map = dict(res)

        ent_a1 = ent_map["bc1q_A1"]
        ent_a2 = ent_map["bc1q_A2"]
        ent_b1 = ent_map["bc1q_B1"]
        ent_b2 = ent_map["bc1q_B2"]

        # A1 and A2 must be in the same entity
        assert ent_a1 == ent_a2
        # B1 and B2 must be in the same entity
        assert ent_b1 == ent_b2
        # Entity A and Entity B must NOT be merged (NO CLUSTER COLLAPSE)
        assert ent_a1 != ent_b1


class TestChangeAddressDetector:
    """Verify change detection heuristics."""

    def test_round_payment_and_irregular_change(self):
        detector = ChangeAddressDetector(confidence_threshold=0.6)
        inputs = [{"address": "bc1q_sender", "amount": 10000000, "script_type": "p2wpkh"}]
        outputs = [
            {"address": "1LegacyPayee", "amount": 5000000, "script_type": "p2pkh"},  # 0.05 BTC round
            {"address": "bc1q_freshChange", "amount": 4998000, "script_type": "p2wpkh"},  # irregular change
        ]
        chg_addr, conf, details = detector.detect_change(inputs, outputs)
        assert chg_addr == "bc1q_freshChange"
        assert conf >= 0.6
        assert "script_type_match" in details["signals"]
        assert "non_round_sats_vs_round_payment" in details["signals"]

    def test_address_reuse_change(self):
        detector = ChangeAddressDetector()
        inputs = [{"address": "bc1q_sender", "amount": 5000000}]
        outputs = [
            {"address": "bc1q_dest", "amount": 3000000},
            {"address": "bc1q_sender", "amount": 1999000},  # sent back to sender
        ]
        chg_addr, conf, _ = detector.detect_change(inputs, outputs)
        assert chg_addr == "bc1q_sender"
        assert conf >= 0.90


class TestEntityClassifier:
    """Test entity behavioral typing."""

    def test_classify_exchange(self):
        addrs = [f"addr_{i}" for i in range(30)]
        out_txs = [{"outputs": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} for _ in range(20)]
        etype, conf, _ = EntityClassifier.classify(
            member_addrs=addrs,
            incoming_txs=[],
            outgoing_txs=out_txs,
            total_received=10_000_000_000,
            total_sent=10_000_000_000,
        )
        assert etype == "EXCHANGE"
        assert conf >= 0.7

    def test_classify_mixer(self):
        etype, conf, _ = EntityClassifier.classify(
            member_addrs=["addr_m1", "addr_m2"],
            incoming_txs=[{}] * 5,
            outgoing_txs=[{}] * 5,
            total_received=100_000_000,
            total_sent=100_000_000,
            coinjoin_tx_count=4,
        )
        assert etype == "MIXER"
        assert conf >= 0.7

    def test_classify_individual(self):
        etype, conf, _ = EntityClassifier.classify(
            member_addrs=["addr_user"],
            incoming_txs=[{}],
            outgoing_txs=[{}],
            total_received=10_000_000,
            total_sent=9_990_000,
        )
        assert etype == "INDIVIDUAL"
        assert conf >= 0.8


class TestHeteroGraph:
    """Verify heterogeneous graph structure and subgraph queries."""

    def test_graph_and_ego_subgraph(self):
        graph = HeteroGraph()
        graph.add_node("ENT_1", "Entity", "Entity 1")
        graph.add_node("addr_1", "Address", "Address 1")
        graph.add_node("tx_1", "Transaction", "TX 1")
        graph.add_node("192.168.1.1", "IP", "IP 1")

        graph.add_edge("addr_1", "ENT_1", "member_of")
        graph.add_edge("addr_1", "tx_1", "spends")
        graph.add_edge("tx_1", "192.168.1.1", "observed_from")

        subgraph = graph.get_ego_subgraph(center_id="ENT_1", hops=2)
        assert subgraph["center"] == "ENT_1"
        assert subgraph["total_nodes"] >= 3
        assert subgraph["total_edges"] >= 2
        # Check node types
        node_types = {n["type"] for n in subgraph["nodes"]}
        assert "Entity" in node_types
        assert "Address" in node_types


class TestGroundTruthEvaluation:
    """Verify clustering evaluation vs ground truth on synthetic test dataset."""

    def test_clustering_and_ground_truth_metrics(self):
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)
        # Ingest test dataset
        pipeline.run(TEST_JSON)

        # Run Entity Resolution
        resolver = EntityResolver(db=db, change_threshold=0.75, min_coinjoin_outputs=3)
        summary, graph = resolver.run()

        assert summary.total_addresses > 1000
        assert summary.total_entities > 100
        assert summary.coinjoin_txs_excluded > 0
        assert summary.duration_seconds < 10.0

        # Load ground truth and evaluate
        gt_map = ClusterEvaluator.load_ground_truth_map(GROUND_TRUTH)
        res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        disc_map = dict(res)

        metrics = ClusterEvaluator.evaluate(disc_map, gt_map)
        assert metrics["evaluated_addresses"] >= 900
        # Check high clustering precision (zero or near-zero false merges)
        assert metrics["pairwise_precision"] >= 0.90
        # Check high NMI and non-negative ARI
        assert metrics["normalized_mutual_info"] >= 0.70
        assert metrics["adjusted_rand_index"] >= 0.0


class TestGraphApiEndpoints:
    """Verify FastAPI graph and entity endpoints."""

    def test_api_workflow(self):
        from app.core.security import _ensure_api_key
        client = TestClient(app, headers={"X-API-Key": _ensure_api_key()})

        # 1. Ingest dataset first via direct pipeline or db
        from app.core.config import settings
        db = DatabaseManager(settings.DB_PATH)
        pipeline = IngestPipeline(db=db)
        pipeline.run(TEST_JSON)

        # 2. Trigger clustering endpoint
        res = client.post("/api/graph/cluster", json={
            "change_threshold": 0.65,
            "min_coinjoin_outputs": 3,
            "ground_truth_path": GROUND_TRUTH,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert "summary" in data
        assert "eval_metrics" in data
        assert data["eval_metrics"]["pairwise_precision"] >= 0.90
        assert data["eval_metrics"]["normalized_mutual_info"] >= 0.70

        # 3. List entities endpoint
        res_list = client.get("/api/graph/entities?limit=10")
        assert res_list.status_code == 200
        entities = res_list.json()
        assert len(entities) > 0
        top_entity_id = entities[0]["entity_id"]

        # 4. Entity detail endpoint
        res_detail = client.get(f"/api/graph/entities/{top_entity_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["entity_id"] == top_entity_id
        assert "addresses" in detail
        assert len(detail["addresses"]) > 0

        # 5. Ego-subgraph endpoint
        res_sub = client.get(f"/api/graph/subgraph?center_id={top_entity_id}&hops=2")
        assert res_sub.status_code == 200
        subgraph = res_sub.json()
        assert subgraph["center"] == top_entity_id
        assert len(subgraph["nodes"]) > 0

        # 6. Metrics endpoint
        res_metrics = client.get(f"/api/graph/metrics?ground_truth_path={GROUND_TRUTH}")
        assert res_metrics.status_code == 200
        m = res_metrics.json()
        assert m["pairwise_precision"] >= 0.90
        assert m["normalized_mutual_info"] >= 0.70
        assert m["adjusted_rand_index"] >= 0.0
