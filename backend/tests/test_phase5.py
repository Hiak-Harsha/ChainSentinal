"""Unit tests for Phase 5 — Features, Models, Conformal Prediction, Explainability & Prioritization."""

from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from chainsentinel.alerts.alert_generator import AlertGenerator
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.explain.explainer import ForensicExplainer
from chainsentinel.features.extractor import FEATURE_NAMES, MultimodalFeatureExtractor
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.models.conformal import ConformalPredictor
from chainsentinel.models.pipeline import ModelPipeline
from chainsentinel.models.supervised import SupervisedTypologyClassifier
from chainsentinel.models.unsupervised import IsolationForestAnomalyDetector
from chainsentinel.storage.db import DatabaseManager

DATA_DIR = Path(__file__).parent.parent / "data" / "cli_test"
TEST_JSON = str(DATA_DIR / "observations.json")
GROUND_TRUTH = str(DATA_DIR / "ground_truth.json")


@pytest.fixture(scope="module")
def prepared_db(tmp_path_factory):
    """Fixture providing a temporary DuckDB database fully ingested, clustered, and correlated."""
    tmp_dir = tmp_path_factory.mktemp("phase5_db")
    db_file = tmp_dir / "test_phase5.duckdb"
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


class TestFeatureExtractor:
    """Verify multimodal feature extraction across financial, graph, temporal, and network domains."""

    def test_extract_all_35_features(self, prepared_db):
        db, _ = prepared_db
        extractor = MultimodalFeatureExtractor(db)

        # Query a sample entity
        row = db.conn.execute("SELECT entity_id FROM entities LIMIT 1").fetchone()
        assert row is not None
        entity_id = row[0]

        feats = extractor.extract_entity_features(entity_id)
        assert len(feats) == len(FEATURE_NAMES)
        assert len(FEATURE_NAMES) == 35

        # Verify no NaN or Inf
        for fn, val in feats.items():
            assert val is not None
            assert isinstance(val, (int, float))
            assert not (val != val)  # not NaN

    def test_batch_extraction_and_persistence(self, prepared_db):
        db, _ = prepared_db
        extractor = MultimodalFeatureExtractor(db)
        saved = extractor.extract_all_and_save()
        assert len(saved) > 0

        # Verify stored in DuckDB table
        stored = db.list_all_entity_features()
        assert len(stored) == len(saved)
        assert "entity_id" in stored[0]
        assert "total_volume_sat" in stored[0]["features"]


class TestSupervisedClassifier:
    """Verify supervised multi-class model training, evaluation, and serialization."""

    def test_train_and_predict(self, prepared_db):
        db, tmp_dir = prepared_db
        extractor = MultimodalFeatureExtractor(db)
        features_data = extractor.extract_all_and_save()
        X = [f["features"] for f in features_data]
        y = ["T1_PEEL_CHAIN" if i % 2 == 0 else "LEGITIMATE" for i in range(len(X))]

        clf = SupervisedTypologyClassifier(random_state=42)
        clf.fit(X, y)

        assert clf.is_fitted
        assert len(clf.classes_) == 2

        # Predict proba
        probs = clf.predict_proba(X)
        assert probs.shape == (len(X), 2)
        for p in probs:
            assert abs(sum(p) - 1.0) < 1e-4

        # Predict top-k
        top_k = clf.predict_top_k(X, k=2)
        assert len(top_k) == len(X)
        assert len(top_k[0]) == 2

        # Serialization
        model_file = tmp_dir / "test_clf.pkl"
        clf.save(model_file)
        loaded = SupervisedTypologyClassifier.load(model_file)
        assert loaded.is_fitted
        assert loaded.classes_ == clf.classes_


class TestUnsupervisedAnomaly:
    """Verify Isolation Forest anomaly scoring and hold-out detection."""

    def test_anomaly_scoring_bounds(self, prepared_db):
        db, tmp_dir = prepared_db
        extractor = MultimodalFeatureExtractor(db)
        features_data = extractor.extract_all_and_save()
        X = [f["features"] for f in features_data]

        detector = IsolationForestAnomalyDetector(contamination=0.15, random_state=42)
        detector.fit(X)
        assert detector.is_fitted

        scores = detector.score_samples(X)
        assert len(scores) == len(X)
        for s in scores:
            assert 0.0 <= s <= 1.0

        # Save and load
        anom_file = tmp_dir / "test_anom.pkl"
        detector.save(anom_file)
        loaded = IsolationForestAnomalyDetector.load(anom_file)
        assert loaded.is_fitted


class TestConformalPrediction:
    """Verify split conformal prediction bounds, prediction set generation, and reliability grades."""

    def test_conformal_coverage_and_grades(self, prepared_db):
        db, tmp_dir = prepared_db
        extractor = MultimodalFeatureExtractor(db)
        features_data = extractor.extract_all_and_save()
        X = [f["features"] for f in features_data]
        y = ["T1_PEEL_CHAIN" if i % 2 == 0 else "LEGITIMATE" for i in range(len(X))]

        clf = SupervisedTypologyClassifier(random_state=42)
        clf.fit(X, y)
        probs = clf.predict_proba(X)

        conformal = ConformalPredictor(default_alpha=0.10)
        conformal.calibrate(probs, y, clf.classes_)
        assert conformal.is_calibrated

        sets = conformal.predict_sets(probs, alpha=0.10)
        assert len(sets) == len(X)
        for s in sets:
            assert len(s["conformal_set"]) >= 1
            assert s["grade"] in ("A", "B", "C")
            assert 0.0 <= s["calibrated_p"] <= 1.0

        # Save and load
        conf_file = tmp_dir / "test_conf.pkl"
        conformal.save(conf_file)
        loaded = ConformalPredictor.load(conf_file)
        assert loaded.is_calibrated


class TestForensicExplainer:
    """Verify TreeSHAP feature attributions, peer percentiles, and narrative explanations."""

    def test_explainer_output_format(self, prepared_db):
        db, _ = prepared_db
        extractor = MultimodalFeatureExtractor(db)
        features_data = extractor.extract_all_and_save()
        X = [f["features"] for f in features_data]
        y = ["T1_PEEL_CHAIN" if i % 2 == 0 else "LEGITIMATE" for i in range(len(X))]

        clf = SupervisedTypologyClassifier(random_state=42)
        clf.fit(X, y)

        explainer = ForensicExplainer(clf, X)
        percentiles = explainer.compute_peer_percentiles(X[0])
        for fn, pctl in percentiles.items():
            assert 0.0 <= pctl <= 100.0

        reasons = explainer.explain_entity(
            entity_id="ENT-test",
            feature_dict=X[0],
            predicted_class="T1_PEEL_CHAIN",
            class_prob=0.92,
            top_n=3,
        )
        assert len(reasons) == 3
        for r in reasons:
            assert "feature" in r
            assert "value" in r
            assert "peer_percentile" in r
            assert "shap" in r
            assert "text" in r
            assert isinstance(r["text"], str) and len(r["text"]) > 5


class TestAlertGenerationAndContract:
    """Verify alert synthesis, composite risk score, and Section 7 API contract schema."""

    def test_alert_contract_schema(self, prepared_db):
        db, _ = prepared_db
        alert_gen = AlertGenerator(db)

        # Query real entity
        row = db.conn.execute("SELECT entity_id FROM entities LIMIT 1").fetchone()
        assert row is not None
        eid = row[0]

        reasons = [
            {
                "feature": "peel_chain_depth",
                "value": 14,
                "peer_percentile": 99.4,
                "shap": 0.38,
                "text": "Peel chain depth of 14 exceeds 99.4% of entities.",
            }
        ]

        alert = alert_gen.build_alert(
            entity_id=eid,
            predicted_class="T1_PEEL_CHAIN",
            calibrated_p=0.92,
            anomaly_score=0.85,
            volume_sat=500000000,
            conformal_set=["T1_PEEL_CHAIN"],
            grade="A",
            reasons=reasons,
        )

        # Section 7 Contract Assertions
        assert alert["alert_id"].startswith("ALT-")
        assert alert["entity_id"] == eid
        assert 0.0 <= alert["priority"] <= 1.0
        assert 0.0 <= alert["risk_score"] <= 1.0
        assert alert["status"] == "NEW"
        assert alert["created_at"] > 0

        # Confidence sub-schema
        assert alert["confidence"]["calibrated_p"] == 0.92
        assert alert["confidence"]["conformal_set"] == ["T1_PEEL_CHAIN"]
        assert alert["confidence"]["grade"] == "A"

        # Typologies sub-schema
        assert len(alert["typologies"]) >= 1
        assert alert["typologies"][0]["name"] == "T1_PEEL_CHAIN"
        assert "txids" in alert["typologies"][0]

        # Attribution sub-schema
        assert "ip" in alert["attribution"]
        assert "asn" in alert["attribution"]
        assert "country" in alert["attribution"]
        assert "confidence" in alert["attribution"]
        assert "basis" in alert["attribution"]

        # Evidence sub-schema
        assert "txids" in alert["evidence"]
        assert "ips" in alert["evidence"]
        assert "subgraph_ref" in alert["evidence"]
        assert "bundle_hash" in alert["evidence"]
        assert len(alert["evidence"]["bundle_hash"]) == 64  # SHA-256


class TestModelPipelineAndAPI:
    """Verify end-to-end pipeline training, detection, and FastAPI endpoints."""

    def test_pipeline_train_and_detect(self, prepared_db):
        db, tmp_dir = prepared_db
        pipeline = ModelPipeline(db=db, model_dir=tmp_dir / "models")
        report = pipeline.train(ground_truth_path=GROUND_TRUTH)

        assert report["status"] == "success"
        assert report["entities_trained"] > 0
        assert report["metrics"]["accuracy"] >= 0.70

        # Detect
        alerts = pipeline.detect(min_risk_score=0.20, limit=20)
        assert len(alerts) > 0
        assert alerts[0]["priority"] >= alerts[-1]["priority"]

        # Check DuckDB persistence
        db_alerts = db.list_alerts(limit=20)
        assert len(db_alerts) > 0

    def test_holdout_typology_experiment(self, prepared_db):
        db, tmp_dir = prepared_db
        pipeline = ModelPipeline(db=db, model_dir=tmp_dir / "models")
        holdout_res = pipeline.evaluate_holdout(ground_truth_path=GROUND_TRUTH)

        assert "legitimate_anomaly_mean" in holdout_res
        assert "holdout_anomaly_mean" in holdout_res
        assert "anomaly_separation_delta" in holdout_res

    def test_fastapi_endpoints(self, prepared_db):
        db, tmp_dir = prepared_db
        # Set settings DB_PATH to this temporary test database
        old_db_path = settings.DB_PATH
        old_models_dir = settings.MODELS_DIR
        try:
            settings.DB_PATH = Path(db.db_path)
            settings.MODELS_DIR = tmp_dir / "api_models"

            client = TestClient(app)

            # 1. Models train
            res_train = client.post("/api/models/train", json={"ground_truth_path": GROUND_TRUTH})
            assert res_train.status_code == 200
            assert res_train.json()["status"] == "success"

            # 2. Models detect
            res_detect = client.post("/api/models/detect", json={"min_risk": 0.20, "limit": 25})
            assert res_detect.status_code == 200
            alerts = res_detect.json()["alerts"]
            assert len(alerts) > 0

            # 3. Models lab diagnostics
            res_lab = client.get("/api/models/lab")
            assert res_lab.status_code == 200
            assert res_lab.json()["status"] == "ready"

            # 4. List alerts
            res_alerts = client.get("/api/alerts?min_priority=0.0&limit=10")
            assert res_alerts.status_code == 200
            alert_list = res_alerts.json()
            assert len(alert_list) > 0
            sample_id = alert_list[0]["alert_id"]

            # 5. Get alert detail
            res_detail = client.get(f"/api/alerts/{sample_id}")
            assert res_detail.status_code == 200
            assert res_detail.json()["alert_id"] == sample_id

            # 6. Update alert status
            res_status = client.post(
                f"/api/alerts/{sample_id}/status", json={"status": "INVESTIGATING"}
            )
            assert res_status.status_code == 200
            assert res_status.json()["current_status"] == "INVESTIGATING"

        finally:
            settings.DB_PATH = old_db_path
            settings.MODELS_DIR = old_models_dir
