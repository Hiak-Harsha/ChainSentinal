"""Unit tests for Phase 8 — Evaluation reporter, benchmarks, and CLI reporting."""

from __future__ import annotations

from pathlib import Path
import pytest
from click.testing import CliRunner

from chainsentinel.cli import cli
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.eval.reporter import ForensicReporter
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.ingest.pipeline import IngestPipeline
from chainsentinel.storage.db import DatabaseManager

DATA_DIR = Path(__file__).parent.parent / "data" / "cli_test"
TEST_JSON = str(DATA_DIR / "observations.json")
GROUND_TRUTH = str(DATA_DIR / "ground_truth.json")


@pytest.fixture(scope="module")
def prepared_db(tmp_path_factory):
    """Fixture providing a temporary DuckDB database fully ingested, clustered, and correlated."""
    tmp_dir = tmp_path_factory.mktemp("phase8_db")
    db_file = tmp_dir / "test_phase8.duckdb"
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


def test_forensic_reporter_full_evaluation(prepared_db):
    """Verify that ForensicReporter produces valid quantitative metrics."""
    db, tmp_dir = prepared_db
    reporter = ForensicReporter(db=db, ground_truth_path=GROUND_TRUTH)

    eval_results = reporter.run_full_evaluation()

    assert "telemetry" in eval_results
    assert "clustering" in eval_results
    assert "attribution" in eval_results
    assert "supervised_classification" in eval_results
    assert "unsupervised_holdout_experiment" in eval_results

    # Check clustering metrics
    c = eval_results["clustering"]
    assert c["pairwise_precision"] >= 0.95
    assert c["normalized_mutual_info"] >= 0.70

    # Check attribution metrics
    a = eval_results["attribution"]
    assert "overall_top1_accuracy" in a or "overall" in a

    # Check holdout metrics
    h = eval_results["unsupervised_holdout_experiment"]
    assert "anomaly_separation_delta" in h


def test_markdown_report_generation(prepared_db):
    """Verify that ForensicReporter writes a valid markdown report file."""
    db, tmp_dir = prepared_db
    reporter = ForensicReporter(db=db, ground_truth_path=GROUND_TRUTH)

    eval_results = reporter.run_full_evaluation()
    out_file = tmp_dir / "EVAL_REPORT.md"

    content = reporter.generate_markdown_report(eval_results, output_path=out_file)

    assert out_file.exists()
    assert "# ChainSentinel — Forensic Pipeline Evaluation Report" in content
    assert "Executive Summary & Verification Scorecard" in content
    assert "Entity Resolution (CIOH)" in content
    assert "Network⇄Blockchain Attribution" in content


def test_sample_case_dossier_export(prepared_db):
    """Verify that ForensicReporter creates a court-admissible sample case file."""
    db, tmp_dir = prepared_db
    reporter = ForensicReporter(db=db, ground_truth_path=GROUND_TRUTH)

    out_file = tmp_dir / "SAMPLE_CASE_DOSSIER.md"
    content = reporter.export_sample_dossier(output_path=out_file)

    assert out_file.exists()
    assert "# Forensic Investigative Case Dossier" in content
    assert "Tamper-Evident SHA-256 Digest" in content
    assert "Evidentiary Integrity Seal" in content


def test_cli_report_command(prepared_db):
    """Verify that the `chainsentinel report` CLI command runs cleanly."""
    db, tmp_dir = prepared_db
    out_dir = tmp_dir / "cli_reports"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--db",
            str(db.db_path),
            "--eval-ground-truth",
            GROUND_TRUTH,
            "--output-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "CHAINSENTINEL FORENSIC BENCHMARK SCORECARD" in result.output
    assert (out_dir / "EVAL_REPORT.md").exists()
    assert (out_dir / "SAMPLE_CASE_DOSSIER.md").exists()
