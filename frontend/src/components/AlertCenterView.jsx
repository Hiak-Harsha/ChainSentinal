import React, { useState } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  Sliders,
} from 'lucide-react';
import { CopyHash, RiskGauge, StatusBadge } from './shared';
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
      a.typologies?.some((t) => t.name.toLowerCase().includes(q));

    const matchesStatus = statusFilter === 'ALL' || a.status === statusFilter;
    const matchesGrade = gradeFilter === 'ALL' || a.confidence?.grade === gradeFilter;
    const priority = a.priority ?? a.risk_score ?? null;
    const matchesRisk = priority !== null ? priority >= minRisk : minRisk === 0;

    return matchesSearch && matchesStatus && matchesGrade && matchesRisk;
  });

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {/* Search & Filter Toolbar */}
      <div
        className="card"
        style={{
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
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

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

      {/* Alerts Table (Full Width, List-Only) */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <AlertTriangle size={18} style={{ color: 'var(--amber)' }} />
              Ranked Investigative Leads ({filteredAlerts.length})
            </div>
            <div className="card-subtitle">
              Section 7 NTRO Compliance &bull; Select any row to inspect SHAP rationale in the Inspector Panel
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Risk Score</th>
                <th>Alert ID</th>
                <th>Entity Target</th>
                <th>Detected Typology</th>
                <th>Conformal Grade</th>
                <th>Attributed Origin IP</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ padding: 'var(--space-6) var(--space-4)' }}>
                    <RadarEmptyState
                      title="FORENSIC RADAR ACTIVE"
                      subtitle="No anomalous transaction patterns detected matching current filter criteria."
                    />
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((a) => {
                  const priority = a.priority ?? a.risk_score ?? 0;
                  const topTyp = a.typologies?.[0]?.name || 'UNKNOWN';
                  const topStr = a.typologies?.[0]?.strength ?? 0;
                  const grade = a.confidence?.grade || 'B';
                  const ip = a.attribution?.ip || 'N/A';
                  const status = a.status || 'NEW';
                  const isSelected = selectedAlert?.alert_id === a.alert_id;

                  return (
                    <tr
                      key={a.alert_id}
                      onClick={() => onSelectAlert && onSelectAlert(a)}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? 'var(--bg-elevated)' : undefined,
                      }}
                    >
                      <td>
                        <RiskGauge score={priority} variant="bar" size="sm" showLabel={false} />
                      </td>
                      <td>
                        <CopyHash value={a.alert_id} label="Alert ID" truncateLength={5} />
                      </td>
                      <td>
                        <CopyHash value={a.entity_id} label="Entity Target" truncateLength={6} />
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <div style={{ padding: 'var(--space-1)', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.04)', display: 'flex' }}>
                            {getTypologyIcon(topTyp, { size: 18 })}
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-emphasis)' }}>
                              {topTyp.replace('T_', '').replace(/_/g, ' ')}
                            </span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                              P = {(topStr * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <StatusBadge
                          status={grade}
                          size="sm"
                          showDot={false}
                          className="font-bold"
                        />
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-main)' }}>
                            {ip}
                          </span>
                          {a.attribution?.country && (
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                              {a.attribution.country} &bull; {a.attribution.asn}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={status} size="sm" />
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectAlert) onSelectAlert(a);
                          }}
                        >
                          Deep Dive
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
