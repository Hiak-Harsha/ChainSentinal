"""DuckDB SQL DDL schema definitions for ChainSentinel."""

SCHEMA_DDL = """
-- Core network layer observations
CREATE TABLE IF NOT EXISTS observations (
    obs_id VARCHAR PRIMARY KEY,
    ts DOUBLE,
    src_ip VARCHAR,
    dst_ip VARCHAR,
    src_port INTEGER,
    dst_port INTEGER,
    txid VARCHAR,
    src_country VARCHAR,
    src_asn VARCHAR,
    src_asn_org VARCHAR,
    is_anonymizer BOOLEAN,
    sensor_id VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_obs_txid ON observations (txid);
CREATE INDEX IF NOT EXISTS idx_obs_src_ip ON observations (src_ip);
CREATE INDEX IF NOT EXISTS idx_obs_ts ON observations (ts);

-- Normalized blockchain transactions
CREATE TABLE IF NOT EXISTS transactions (
    txid VARCHAR PRIMARY KEY,
    first_seen_ts DOUBLE,
    fee_sat BIGINT,
    vsize INTEGER,
    fee_rate DOUBLE,
    n_in INTEGER,
    n_out INTEGER,
    total_in BIGINT,
    total_out BIGINT,
    script_types VARCHAR[]
);

CREATE INDEX IF NOT EXISTS idx_tx_first_seen ON transactions (first_seen_ts);

-- Transaction inputs
CREATE TABLE IF NOT EXISTS tx_inputs (
    txid VARCHAR,
    idx INTEGER,
    address VARCHAR,
    amount BIGINT,
    PRIMARY KEY (txid, idx)
);

CREATE INDEX IF NOT EXISTS idx_inputs_addr ON tx_inputs (address);

-- Transaction outputs
CREATE TABLE IF NOT EXISTS tx_outputs (
    txid VARCHAR,
    idx INTEGER,
    address VARCHAR,
    amount BIGINT,
    script_type VARCHAR,
    PRIMARY KEY (txid, idx)
);

CREATE INDEX IF NOT EXISTS idx_outputs_addr ON tx_outputs (address);

-- Unique address registry
CREATE TABLE IF NOT EXISTS addresses (
    address VARCHAR PRIMARY KEY,
    first_seen DOUBLE,
    last_seen DOUBLE,
    script_type VARCHAR
);

-- Quarantined invalid rows with error classification
CREATE TABLE IF NOT EXISTS quarantined_observations (
    obs_id VARCHAR PRIMARY KEY,
    raw_data VARCHAR,
    reason_code VARCHAR,
    error_details VARCHAR,
    ingested_at DOUBLE
);

CREATE INDEX IF NOT EXISTS idx_quarantine_reason ON quarantined_observations (reason_code);

-- Ingestion job execution tracking
CREATE TABLE IF NOT EXISTS ingest_jobs (
    job_id VARCHAR PRIMARY KEY,
    file_path VARCHAR,
    format VARCHAR,
    status VARCHAR,
    total_rows INTEGER DEFAULT 0,
    valid_rows INTEGER DEFAULT 0,
    quarantined_rows INTEGER DEFAULT 0,
    started_at DOUBLE,
    completed_at DOUBLE,
    qc_report_json VARCHAR
);

-- Saved schema mapping profiles
CREATE TABLE IF NOT EXISTS schema_mapping_profiles (
    profile_name VARCHAR PRIMARY KEY,
    mapping_json VARCHAR,
    created_at DOUBLE
);

-- Resolved real-world entities
CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR PRIMARY KEY,
    entity_type VARCHAR,
    member_count BIGINT,
    resolution_conf DOUBLE,
    first_seen DOUBLE,
    last_seen DOUBLE,
    total_received_sat BIGINT,
    total_sent_sat BIGINT,
    created_at DOUBLE
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type);

-- Address to Entity resolution mapping
CREATE TABLE IF NOT EXISTS address_entity_map (
    address VARCHAR PRIMARY KEY,
    entity_id VARCHAR,
    confidence DOUBLE,
    method VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_aem_entity ON address_entity_map (entity_id);

-- Heterogeneous graph edges
CREATE TABLE IF NOT EXISTS graph_edges (
    source VARCHAR,
    target VARCHAR,
    edge_type VARCHAR,
    weight DOUBLE,
    metadata_json VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_edges_src ON graph_edges (source);
CREATE INDEX IF NOT EXISTS idx_edges_tgt ON graph_edges (target);
CREATE INDEX IF NOT EXISTS idx_edges_type ON graph_edges (edge_type);

-- First-seen origin IP estimates per transaction
CREATE TABLE IF NOT EXISTS tx_origins (
    txid VARCHAR PRIMARY KEY,
    origin_ip VARCHAR,
    confidence DOUBLE,
    delta_t DOUBLE,
    is_anonymizer BOOLEAN,
    sensor_count INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tx_origins_ip ON tx_origins (origin_ip);

-- Entity to IP attribution links (TF-IDF hub-debiased)
CREATE TABLE IF NOT EXISTS ip_entity_links (
    ip VARCHAR,
    entity_id VARCHAR,
    score DOUBLE,
    posterior_prob DOUBLE,
    n_tx INTEGER,
    first_seen_ratio DOUBLE,
    PRIMARY KEY (ip, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_iel_entity ON ip_entity_links (entity_id);
CREATE INDEX IF NOT EXISTS idx_iel_ip ON ip_entity_links (ip);

-- Multi-cluster operator links via shared origin IPs
CREATE TABLE IF NOT EXISTS shares_origin_links (
    entity_a VARCHAR,
    entity_b VARCHAR,
    shared_ip VARCHAR,
    co_occurrences INTEGER,
    p_value DOUBLE,
    PRIMARY KEY (entity_a, entity_b, shared_ip)
);

CREATE INDEX IF NOT EXISTS idx_sol_ea ON shares_origin_links (entity_a);
CREATE INDEX IF NOT EXISTS idx_sol_eb ON shares_origin_links (entity_b);

-- Behavioral network signatures per entity
CREATE TABLE IF NOT EXISTS entity_network_signatures (
    entity_id VARCHAR PRIMARY KEY,
    non_standard_port_ratio DOUBLE,
    ip_churn_rate DOUBLE,
    asn_count INTEGER,
    anonymizer_ratio DOUBLE,
    circadian_entropy DOUBLE,
    geo_hop_count INTEGER
);

-- Risk-ranked investigative alerts
CREATE TABLE IF NOT EXISTS alerts (
    alert_id VARCHAR PRIMARY KEY,
    entity_id VARCHAR,
    priority DOUBLE,
    risk_score DOUBLE,
    status VARCHAR,
    alert_json VARCHAR,
    created_at DOUBLE
);

CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts (entity_id);
CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts (priority);
CREATE INDEX IF NOT EXISTS idx_alerts_risk ON alerts (risk_score);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);

-- Multimodal entity feature vectors
CREATE TABLE IF NOT EXISTS entity_features (
    entity_id VARCHAR PRIMARY KEY,
    feature_vector_json VARCHAR,
    updated_at DOUBLE
);

-- Model performance and evaluation metrics registry
CREATE TABLE IF NOT EXISTS model_metrics (
    model_name VARCHAR PRIMARY KEY,
    metrics_json VARCHAR,
    evaluated_at DOUBLE
);

-- Forward and backward taint tracking runs
CREATE TABLE IF NOT EXISTS taint_traces (
    trace_id VARCHAR PRIMARY KEY,
    root_ref VARCHAR,
    direction VARCHAR,
    decay_model VARCHAR,
    max_hops INTEGER,
    hops_json VARCHAR,
    summary_json VARCHAR,
    created_at DOUBLE
);

CREATE INDEX IF NOT EXISTS idx_traces_root ON taint_traces (root_ref);
CREATE INDEX IF NOT EXISTS idx_traces_direction ON taint_traces (direction);

-- Autonomous investigative case files
CREATE TABLE IF NOT EXISTS investigative_cases (
    case_id VARCHAR PRIMARY KEY,
    target_id VARCHAR,
    title VARCHAR,
    status VARCHAR,
    case_json VARCHAR,
    created_at DOUBLE
);

CREATE INDEX IF NOT EXISTS idx_cases_target ON investigative_cases (target_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON investigative_cases (status);
"""


