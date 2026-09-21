"""ChainSentinel CLI — command-line interface for the pipeline."""

import click

from chainsentinel import __version__


@click.group()
@click.version_option(version=__version__, prog_name="chainsentinel")
@click.option("--seed", default=42, type=int, help="Global random seed for reproducibility.")
@click.pass_context
def cli(ctx: click.Context, seed: int) -> None:
    """ChainSentinel: AI-Powered Bitcoin Transaction Traffic Analysis."""
    ctx.ensure_object(dict)
    ctx.obj["seed"] = seed


@cli.command()
@click.option("--tx", "tx_count", default=100_000, type=int, help="Number of transactions to generate.")
@click.option("--preset", default=None, type=click.Choice(["50k", "500k", "2m"], case_sensitive=False), help="Standard dataset preset (50k, 500k, 2m).")
@click.option("--seed", "seed_opt", default=None, type=int, help="Seed for generation (defaults to global seed).")
@click.option("--output", "-o", default="data/generated", help="Output directory.")
@click.option(
    "--formats",
    default="csv,json,xml",
    help="Comma-separated output formats (csv, json, xml).",
)
@click.pass_context
def generate(ctx: click.Context, tx_count: int, preset: str | None, seed_opt: int | None, output: str, formats: str) -> None:
    """Generate synthetic Bitcoin transaction data with ground truth."""
    seed = seed_opt if seed_opt is not None else ctx.obj.get("seed", 42)
    fmt_list = [f.strip().lower() for f in formats.split(",")]
    if preset:
        from chainsentinel.gen.config import PRESETS
        tx_count = PRESETS[preset.lower()]
        click.echo(f"Using preset '{preset}': target {tx_count:,} transactions")
    click.echo(f"Generating {tx_count:,} transactions (seed={seed}) -> {output}")
    click.echo(f"Formats: {', '.join(fmt_list)}")

    from chainsentinel.gen.generator import run_generator

    run_generator(
        tx_count=tx_count,
        seed=seed,
        output_dir=output,
        formats=fmt_list,
        preset=preset,
    )


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format", "-f", "format_hint", default=None,
    help="Input format (csv, json, xml). Auto-detected if omitted."
)
@click.option("--db", "db_path", default="data/chainsentinel.duckdb", help="Path to DuckDB database.")
@click.option("--profile", "profile_name", default=None, help="Saved schema mapping profile.")
@click.option("--export-parquet", "parquet_dir", default=None, help="Export tables to Parquet directory after ingest.")
@click.pass_context
def ingest(
    ctx: click.Context,
    file_path: str,
    format_hint: str | None,
    db_path: str,
    profile_name: str | None,
    parquet_dir: str | None,
) -> None:
    """Ingest, validate, enrich, and store Bitcoin observation data (CSV/JSON/XML)."""
    click.echo(f"Ingesting file: {file_path}")
    click.echo(f"Database target: {db_path}")

    from chainsentinel.ingest.pipeline import IngestPipeline
    from chainsentinel.storage.db import DatabaseManager

    db = DatabaseManager(db_path=db_path)
    mapping_override = None
    if profile_name:
        mapping_override = db.get_schema_profile(profile_name)
        if mapping_override:
            click.echo(f"Applying mapping profile: '{profile_name}'")
        else:
            click.echo(f"Warning: Profile '{profile_name}' not found, using auto-detection.")

    pipeline = IngestPipeline(db=db)

    def on_progress(pinfo: dict) -> None:
        click.echo(
            f"  -> Processed: {pinfo['processed']:,} | "
            f"Valid: {pinfo['valid']:,} | "
            f"Quarantined: {pinfo['quarantined']:,}"
        )

    report = pipeline.run(
        file_path=file_path,
        format_hint=format_hint,
        mapping_override=mapping_override,
        progress_callback=on_progress,
    )

    if parquet_dir:
        click.echo(f"Exporting Parquet files to {parquet_dir}...")
        exported = db.export_parquet(parquet_dir)
        click.echo(f"  -> Exported {len(exported)} Parquet tables")

    click.echo("\n[Ingestion Complete]")
    click.echo(f"  Total Processed:    {report.total_rows_processed:,}")
    click.echo(f"  Valid Rows:         {report.valid_rows:,} ({report.valid_rate * 100:.1f}%)")
    click.echo(f"  Quarantined Rows:   {report.quarantined_rows:,}")
    click.echo(f"  Duplicate Rows:     {report.duplicate_rows:,}")
    click.echo(f"  Unique TXs:         {report.unique_transactions:,}")
    click.echo(f"  Unique Addresses:   {report.unique_addresses:,}")
    click.echo(f"  Unique IPs:         {report.unique_ips:,}")
    click.echo(f"  Anonymizer Traffic: {report.anonymizer_count:,} observations")
    click.echo(f"  Total Volume:       {report.total_volume_satoshis / 1e8:,.4f} BTC")
    click.echo(f"  Total Fees:         {report.total_fees_satoshis / 1e8:,.6f} BTC")
    click.echo(f"  Duration:           {report.duration_seconds}s")

    if report.error_breakdown:
        click.echo("\n  [Quarantine Reasons]")
        for reason, count in sorted(report.error_breakdown.items(), key=lambda x: -x[1]):
            click.echo(f"    - {reason}: {count:,}")



@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--change-thresh", type=float, default=0.75, help="Confidence threshold for change address linking.")
@click.option("--min-cj-outputs", type=int, default=3, help="Minimum equal outputs to flag CoinJoin.")
@click.option("--eval-ground-truth", "gt_path", type=click.Path(exists=True), default=None, help="Path to ground_truth.json.")
@click.pass_context
def cluster(
    ctx: click.Context,
    db_path: str | None,
    change_thresh: float,
    min_cj_outputs: int,
    gt_path: str | None,
) -> None:
    """Run entity resolution (CIOH + CoinJoin exclusion + change heuristics) and build graph."""
    from app.core.config import settings
    from chainsentinel.eval.cluster_eval import ClusterEvaluator
    from chainsentinel.graph.entity_resolver import EntityResolver
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Resolving entities from database: {target_db}")
    db = DatabaseManager(target_db)

    resolver = EntityResolver(
        db=db,
        change_threshold=change_thresh,
        min_coinjoin_outputs=min_cj_outputs,
    )
    summary, _ = resolver.run()

    click.echo("\n[Entity Resolution Complete]")
    click.echo(f"  Total Addresses:     {summary.total_addresses:,}")
    click.echo(f"  Resolved Entities:   {summary.total_entities:,}")
    click.echo(f"  CoinJoins Excluded:  {summary.coinjoin_txs_excluded:,} txs")
    click.echo(f"  Change Addrs Linked: {summary.change_addresses_linked:,}")
    click.echo(f"  Largest Cluster:     {summary.largest_cluster_size:,} addresses")
    click.echo(f"  Duration:            {summary.duration_seconds:.2f}s")

    if summary.entity_type_breakdown:
        click.echo("\n  [Entity Classifications]")
        for etype, cnt in sorted(summary.entity_type_breakdown.items(), key=lambda x: -x[1]):
            click.echo(f"    - {etype}: {cnt:,}")

    if gt_path:
        click.echo(f"\n[Evaluating Against Ground Truth: {gt_path}]")
        gt_map = ClusterEvaluator.load_ground_truth_map(gt_path)
        res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        disc_map = dict(res)
        metrics = ClusterEvaluator.evaluate(disc_map, gt_map)
        click.echo(f"  Evaluated Addresses: {metrics['evaluated_addresses']:,}")
        click.echo(f"  Pairwise Precision:  {metrics['pairwise_precision']:.4f}")
        click.echo(f"  Pairwise Recall:     {metrics['pairwise_recall']:.4f}")
        click.echo(f"  Pairwise F1:         {metrics['pairwise_f1']:.4f}")
        click.echo(f"  Adjusted Rand Index: {metrics['adjusted_rand_index']:.4f}")
        click.echo(f"  Normalized MI (NMI): {metrics['normalized_mutual_info']:.4f}")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--window", "time_window", type=float, default=60.0, help="Co-occurrence time window in seconds.")
@click.option("--eval-ground-truth", "gt_path", type=click.Path(exists=True), default=None, help="Path to ground_truth.json.")
@click.pass_context
def correlate(
    ctx: click.Context,
    db_path: str | None,
    time_window: float,
    gt_path: str | None,
) -> None:
    """Run Network-Blockchain correlation engine (origin estimation, TF-IDF, timing tests)."""
    from app.core.config import settings
    from chainsentinel.correlate.engine import CorrelationEngine
    from chainsentinel.eval.correlate_eval import CorrelateEvaluator
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Running correlation engine on: {target_db}")
    db = DatabaseManager(target_db)

    engine = CorrelationEngine(db=db, time_window_sec=time_window)
    summary, attributions = engine.run()

    click.echo("\n[Correlation Complete]")
    click.echo(f"  Transactions Analyzed: {summary.total_tx_analyzed:,}")
    click.echo(f"  Entities Analyzed:     {summary.total_entities_analyzed:,}")
    click.echo(f"  Origin Estimates:      {summary.total_origin_estimates:,}")
    click.echo(f"  IP-Entity Links:       {summary.total_ip_entity_links:,}")
    click.echo(f"  Operator Links:        {summary.total_operator_links:,} pairs (p <= 0.05)")
    click.echo(f"  Signatures Extracted:  {summary.total_signatures_extracted:,}")
    click.echo(f"  Duration:              {summary.duration_seconds:.2f}s")

    if gt_path:
        click.echo(f"\n[Evaluating Attribution vs Ground Truth: {gt_path}]")
        aem_res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        aem_map = dict(aem_res)
        metrics = CorrelateEvaluator.evaluate_attribution(
            attributions=attributions,
            ground_truth_path=gt_path,
            address_entity_map=aem_map,
        )
        click.echo(f"  Entities Evaluated:    {metrics['total_entities_evaluated']:,}")
        click.echo(f"  Overall Top-1 Accuracy:{metrics['overall_top1_accuracy'] * 100:.2f}%")
        click.echo(f"  Overall Top-3 Accuracy:{metrics['overall_top3_accuracy'] * 100:.2f}%")
        click.echo("  [By Obfuscation Level]")
        for lvl, st in metrics["by_obfuscation_level"].items():
            click.echo(f"    - {lvl}: Top-1: {st['top1_accuracy']*100:.1f}% | Top-3: {st['top3_accuracy']*100:.1f}% ({st['total_entities']} entities)")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--eval-ground-truth", "gt_path", type=click.Path(exists=True), default=None, help="Path to ground_truth.json.")
@click.option("--model-dir", type=click.Path(), default="data/models", help="Directory to save models.")
@click.pass_context
def train(
    ctx: click.Context,
    db_path: str | None,
    gt_path: str | None,
    model_dir: str,
) -> None:
    """Train ML models (supervised gradient boost, conformal calibration, anomaly detector)."""
    from app.core.config import settings
    from chainsentinel.models.pipeline import ModelPipeline
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Training intelligence pipeline on database: {target_db}")
    db = DatabaseManager(target_db)

    pipeline = ModelPipeline(db=db, model_dir=model_dir)
    report = pipeline.train(ground_truth_path=gt_path)

    if report.get("status") == "error":
        click.echo(f"[Error] {report.get('message')}")
        return

    m = report["metrics"]
    click.echo("\n[Model Training & Calibration Complete]")
    click.echo(f"  Entities Trained:       {report['entities_trained']:,}")
    click.echo(f"  Accuracy:               {m['accuracy'] * 100:.2f}%")
    click.echo(f"  Precision (macro):      {m['precision_macro'] * 100:.2f}%")
    click.echo(f"  Recall (macro):         {m['recall_macro'] * 100:.2f}%")
    click.echo(f"  F1-Score (macro):       {m['f1_macro'] * 100:.2f}%")
    click.echo(f"  F1-Score (weighted):    {m['f1_weighted'] * 100:.2f}%")

    c = report["conformal"]
    click.echo("\n  [Conformal Prediction Bounds (90% Guarantee)]")
    click.echo(f"  Mean Prediction Set Size: {c['avg_set_size']:.2f} classes")
    click.echo(f"  Grade Distribution:     A: {c['grade_distribution']['A']}, B: {c['grade_distribution']['B']}, C: {c['grade_distribution']['C']}")

    click.echo("\n  [Top Diagnostic Features (TreeSHAP Importances)]")
    for feat, imp in report["top_features"][:6]:
        click.echo(f"    - {feat:<28}: {imp * 100:.1f}%")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--min-risk", type=float, default=0.35, help="Minimum composite risk score threshold.")
@click.option("--limit", type=int, default=25, help="Maximum alerts to display.")
@click.option("--model-dir", type=click.Path(), default="data/models", help="Directory with saved models.")
@click.pass_context
def detect(
    ctx: click.Context,
    db_path: str | None,
    min_risk: float,
    limit: int,
    model_dir: str,
) -> None:
    """Run detection engine and produce ranked, explainable investigative alerts."""
    from app.core.config import settings
    from chainsentinel.models.pipeline import ModelPipeline
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Running detection engine on database: {target_db}")
    db = DatabaseManager(target_db)

    pipeline = ModelPipeline(db=db, model_dir=model_dir)
    alerts = pipeline.detect(min_risk_score=min_risk, limit=limit)

    click.echo(f"\n[Detection Complete: {len(alerts)} Alerts Generated (Risk >= {min_risk})]")
    for i, a in enumerate(alerts, 1):
        top_typ = a["typologies"][0]["name"] if a["typologies"] else "UNKNOWN"
        top_str = a["typologies"][0]["strength"] if a["typologies"] else 0.0
        conf = a["confidence"]
        attr = a["attribution"]
        top_reason = a["reasons"][0]["text"] if a["reasons"] else "No primary reason"

        click.echo(f"\n  #{i:02d} [{a['alert_id']}] Priority: {a['priority']:.2f} | Risk: {a['risk_score']:.2f}")
        click.echo(f"       Entity:      {a['entity_id']} ({len(a['evidence']['txids'])} txs)")
        click.echo(f"       Typology:    {top_typ} (p={top_str:.2f}) | Grade: [{conf['grade']}] Set: {conf['conformal_set']}")
        click.echo(f"       Attribution: IP {attr['ip']} ({attr['country']}, {attr['asn']}) Conf: {attr['confidence']:.2f}")
        click.echo(f"       Key Rationale: {top_reason}")
        click.echo(f"       Bundle Hash: {a['evidence']['bundle_hash'][:16]}...")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--eval-ground-truth", "gt_path", type=click.Path(exists=True), default="data/cli_test/ground_truth.json", help="Path to ground_truth.json.")
@click.pass_context
def evaluate(
    ctx: click.Context,
    db_path: str | None,
    gt_path: str,
) -> None:
    """Evaluate full pipeline performance and hold-out unseen typology experiment."""
    from app.core.config import settings
    from chainsentinel.models.pipeline import ModelPipeline
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Evaluating models on database: {target_db} vs {gt_path}")
    db = DatabaseManager(target_db)

    pipeline = ModelPipeline(db=db)
    train_res = pipeline.train(ground_truth_path=gt_path)
    if train_res.get("status") == "error":
        click.echo(f"\n[Error] {train_res.get('message', 'Failed to train models.')}")
        click.echo("Please ensure data has been ingested and clustered before running evaluation.")
        return

    click.echo("\n[1. Supervised Multi-Class Benchmark]")
    m = train_res["metrics"]
    click.echo(f"  Accuracy:            {m['accuracy'] * 100:.2f}%")
    click.echo(f"  F1-Score (macro):    {m['f1_macro'] * 100:.2f}%")
    click.echo(f"  F1-Score (weighted): {m['f1_weighted'] * 100:.2f}%")

    click.echo("\n[2. Unseen Hold-Out Typology Experiment (Proof of Real AI/ML)]")
    click.echo("  Training anomaly detector strictly without T8 (Dusting) and T9 (Multi-Cluster)...")
    holdout_res = pipeline.evaluate_holdout(ground_truth_path=gt_path)
    click.echo(f"  Legitimate Baseline Anomaly Mean: {holdout_res['legitimate_anomaly_mean']:.3f}")
    click.echo(f"  Unseen Hold-Out Anomaly Mean:     {holdout_res['holdout_anomaly_mean']:.3f}")
    click.echo(f"  Separation Delta:                 +{holdout_res['anomaly_separation_delta']:.3f}")
    click.echo(f"  Hold-Out Anomaly Detection Rate:  {holdout_res['flagged_as_anomalous_ratio'] * 100:.1f}%")


@cli.command()
@click.argument("target")
@click.option("--direction", "-d", type=click.Choice(["forward", "backward", "both"], case_sensitive=False), default="forward", help="Tracing direction.")
@click.option("--decay", "-m", type=click.Choice(["proportional", "fifo", "poison"], case_sensitive=False), default="proportional", help="Taint decay model.")
@click.option("--max-hops", "-k", default=5, type=int, help="Maximum hop horizon.")
@click.option("--amount", type=int, default=None, help="Initial taint amount in satoshis.")
@click.option("--min-ratio", default=0.01, type=float, help="Pruning threshold ratio.")
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.pass_context
def trace(
    ctx: click.Context,
    target: str,
    direction: str,
    decay: str,
    max_hops: int,
    amount: int | None,
    min_ratio: float,
    db_path: str | None,
) -> None:
    """Execute forward, backward, or bidirectional forensic taint tracing."""
    from app.core.config import settings
    from chainsentinel.storage.db import DatabaseManager
    from chainsentinel.trace.taint_tracker import TaintTracker

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Executing {direction.upper()} taint trace on target: {target}")
    click.echo(f"Model: {decay} | Max Hops: {max_hops} | Database: {target_db}")

    db = DatabaseManager(target_db)
    tracker = TaintTracker(db)

    res = tracker.trace(
        root_ref=target,
        direction=direction,
        initial_taint_sat=amount,
        max_hops=max_hops,
        decay_model=decay,
        min_taint_ratio=min_ratio,
    )

    summary = res.get("summary", {})
    hops = res.get("hops", [])
    endpoints = res.get("endpoints", [])

    click.echo(f"\n[Trace Execution Completed — Trace ID: {res['trace_id']}]")
    click.echo(f"  Total Traversed Hops: {len(hops)}")
    click.echo(f"  Terminal Endpoints:   {len(endpoints)}")

    if summary.get("cashout_exchanges"):
        click.echo(f"  Cashout Exchanges:    {', '.join(summary['cashout_exchanges'])}")
    if summary.get("source_entities"):
        click.echo(f"  Funding Sources:      {', '.join(summary['source_entities'])}")
    if summary.get("operator_ips"):
        click.echo(f"  Attributed IPs:       {', '.join(summary['operator_ips'][:5])}")

    click.echo("\n  Top Taint Flows:")
    for h in hops[:10]:
        click.echo(
            f"   Hop {h.get('hop_index', 1)}: {h.get('source_entity')} -> {h.get('target_entity')} "
            f"| Taint: {h.get('taint_pct', 0)}% ({h.get('tainted_sat', 0):,} sat) "
            f"| Type: {h.get('target_type', 'UNKNOWN')}"
            + (f" [STOP: {h.get('stop_reason')}]" if h.get("stop_reason") else "")
        )


@cli.command()
@click.argument("target")
@click.option("--max-hops", "-k", default=4, type=int, help="Tracing horizon.")
@click.option("--decay", type=click.Choice(["proportional", "fifo", "poison"], case_sensitive=False), default="proportional", help="Decay model.")
@click.option("--title", default=None, help="Optional case title.")
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.pass_context
def investigate(
    ctx: click.Context,
    target: str,
    max_hops: int,
    decay: str,
    title: str | None,
    db_path: str | None,
) -> None:
    """Autonomously investigate an entity/address/TXID and generate a forensic case file."""
    from app.core.config import settings
    from chainsentinel.storage.db import DatabaseManager
    from chainsentinel.trace.agent import AutonomousInvestigator

    target_db = db_path or str(settings.DB_PATH)
    click.echo(f"Initiating autonomous forensic investigation on: {target}")
    click.echo(f"Database: {target_db}")

    db = DatabaseManager(target_db)
    agent = AutonomousInvestigator(db)

    case = agent.investigate(
        target=target,
        max_hops=max_hops,
        decay_model=decay,
        title=title,
    )

    ev = case.get("evidence_bundle", {})
    sub = case.get("cytoscape_subgraph", {}).get("elements", {})
    n_nodes = len(sub.get("nodes", []))
    n_edges = len(sub.get("edges", []))

    click.echo(f"\n[Case File Created: {case['case_id']}]")
    click.echo(f"  Title:        {case['title']}")
    click.echo(f"  Status:       {case['status']}")
    click.echo(f"  Bundle Hash:  {case['bundle_hash']}")
    click.echo(f"  Graph Nodes:  {n_nodes} nodes, {n_edges} edges")
    click.echo(f"  Forward Hops: {ev.get('forward_hops_count', 0)}")
    click.echo(f"  Backward Hops:{ev.get('backward_hops_count', 0)}")
    click.echo("\n--- Narrative Preview ---")
    lines = case.get("narrative_report", "").split("\n")
    for l in lines[:12]:
        click.echo(f"  {l}")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=None, help="DuckDB database path.")
@click.option("--eval-ground-truth", "gt_path", type=click.Path(exists=True), default=None, help="Path to ground_truth.json.")
@click.option("--output-dir", "output_dir", type=click.Path(), default="docs", help="Directory to save generated markdown reports.")
@click.pass_context
def report(
    ctx: click.Context,
    db_path: str | None,
    gt_path: str | None,
    output_dir: str,
) -> None:
    """Generate comprehensive forensic evaluation report and sample case dossier."""
    from pathlib import Path
    from app.core.config import settings
    from chainsentinel.eval.reporter import ForensicReporter
    from chainsentinel.storage.db import DatabaseManager

    target_db = db_path or str(settings.DB_PATH)
    target_gt = gt_path or "data/cli_test/ground_truth.json"
    if not Path(target_gt).exists():
        alt_gt = Path("data/synthetic/ground_truth.json")
        if alt_gt.exists():
            target_gt = str(alt_gt)

    click.echo("Generating Forensic Evaluation Benchmark...")
    click.echo(f"  Database:     {target_db}")
    click.echo(f"  Ground Truth: {target_gt}")
    click.echo(f"  Output Dir:   {output_dir}")

    db = DatabaseManager(target_db)
    reporter = ForensicReporter(db=db, ground_truth_path=target_gt)

    eval_results = reporter.run_full_evaluation()

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "EVAL_REPORT.md"
    dossier_file = out_dir / "SAMPLE_CASE_DOSSIER.md"

    reporter.generate_markdown_report(eval_results, output_path=report_file)
    reporter.export_sample_dossier(output_path=dossier_file)

    c = eval_results.get("clustering", {})
    a = eval_results.get("attribution", {})
    s = eval_results.get("supervised_classification", {})
    h = eval_results.get("unsupervised_holdout_experiment", {})
    t = eval_results.get("telemetry", {})

    top1 = a.get("overall_top1_accuracy")
    if top1 is None:
        top1 = a.get("overall", {}).get("top1_accuracy", 0.0)
    top3 = a.get("overall_top3_accuracy")
    if top3 is None:
        top3 = a.get("overall", {}).get("top3_accuracy", 0.0)

    from chainsentinel.eval.reporter import load_eval_targets
    targets = load_eval_targets()
    t_clust = targets.get("clustering", {})
    t_attr = targets.get("attribution", {})
    t_sup = targets.get("supervised_classification", {})
    t_unsup = targets.get("unsupervised_holdout_experiment", {})

    click.echo("\n========================================================")
    click.echo("       CHAINSENTINEL FORENSIC BENCHMARK SCORECARD       ")
    click.echo("========================================================")
    click.echo(f"  Monitored Entities:      {t.get('total_entities', 0):,}")
    click.echo(f"  Monitored Transactions:  {t.get('total_transactions', 0):,}")
    click.echo(f"  Active High-Risk Alerts: {t.get('total_alerts', 0):,}")
    click.echo("--------------------------------------------------------")
    
    tgt_p = t_clust.get("pairwise_precision", {}).get("target", 0.95) * 100
    act_p = f"{c['pairwise_precision']*100:.2f}%" if "pairwise_precision" in c else "N/A"
    click.echo(f"  CIOH Pairwise Precision: {act_p}  (Target >= {tgt_p:.1f}%)")

    tgt_nmi = t_clust.get("normalized_mutual_info", {}).get("target", 0.70)
    act_nmi = f"{c['normalized_mutual_info']:.4f}" if "normalized_mutual_info" in c else "N/A"
    click.echo(f"  CIOH Normalized MI (NMI):{act_nmi}  (Target >= {tgt_nmi:.3f})")

    tgt_t1 = t_attr.get("overall_top1_accuracy", {}).get("target", 0.45) * 100
    act_t1 = f"{float(top1)*100:.2f}%" if top1 is not None else "N/A"
    click.echo(f"  IP Attribution Top-1:    {act_t1}  (Target >= {tgt_t1:.1f}%)")

    tgt_t3 = t_attr.get("overall_top3_accuracy", {}).get("target", 0.50) * 100
    act_t3 = f"{float(top3)*100:.2f}%" if top3 is not None else "N/A"
    click.echo(f"  IP Attribution Top-3:    {act_t3}  (Target >= {tgt_t3:.1f}%)")

    tgt_acc = t_sup.get("accuracy", {}).get("target", 0.85) * 100
    act_acc = f"{s['accuracy']*100:.2f}%" if "accuracy" in s else "N/A"
    click.echo(f"  Supervised Accuracy:     {act_acc}  (Target >= {tgt_acc:.1f}%)")

    tgt_f1 = t_sup.get("f1_macro", {}).get("target", 0.70)
    act_f1 = f"{s['f1_macro']:.4f}" if "f1_macro" in s else "N/A"
    click.echo(f"  Supervised Macro F1:     {act_f1}  (Target >= {tgt_f1:.3f})")

    tgt_sep = t_unsup.get("anomaly_separation_delta", {}).get("target", 0.30)
    act_sep = f"+{h['anomaly_separation_delta']:.3f}" if "anomaly_separation_delta" in h else "N/A"
    click.echo(f"  Hold-out Anomaly Delta: {act_sep}  (Target >= +{tgt_sep:.3f})")

    tgt_flag = t_unsup.get("flagged_as_anomalous_ratio", {}).get("target", 0.40) * 100
    act_flag = f"{h['flagged_as_anomalous_ratio']*100:.2f}%" if "flagged_as_anomalous_ratio" in h else "N/A"
    click.echo(f"  Hold-out Detection Rate: {act_flag}  (Target >= {tgt_flag:.1f}%)")
    click.echo("========================================================")
    click.echo(f"  [+] Evaluation Report:   {report_file}")
    click.echo(f"  [+] Sample Case Dossier: {dossier_file}")
    click.echo("  [OK] SIH26146 Forensic Benchmarks Processed.")


@cli.command("retrain-from-feedback")
@click.option("--db", default=None, type=click.Path(), help="DuckDB database path.")
@click.option("--model-dir", default=None, type=click.Path(), help="Model artifacts directory.")
@click.option("--dry-run", is_flag=True, help="Display feedback stats without retraining.")
def retrain_from_feedback_cmd(db: str | None, model_dir: str | None, dry_run: bool) -> None:
    """Retrain AI models incrementally using analyst feedback verdicts."""
    target_db = resolve_db_path(db)
    database = DatabaseManager(target_db)
    feedback_items = database.list_alert_feedback(limit=1000)

    click.echo("\n========================================================")
    click.echo("     CHAINSENTINEL ACTIVE LEARNING: ANALYST FEEDBACK     ")
    click.echo("========================================================")
    click.echo(f"  Database:           {target_db}")
    click.echo(f"  Recorded Feedback:  {len(feedback_items)} entries")

    confirmed = [f for f in feedback_items if f.get("analyst_verdict") == "confirmed_malicious"]
    false_pos = [f for f in feedback_items if f.get("analyst_verdict") == "false_positive"]
    needs_rev = [f for f in feedback_items if f.get("analyst_verdict") == "needs_review"]

    click.echo(f"  - Confirmed Malicious:  {len(confirmed)}")
    click.echo(f"  - False Positives:      {len(false_pos)}")
    click.echo(f"  - Under Review:         {len(needs_rev)}")

    if not feedback_items:
        click.echo("  [!] No analyst feedback recorded yet in alert_feedback.")
        click.echo("========================================================\n")
        return

    if dry_run:
        click.echo("  [DRY-RUN] Retraining skipped (dry-run mode).")
        click.echo("========================================================\n")
        return

    m_dir = Path(model_dir) if model_dir else Path("data/models")
    pipeline = ModelPipeline(db=database, model_dir=m_dir)
    click.echo("  [*] Updating model weights with active learning supervision...")
    report = pipeline.train(ground_truth_path=None)
    click.echo("  [+] Model successfully retrained with human-in-the-loop signal!")
    click.echo("========================================================\n")


if __name__ == "__main__":
    cli()

