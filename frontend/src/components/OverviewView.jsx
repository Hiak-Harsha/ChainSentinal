import React from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert,
  Users,
  AlertTriangle,
  Play,
  Search,
  UploadCloud,
  FileText,
  Activity,
  CheckCircle2,
  Database,
  Layers,
  ArrowRight,
  Clock,
  Flame,
  ShieldCheck,
} from 'lucide-react';
import {
  MetricCard,
  SectionCard,
  StatusBadge,
  CopyHash,
  DataTable,
  EmptyState,
} from './shared';
import { BTCCoinIcon } from './visuals/icons';

export default function OverviewView({
  metrics,
  alerts = [],
  health,
  onSelectAlert,
  onSwitchTab,
  onTriggerDetect,
  detecting = false,
  onRefresh,
}) {
  const isHealthy = health?.status === 'ok' || health?.status === 'healthy';
  const totalEntities = metrics?.total_entities ?? metrics?.entity_count ?? null;
  const totalEdges = metrics?.total_edges ?? null;
  const totalTransactions = metrics?.total_transactions ?? null;
  const totalAddresses = metrics?.total_addresses ?? null;
  const totalQuarantined = metrics?.total_quarantined ?? 0;
  const totalVolumeBtc = metrics?.total_volume_btc ?? (typeof metrics?.total_volume_sat === 'number' ? (metrics.total_volume_sat / 1e8).toFixed(4) : null);
  const meanRisk = metrics?.mean_risk_score ?? null;
  const highRiskCount = metrics?.high_risk_alerts ?? alerts.filter((a) => (a.priority ?? a.risk_score ?? 0) >= 0.7).length;

  const recentJobs = metrics?.recent_jobs || [];
  const recentCases = metrics?.recent_cases || [];

  const topAlerts = alerts
    .filter((a) => a.status === 'NEW' || a.status === 'INVESTIGATING' || !a.status)
    .slice(0, 5);

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.06 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' } },
  };

  const alertColumns = [
    {
      header: 'Alert ID',
      key: 'alert_id',
      render: (val) => <CopyHash hash={val} truncate={12} />,
    },
    {
      header: 'Target Entity',
      key: 'entity_id',
      render: (val) => (
        <span className="mono" style={{ color: 'var(--text-emphasis)', fontWeight: 600 }}>
          {val ? `${val.slice(0, 14)}…` : '—'}
        </span>
      ),
    },
    {
      header: 'Risk Score',
      key: 'risk_score',
      render: (val, row) => {
        const score = val ?? row.priority ?? 0;
        const color = score >= 0.7 ? 'var(--crimson)' : score >= 0.4 ? 'var(--amber)' : 'var(--emerald)';
        return (
          <span className="mono font-bold" style={{ color }}>
            {(score * 100).toFixed(0)}%
          </span>
        );
      },
    },
    {
      header: 'Confidence Grade',
      key: 'confidence',
      render: (conf) => {
        const grade = conf?.grade || 'B';
        return <span className={`badge badge-grade-${grade.toLowerCase()}`}>Grade {grade}</span>;
      },
    },
    {
      header: 'Status',
      key: 'status',
      render: (val) => <StatusBadge status={val || 'NEW'} />,
    },
    {
      header: 'Action',
      key: 'action',
      align: 'right',
      render: (_, row) => (
        <button
          className="btn btn-secondary btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            onSelectAlert?.(row);
          }}
        >
          Investigate <ArrowRight size={12} />
        </button>
      ),
    },
  ];

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Threat Center Situational Banner */}
      <motion.div
        variants={itemVariants}
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(20, 24, 36, 0.95) 0%, rgba(35, 25, 15, 0.8) 100%)',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-emphasis)', margin: 0 }}>
                Forensic Operations Threat Center
              </h1>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  background: isHealthy ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                  color: isHealthy ? '#10b981' : '#f43f5e',
                  border: `1px solid ${isHealthy ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isHealthy ? '#10b981' : '#f43f5e',
                  }}
                />
                {isHealthy ? 'BACKEND ONLINE' : 'TELEMETRY DISCONNECTED'}
              </span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.3rem', lineHeight: 1.4 }}>
              Deterministic Bitcoin forensic ledger &bull; Continuous entity topology resolution &bull; Inductive conformal risk scoring.
            </div>
          </div>

          {/* Core Action Group */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              id="btn-quick-detect"
              className="btn btn-primary"
              onClick={onTriggerDetect}
              disabled={detecting}
            >
              <Play size={15} />
              {detecting ? 'Running Inference…' : 'Run Detection Engine'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onSwitchTab?.('graph')}
            >
              <Search size={15} /> Explore Network
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onSwitchTab?.('ingest')}
            >
              <UploadCloud size={15} /> Ingest Data
            </button>
          </div>
        </div>
      </motion.div>

      {/* 2. Scaled Telemetry KPI Cards */}
      <motion.div
        variants={itemVariants}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '1rem',
        }}
      >
        <MetricCard
          label="RESOLVED ENTITIES"
          numericValue={totalEntities}
          variant="cyan"
          icon={Users}
          meta="CIOH + CoinJoin clustered entities"
          onClick={() => onSwitchTab?.('graph')}
        />

        <MetricCard
          label="HIGH-RISK LEADS"
          numericValue={highRiskCount}
          variant="crimson"
          icon={AlertTriangle}
          meta={`${alerts.length} total active ranked leads`}
          onClick={() => onSwitchTab?.('alerts')}
        />

        <MetricCard
          label="TRACKED VOLUME"
          value={totalVolumeBtc !== null ? `${totalVolumeBtc} BTC` : '—'}
          variant="btc"
          icon={BTCCoinIcon}
          meta={typeof metrics?.total_volume_sat === 'number' ? `${metrics.total_volume_sat.toLocaleString()} satoshis` : 'Aggregated UTXO flow'}
        />

        <MetricCard
          label="QUARANTINE QUEUE"
          numericValue={totalQuarantined}
          variant={totalQuarantined > 0 ? 'amber' : 'emerald'}
          icon={ShieldAlert}
          meta={totalQuarantined > 0 ? 'Invalid records awaiting inspection' : 'Zero validation violations'}
          onClick={() => onSwitchTab?.('ingest')}
        />

        <MetricCard
          label="MEAN ENTITY RISK"
          numericValue={meanRisk !== null ? meanRisk * 100 : null}
          decimals={1}
          suffix="%"
          variant="purple"
          icon={Activity}
          meta="Network-wide Bayesian risk average"
        />
      </motion.div>

      {/* 3. High-Priority Action Table */}
      <motion.div variants={itemVariants}>
        <SectionCard
          icon={ShieldAlert}
          iconColor="var(--crimson)"
          title="Requires Analyst Attention: Unresolved High-Risk Leads"
          subtitle="Top unaddressed forensic leads ranked by Bayesian composite risk score"
          actions={
            <button className="btn btn-secondary btn-sm" onClick={() => onSwitchTab?.('alerts')}>
              View All Alerts ({alerts.length}) <ArrowRight size={13} />
            </button>
          }
        >
          <DataTable
            columns={alertColumns}
            data={topAlerts}
            onRowClick={(row) => onSelectAlert?.(row)}
            emptyTitle="No Critical Alerts Pending"
            emptyDescription="All identified threats have been triaged or no high-risk transactions detected."
            pagination={false}
          />
        </SectionCard>
      </motion.div>

      {/* 4. Recent Forensic Operations Grid */}
      <motion.div
        variants={itemVariants}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
          gap: '1.25rem',
        }}
      >
        {/* Left: Recent Ingestion Jobs */}
        <SectionCard
          icon={UploadCloud}
          iconColor="var(--btc-orange)"
          title="Recent Ingestion Runs"
          subtitle="Data quality auditing and pipeline ingest history"
          actions={
            <button className="btn btn-secondary btn-sm" onClick={() => onSwitchTab?.('ingest')}>
              Ingestion Wizard <ArrowRight size={13} />
            </button>
          }
        >
          {recentJobs.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {recentJobs.map((job) => (
                <div
                  key={job.job_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.6rem 0.8rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.78rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span className="badge badge-emerald mono" style={{ textTransform: 'uppercase' }}>
                      {job.format || 'CSV'}
                    </span>
                    <div>
                      <div className="mono font-semibold" style={{ color: 'var(--text-main)' }}>
                        {job.job_id}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Valid: <strong className="text-emerald">{job.valid_rows?.toLocaleString() ?? 0}</strong> &bull; Quarantined: <strong className="text-crimson">{job.quarantined_rows?.toLocaleString() ?? 0}</strong>
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={job.status} size="sm" />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={UploadCloud}
              title="No Ingestion Runs Recorded"
              description="Upload a CSV, JSON, or XML dataset to begin automated quality validation."
              action={
                <button className="btn btn-secondary btn-sm" onClick={() => onSwitchTab?.('ingest')}>
                  Upload Dataset
                </button>
              }
            />
          )}
        </SectionCard>

        {/* Right: Recent Cases & Entity Topologies */}
        <SectionCard
          icon={FileText}
          iconColor="var(--emerald)"
          title="Recent Investigation Dossiers"
          subtitle="Court-admissible sealed cases and active evidentiary files"
          actions={
            <button className="btn btn-secondary btn-sm" onClick={() => onSwitchTab?.('cases')}>
              All Cases <ArrowRight size={13} />
            </button>
          }
        >
          {recentCases.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {recentCases.map((c) => (
                <div
                  key={c.case_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.6rem 0.8rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.78rem',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {c.title || c.case_id}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                      Target: <span className="mono">{c.target_id?.slice(0, 14)}…</span>
                    </div>
                  </div>
                  <StatusBadge status={c.status || 'NEW'} size="sm" />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="No Investigation Dossiers Open"
              description="Generate an autonomous forensic dossier from any suspicious entity in the Network Canvas."
              action={
                <button className="btn btn-secondary btn-sm" onClick={() => onSwitchTab?.('graph')}>
                  Select Entity
                </button>
              }
            />
          )}
        </SectionCard>
      </motion.div>
    </motion.div>
  );
}
