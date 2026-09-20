"""Unit tests for Phase 4 — Network⇄Blockchain Correlation Engine."""

from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from app.main import app
from chainsentinel.correlate.association_matrix import AssociationMatrix
from chainsentinel.correlate.behavioral_signatures import BehavioralSignatureExtractor
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.correlate.origin_estimator import OriginEstimate, OriginEstimator
from chainsentinel.correlate.timing_correlator import TimingCorrelator
from chainsentinel.eval.correlate_eval import CorrelateEvaluator
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.storage.db import DatabaseManager

DATA_DIR = Path(__file__).parent.parent / "data" / "cli_test"
TEST_JSON = str(DATA_DIR / "observations.json")
GROUND_TRUTH = str(DATA_DIR / "ground_truth.json")


class TestOriginEstimator:
    """Verify first-seen estimation, diffusion gap confidence, and anonymizer penalty."""

    def test_earliest_timestamp_selected(self):
        estimator = OriginEstimator()
        observations = [
            {"src_ip": "1.1.1.1", "ts": 105.0, "is_anonymizer": False, "sensor_id": "s1"},
            {"src_ip": "2.2.2.2", "ts": 100.0, "is_anonymizer": False, "sensor_id": "s2"},  # Earliest
            {"src_ip": "3.3.3.3", "ts": 103.0, "is_anonymizer": False, "sensor_id": "s3"},
        ]
        est = estimator.estimate_origin("tx_1", observations)
        assert est is not None
        assert est.origin_ip == "2.2.2.2"
        assert est.first_seen_ts == 100.0
        assert est.delta_t == 3.0  # 103.0 - 100.0

    def test_confidence_growth_with_delta_t(self):
        estimator = OriginEstimator(tau=2.0)
        # Small gap (fast relay across peers)
        obs_small_gap = [
            {"src_ip": "1.1.1.1", "ts": 100.0, "is_anonymizer": False, "sensor_id": "s1"},
            {"src_ip": "2.2.2.2", "ts": 100.1, "is_anonymizer": False, "sensor_id": "s2"},
        ]
        est_small = estimator.estimate_origin("tx_small", obs_small_gap)

        # Large gap (strong head start)
        obs_large_gap = [
            {"src_ip": "1.1.1.1", "ts": 100.0, "is_anonymizer": False, "sensor_id": "s1"},
            {"src_ip": "2.2.2.2", "ts": 106.0, "is_anonymizer": False, "sensor_id": "s2"},
        ]
        est_large = estimator.estimate_origin("tx_large", obs_large_gap)

        assert est_small is not None and est_large is not None
        assert est_large.confidence > est_small.confidence

    def test_anonymizer_penalty(self):
        estimator = OriginEstimator(anon_penalty=0.35)
        obs_clean = [
            {"src_ip": "1.1.1.1", "ts": 100.0, "is_anonymizer": False, "sensor_id": "s1"},
            {"src_ip": "2.2.2.2", "ts": 105.0, "is_anonymizer": False, "sensor_id": "s2"},
        ]
        obs_tor = [
            {"src_ip": "1.1.1.1", "ts": 100.0, "is_anonymizer": True, "sensor_id": "s1"},
            {"src_ip": "2.2.2.2", "ts": 105.0, "is_anonymizer": False, "sensor_id": "s2"},
        ]
        est_clean = estimator.estimate_origin("tx_clean", obs_clean)
        est_tor = estimator.estimate_origin("tx_tor", obs_tor)

        assert est_clean is not None and est_tor is not None
        assert est_tor.is_anonymizer is True
        assert est_tor.confidence < est_clean.confidence * 0.5


class TestHubRelayDebiasing:
    """Verify TF-IDF down-weights omnipresent public relays and isolates specific origin IPs."""

    def test_omnipresent_relay_downweighted(self):
        matrix = AssociationMatrix()
        # 5 entities
        # "10.0.0.99" is a public hub relay seen across all 5 entities
        # "198.51.100.1" is an operator IP seen ONLY in entity_1

        origin_estimates = {
            "tx_1": OriginEstimate("tx_1", "198.51.100.1", 0.9, 3.0, False, 3, 100.0),
            "tx_2": OriginEstimate("tx_2", "198.51.100.1", 0.9, 3.0, False, 3, 110.0),
            "tx_3": OriginEstimate("tx_3", "10.0.0.99", 0.9, 3.0, False, 3, 120.0),
            # Other entities also first-see from 10.0.0.99
            "tx_e2": OriginEstimate("tx_e2", "10.0.0.99", 0.9, 3.0, False, 3, 200.0),
            "tx_e3": OriginEstimate("tx_e3", "10.0.0.99", 0.9, 3.0, False, 3, 300.0),
            "tx_e4": OriginEstimate("tx_e4", "10.0.0.99", 0.9, 3.0, False, 3, 400.0),
            "tx_e5": OriginEstimate("tx_e5", "10.0.0.99", 0.9, 3.0, False, 3, 500.0),
        }

        entity_txids = {
            "ENT_TARGET": ["tx_1", "tx_2", "tx_3"],
            "ENT_2": ["tx_e2"],
            "ENT_3": ["tx_e3"],
            "ENT_4": ["tx_e4"],
            "ENT_5": ["tx_e5"],
        }

        associations = matrix.compute_associations(entity_txids, origin_estimates)
        target_ips = associations["ENT_TARGET"]

        assert len(target_ips) >= 2
        # Top-1 IP must be the specific operator IP, NOT the omnipresent relay
        top_ip = target_ips[0]["ip"]
        assert top_ip == "198.51.100.1"
        assert target_ips[0]["score"] > target_ips[1]["score"]
        assert target_ips[0]["posterior_prob"] > target_ips[1]["posterior_prob"]


class TestTimingPermutationTest:
    """Verify statistical significance testing for same-operator links."""

    def test_synchronized_broadcasting_significant(self):
        correlator = TimingCorrelator(time_window_sec=60.0, num_permutations=100)

        # Entity A and Entity B broadcast 4 pairs of transactions simultaneously from 192.0.2.1
        origin_estimates = {
            "tx_a1": OriginEstimate("tx_a1", "192.0.2.1", 0.9, 2.0, False, 2, 1000.0),
            "tx_b1": OriginEstimate("tx_b1", "192.0.2.1", 0.9, 2.0, False, 2, 1005.0),
            "tx_a2": OriginEstimate("tx_a2", "192.0.2.1", 0.9, 2.0, False, 2, 5000.0),
            "tx_b2": OriginEstimate("tx_b2", "192.0.2.1", 0.9, 2.0, False, 2, 5010.0),
            "tx_a3": OriginEstimate("tx_a3", "192.0.2.1", 0.9, 2.0, False, 2, 9000.0),
            "tx_b3": OriginEstimate("tx_b3", "192.0.2.1", 0.9, 2.0, False, 2, 9015.0),
        }

        entity_txids = {
            "ENT_A": ["tx_a1", "tx_a2", "tx_a3"],
            "ENT_B": ["tx_b1", "tx_b2", "tx_b3"],
        }

        links = correlator.find_operator_links(entity_txids, origin_estimates)
        assert len(links) == 1
        link = links[0]
        assert link.shared_ip == "192.0.2.1"
        assert link.co_occurrences >= 3
        assert link.p_value <= 0.05  # Statistically significant

    def test_independent_broadcasting_not_significant(self):
        correlator = TimingCorrelator(time_window_sec=60.0, num_permutations=100, p_value_threshold=0.05)

        # Transactions hours apart
        origin_estimates = {
            "tx_a1": OriginEstimate("tx_a1", "192.0.2.1", 0.9, 2.0, False, 2, 1000.0),
            "tx_b1": OriginEstimate("tx_b1", "192.0.2.1", 0.9, 2.0, False, 2, 10000.0),
            "tx_a2": OriginEstimate("tx_a2", "192.0.2.1", 0.9, 2.0, False, 2, 20000.0),
            "tx_b2": OriginEstimate("tx_b2", "192.0.2.1", 0.9, 2.0, False, 2, 30000.0),
        }

        entity_txids = {
            "ENT_A": ["tx_a1", "tx_a2"],
            "ENT_B": ["tx_b1", "tx_b2"],
        }

        links = correlator.find_operator_links(entity_txids, origin_estimates)
        # No links found or p_value not significant
        assert len(links) == 0


class TestBehavioralSignatures:
    """Verify behavioral network signature extraction."""

    def test_non_standard_ports_and_entropy(self):
        # 10 observations with non-standard port 18333
        observations = [
            {"src_ip": "1.1.1.1", "src_port": 18333, "dst_port": 18333, "src_asn": "AS13335", "is_anonymizer": False, "ts": 1704067200.0 + (i * 3600), "src_country": "US"}
            for i in range(10)
        ]

        sig = BehavioralSignatureExtractor.extract(
            entity_id="ENT_TEST",
            observations=observations,
            tx_count=10,
        )

        assert sig.non_standard_port_ratio == 1.0
        assert sig.asn_count == 1
        assert sig.anonymizer_ratio == 0.0
        assert sig.circadian_entropy > 0.0


class TestCorrelateEndToEndVsGroundTruth:
    """Verify full correlation pipeline and IP attribution accuracy vs ground truth."""

    def test_correlation_and_eval_metrics(self):
        db = DatabaseManager(":memory:")
        pipeline = IngestPipeline(db=db)
        pipeline.run(TEST_JSON)

        # Cluster first to get address_entity_map
        resolver = EntityResolver(db=db, change_threshold=0.65)
        resolver.run()

        # Run correlation engine
        engine = CorrelationEngine(db=db, time_window_sec=60.0)
        summary, attributions = engine.run()

        assert summary.total_tx_analyzed > 1000
        assert summary.total_entities_analyzed > 100
        assert summary.total_origin_estimates > 1000
        assert summary.duration_seconds < 10.0

        # Evaluate against ground truth
        aem_res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        aem_map = dict(aem_res)
        metrics = CorrelateEvaluator.evaluate_attribution(
            attributions=attributions,
            ground_truth_path=GROUND_TRUTH,
            address_entity_map=aem_map,
        )

        assert metrics["total_entities_evaluated"] > 50
        # Check overall IP attribution accuracy
        assert metrics["overall_top1_accuracy"] >= 0.40
        assert metrics["overall_top3_accuracy"] >= 0.50

        # Verify level 0 (clean baseline) has recorded accuracy
        lvl0 = metrics["by_obfuscation_level"].get("level_0")
        if lvl0 and lvl0["total_entities"] > 0:
            assert lvl0["top1_accuracy"] >= 0.40


class TestCorrelateApiEndpoints:
    """Verify FastAPI correlation endpoints."""

    def test_api_workflow(self):
        from app.core.security import _ensure_api_key
        client = TestClient(app, headers={"X-API-Key": _ensure_api_key()})

        # 1. Ingest & cluster on DB
        from app.core.config import settings
        db = DatabaseManager(settings.DB_PATH)
        pipeline = IngestPipeline(db=db)
        pipeline.run(TEST_JSON)

        resolver = EntityResolver(db=db, change_threshold=0.65)
        resolver.run()

        # 2. Trigger correlation run endpoint
        res = client.post("/api/correlate/run", json={
            "time_window_sec": 60.0,
            "p_value_thresh": 0.05,
            "ground_truth_path": GROUND_TRUTH,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert "summary" in data
        assert "eval_metrics" in data
        assert data["eval_metrics"]["overall_top1_accuracy"] >= 0.40

        # 3. Fetch top entity attribution
        ent_rows = db.conn.execute("SELECT DISTINCT entity_id FROM ip_entity_links LIMIT 1").fetchall()
        assert len(ent_rows) > 0
        sample_ent = ent_rows[0][0]

        res_attr = client.get(f"/api/correlate/entity/{sample_ent}")
        assert res_attr.status_code == 200
        attributions = res_attr.json()
        assert len(attributions) > 0
        assert "ip" in attributions[0]
        assert "posterior_prob" in attributions[0]

        # 4. Fetch signatures endpoint
        res_sig = client.get(f"/api/correlate/signatures/{sample_ent}")
        assert res_sig.status_code == 200
        sig = res_sig.json()
        assert "circadian_entropy" in sig
        assert "ip_churn_rate" in sig

        # 5. Operator links endpoint
        res_links = client.get("/api/correlate/operator-links")
        assert res_links.status_code == 200
        assert isinstance(res_links.json(), list)

        # 6. Metrics endpoint
        res_m = client.get(f"/api/correlate/metrics?ground_truth_path={GROUND_TRUTH}")
        assert res_m.status_code == 200
        m = res_m.json()
        assert m["overall_top1_accuracy"] >= 0.40
