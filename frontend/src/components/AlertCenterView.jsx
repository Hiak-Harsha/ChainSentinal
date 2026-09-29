import React, { useState } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  Sliders,
  ShieldAlert,
  Flame,
  CheckCircle,
  Eye,
} from 'lucide-react';
import {
  PageHeader,
  PageToolbar,
  SectionCard,
  MetricCard,
  DataTable,
  CopyHash,
  RiskGauge,
  StatusBadge,
  ActionGroup,
} from './shared';
import { getTypologyIcon } from './visuals/icons';
import { RadarEmptyState } from './visuals/RadarEmptyState';

export default function AlertCenterView({
  alerts = [],
  selectedAlert,
  onSelectAlert,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [gradeFilter, setGradeFilter] = useState('ALL');
  const [minRisk, setMinRisk] = useState(0.0);

  // Filter alerts
  const filteredAlerts = alerts.filter((a) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !searchTerm ||
      a.alert_id?.toLowerCase().includes(q) ||
      a.entity_id?.toLowerCase().includes(q) ||
      a.attribution?.ip?.toLowerCase().includes(q) ||
      a.typology?.toLowerCase().includes(q) ||
      a.typologies?.some((t) => t.name.toLowerCase().includes(q));

    const matchesStatus = statusFilter === 'ALL' || a.status === statusFilter;
    const matchesGrade =
      gradeFilter === 'ALL' || a.confidence?.grade === gradeFilter;
    const priority = a.priority ?? a.risk_score ?? null;
    const matchesRisk = priority !== null ? priority >= minRisk : minRisk === 0;

    return matchesSearch && matchesStatus && matchesGrade && matchesRisk;
  });

  // Calculate alert overview telemetry
  const criticalCount = alerts.filter(
    (a) => (a.priority ?? a.risk_score ?? 0) >= 0.7
  ).length;
  const gradeACount = alerts.filter((a) => a.confidence?.grade === 'A').length;
  const newCount = alerts.filter((a) => (a.status || 'NEW') === 'NEW').length;
  const resolvedCount = alerts.filter(
    (a) => a.status === 'RESOLVED' || a.status === 'CLOSED_FALSE_POSITIVE'
  ).length;

  const alertColumns = [
    {
      header: 'Risk Score',
      key: 'priority',
      width: '120px',
      cell: (row) => {
        const priority = row.priority ?? row.risk_score ?? 0;
        return (
          <RiskGauge
            score={priority}
            variant="bar"
            size="sm"
            showLabel={false}
          />
        );
      },
    },
    {
      header: 'Alert ID',
      key: 'alert_id',
      sortable: true,
      cell: (row) => (
        <CopyHash value={row.alert_id} label="Alert ID" truncateLength={5} />
      ),
    },
    {
      header: 'Entity Target',
      key: 'entity_id',
      cell: (row) => (
        <CopyHash
          value={row.entity_id}
          label="Entity Target"
          truncateLength={6}
        />
      ),
    },
    {
      header: 'Detected Typology',
      key: 'typology',
      cell: (row) => {
        const topTyp =
          row.typologies?.[0]?.name || row.typology || 'UNKNOWN';
        const topStr = row.typologies?.[0]?.strength ?? row.typologies?.[0]?.score ?? 0;
        return (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}
          >
            <div
              style={{
                padding: 'var(--space-1)',
                borderRadius: '4px',
                background: 'rgba(255, 255, 255, 0.04)',
                display: 'flex',
              }}
            >
              {getTypologyIcon(topTyp, { size: 18 })}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                style={{
                  fontWeight: 600,
                  color: 'var(--text-emphasis)',
                }}
              >
                {topTyp.replace('T_', '').replace(/_/g, ' ')}
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                P = {(topStr * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        );
      },
    },
    {
      header: 'Conformal Grade',
      key: 'grade',
      width: '90px',
      cell: (row) => {
        const grade = row.confidence?.grade || 'B';
        return (
          <StatusBadge
            status={grade}
            size="sm"
            showDot={false}
            className="font-bold"
          />
        );
      },
    },
    {
      header: 'Attributed Origin IP',
      key: 'ip',
      cell: (row) => {
        const ip = row.attribution?.ip || 'N/A';
        return (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span
              className="mono"
              style={{ fontSize: '0.8rem', color: 'var(--text-main)' }}
            >
              {ip}
            </span>
            {row.attribution?.country && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                {row.attribution.country} &bull; {row.attribution.asn}
              </span>
            )}
          </div>
        );
      },
    },
    {
      header: 'Status',
      key: 'status',
      width: '100px',
      cell: (row) => <StatusBadge status={row.status || 'NEW'} size="sm" />,
    },
    {
      header: 'Action',
      key: 'action',
      width: '110px',
      cell: (row) => (
        <button
          className="btn btn-secondary btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            if (onSelectAlert) onSelectAlert(row);
          }}
        >
          Deep Dive
        </button>
      ),
    },
  ];

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}
    >
      {/* Page Header */}
      <PageHeader
        icon={AlertTriangle}
        title="Ranked Investigative Leads & Forensic Detection Alerts"
        subtitle="Autonomous graph neural network, typological rule inference, TreeSHAP explainability, and analyst triage queue."
      />

      {/* KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}
      >
        <MetricCard
          label="Active Leads"
          value={alerts.length}
          icon={AlertTriangle}
          accentColor="var(--btc-orange)"
          helper="Total detected leads in queue"
        />
        <MetricCard
          label="Critical Risk (≥ 70%)"
          value={criticalCount}
          icon={Flame}
          accentColor="var(--crimson)"
          helper="Urgent priority requiring immediate triage"
        />
        <MetricCard
          label="High Confidence (Grade A)"
          value={gradeACount}
          icon={ShieldAlert}
          accentColor="var(--emerald)"
          helper="Conformal coverage singleton predictions"
        />
        <MetricCard
          label="Pending Triage (New)"
          value={newCount}
          icon={Eye}
          accentColor="var(--color-primary)"
          helper="Unreviewed anomalous transactions"
        />
      </div>

      {/* Search & Filter Controls Toolbar */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            flex: 1,
            minWidth: '280px',
          }}
        >
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50)',
                color: 'var(--text-dim)',
              }}
            />
            <input
              type="text"
              className="input"
              style={{ width: '100%', paddingLeft: '2.25rem' }}
              placeholder="Search by Entity ID, Alert ID, IP, or Typology..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            flexWrap: 'wrap',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              fontSize: '0.82rem',
              color: 'var(--text-muted)',
            }}
          >
            <Filter size={15} />
            <span>Status:</span>
            <select
              className="select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">NEW</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="ESCALATED">ESCALATED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED_FALSE_POSITIVE">FALSE POSITIVE</option>
            </select>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              fontSize: '0.82rem',
              color: 'var(--text-muted)',
            }}
          >
            <Sliders size={15} />
            <span>Grade:</span>
            <select
              className="select"
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value)}
            >
              <option value="ALL">All Grades</option>
              <option value="A">Grade A (Singleton High Conf)</option>
              <option value="B">Grade B (Multi-class Moderate)</option>
              <option value="C">Grade C (Ambiguous / Uncertain)</option>
            </select>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              fontSize: '0.82rem',
              color: 'var(--text-muted)',
            }}
          >
            <span>Min Risk:</span>
            <select
              className="select"
              value={minRisk}
              onChange={(e) => setMinRisk(parseFloat(e.target.value))}
            >
              <option value="0.0">All (&ge; 0%)</option>
              <option value="0.4">Moderate (&ge; 40%)</option>
              <option value="0.7">Critical (&ge; 70%)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts Table Section Card */}
      <SectionCard
        icon={AlertTriangle}
        iconColor="var(--amber)"
        title={`Ranked Investigative Leads (${filteredAlerts.length})`}
        subtitle="Select any row to inspect SHAP rationale, topology graph, and attribution in the Inspector Panel."
      >
        {filteredAlerts.length === 0 ? (
          <div style={{ padding: '2rem 1rem' }}>
            <RadarEmptyState
              title="FORENSIC RADAR ACTIVE"
              subtitle="No anomalous transaction patterns detected matching current filter criteria."
            />
          </div>
        ) : (
          <DataTable
            columns={alertColumns}
            data={filteredAlerts}
            keyExtractor={(row) => row.alert_id}
            rowKey={(row) => row.alert_id}
            onRowClick={(row) => onSelectAlert && onSelectAlert(row)}
            selectedRowKey={selectedAlert?.alert_id}
            pageSize={15}
          />
        )}
      </SectionCard>
    </div>
  );
}
