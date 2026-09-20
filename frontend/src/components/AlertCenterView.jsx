import React, { useState } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  Copy,
  Check,
  ExternalLink,
  ShieldAlert,
  GitBranch,
  FileCheck,
  Radio,
  Clock,
  X,
} from 'lucide-react';
import { api } from '../api';

export default function AlertCenterView({
  alerts = [],
  selectedAlert,
  onSelectAlert,
  onCloseDetail,
  onLaunchTrace,
  onLaunchInvestigate,
  onStatusUpdated,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [gradeFilter, setGradeFilter] = useState('ALL');
  const [minRisk, setMinRisk] = useState(0.0);
  const [copiedHash, setCopiedHash] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

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
    const priority = a.priority || a.risk_score || 0;
    const matchesRisk = priority >= minRisk;

    return matchesSearch && matchesStatus && matchesGrade && matchesRisk;
  });

  const handleCopyHash = (hash) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleUpdateStatus = async (alertId, newStatus) => {
    setUpdatingStatus(true);
    try {
      await api.updateAlertStatus(alertId, newStatus);
      if (onStatusUpdated) onStatusUpdated(alertId, newStatus);
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div>
      {/* Search & Filter Toolbar */}
      <div
        className="card"
        style={{
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={16}
              style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }}
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <span>Min Priority:</span>
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

      {/* Alerts Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <AlertTriangle size={18} style={{ color: 'var(--amber)' }} />
              Ranked Investigative Leads ({filteredAlerts.length})
            </div>
            <div className="card-subtitle">
              Section 7 NTRO Compliance with Conformal Set Bounds &amp; SHAP Rationale
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Alert ID</th>
                <th>Entity Target</th>
                <th>Detected Typology</th>
                <th>Conformal Grade</th>
                <th>Attributed Origin IP</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '3rem' }}>
                    No alerts match your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((a) => {
                  const priority = a.priority || a.risk_score || 0;
                  const topTyp = a.typologies?.[0]?.name || 'UNKNOWN';
                  const topStr = a.typologies?.[0]?.strength || 0.0;
                  const grade = a.confidence?.grade || 'B';
                  const ip = a.attribution?.ip || 'N/A';
                  const status = a.status || 'NEW';

                  return (
                    <tr key={a.alert_id}>
                      <td>
                        <span
                          className={`badge ${
                            priority > 0.7
                              ? 'badge-crimson'
                              : priority > 0.4
                              ? 'badge-amber'
                              : 'badge-emerald'
                          }`}
                        >
                          {(priority * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {a.alert_id}
                        </span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700, color: '#fff' }}>
                          {a.entity_id}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontWeight: 600, color: 'var(--cyan-primary)' }}>
                            {topTyp.replace('T', '').replace(/_/g, ' ')}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                            P = {(topStr * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge-grade ${
                            grade === 'A'
                              ? 'badge-grade-a'
                              : grade === 'B'
                              ? 'badge-grade-b'
                              : 'badge-grade-c'
                          }`}
                          title={`Conformal Set: ${a.confidence?.conformal_set?.join(', ') || 'N/A'}`}
                        >
                          {grade}
                        </span>
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
                        <span
                          className={`badge ${
                            status === 'ESCALATED'
                              ? 'badge-crimson'
                              : status === 'INVESTIGATING'
                              ? 'badge-cyan'
                              : status === 'RESOLVED'
                              ? 'badge-emerald'
                              : 'badge-amber'
                          }`}
                        >
                          {status}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectAlert(a)}
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

      {/* Deep Dive Modal Dialog */}
      {selectedAlert && (
        <div className="modal-backdrop" onClick={onCloseDetail}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '1rem',
                marginBottom: '1.25rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <ShieldAlert size={20} style={{ color: 'var(--crimson)' }} />
                  <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>
                    Investigative Dossier: {selectedAlert.entity_id}
                  </h3>
                </div>
                <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                  Alert ID: {selectedAlert.alert_id} &bull; Priority: {((selectedAlert.priority || selectedAlert.risk_score || 0) * 100).toFixed(1)}%
                </div>
              </div>

              <button
                className="btn btn-secondary btn-sm"
                onClick={onCloseDetail}
                style={{ padding: '0.35rem 0.5rem' }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Quick Actions & Triage Status Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.75rem',
                background: 'rgba(255, 255, 255, 0.02)',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                marginBottom: '1.25rem',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                <Clock size={15} style={{ color: 'var(--cyan-primary)' }} />
                <span>Triage Status:</span>
                <select
                  className="select"
                  value={selectedAlert.status || 'NEW'}
                  disabled={updatingStatus}
                  onChange={(e) => handleUpdateStatus(selectedAlert.alert_id, e.target.value)}
                >
                  <option value="NEW">NEW</option>
                  <option value="INVESTIGATING">INVESTIGATING</option>
                  <option value="ESCALATED">ESCALATED</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="CLOSED_FALSE_POSITIVE">FALSE POSITIVE</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onLaunchTrace(selectedAlert.entity_id)}
                >
                  <GitBranch size={14} />
                  Trace Taint Flows
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onLaunchInvestigate(selectedAlert.entity_id)}
                >
                  <FileCheck size={14} />
                  Build Case Dossier
                </button>
              </div>
            </div>

            {/* Modal Body: 2 Columns */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
              {/* Left Column: AI Decision & Conformal Guarantees */}
              <div>
                {/* Conformal Reliability Card */}
                <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.6rem', color: 'var(--text-main)' }}>
                    Conformal Mathematical Reliability
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
                    <div
                      className={`badge-grade ${
                        selectedAlert.confidence?.grade === 'A'
                          ? 'badge-grade-a'
                          : selectedAlert.confidence?.grade === 'B'
                          ? 'badge-grade-b'
                          : 'badge-grade-c'
                      }`}
                      style={{ width: '38px', height: '38px', fontSize: '1.2rem' }}
                    >
                      {selectedAlert.confidence?.grade || 'B'}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#fff' }}>
                        Grade {selectedAlert.confidence?.grade || 'B'} Classification
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Guaranteed 90% coverage prediction set:
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {selectedAlert.confidence?.conformal_set?.map((cls) => (
                      <span key={cls} className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                        {cls.replace('T', '').replace(/_/g, ' ')}
                      </span>
                    )) || <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>No set recorded</span>}
                  </div>
                </div>

                {/* Network Attribution Card */}
                <div className="card" style={{ padding: '1rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Radio size={16} style={{ color: 'var(--purple-primary)' }} />
                    Network-Layer Attribution
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.82rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Estimated Origin IP:</span>
                      <span className="mono" style={{ fontWeight: 700, color: 'var(--cyan-primary)' }}>
                        {selectedAlert.attribution?.ip || 'N/A'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Location &amp; ASN:</span>
                      <span>
                        {selectedAlert.attribution?.country || 'Unknown'}, {selectedAlert.attribution?.asn || 'N/A'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Confidence / Posterior:</span>
                      <span className="mono">
                        {((selectedAlert.attribution?.confidence || selectedAlert.attribution?.score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Derivation Basis:</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        {selectedAlert.attribution?.derivation || 'TF-IDF broadcast de-biasing'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: TreeSHAP Feature Attributions & Evidence */}
              <div>
                <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.75rem', color: 'var(--text-main)' }}>
                    TreeSHAP Forensic Risk Drivers
                  </div>

                  {selectedAlert.reasons && selectedAlert.reasons.length > 0 ? (
                    selectedAlert.reasons.map((r, idx) => {
                      const shap = r.shap_value || 0.0;
                      const isPositive = shap >= 0;
                      const pctWidth = Math.min(100, Math.max(15, Math.abs(shap) * 60));

                      return (
                        <div key={idx} style={{ marginBottom: '0.75rem' }}>
                          <div className="shap-bar-row">
                            <span className="shap-label" title={r.feature}>
                              {r.feature?.replace(/_/g, ' ')}
                            </span>
                            <div className="shap-bar-track">
                              <div
                                className={`shap-bar-fill ${!isPositive ? 'negative' : ''}`}
                                style={{ width: `${pctWidth}%` }}
                              ></div>
                            </div>
                            <span className="shap-val">
                              {isPositive ? `+${shap.toFixed(2)}` : shap.toFixed(2)}
                            </span>
                          </div>

                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', paddingLeft: '0.25rem' }}>
                            {r.text} &bull;{' '}
                            <span style={{ color: 'var(--amber)', fontWeight: 600 }}>
                              {r.percentile?.toFixed(1) || 95}% percentile
                            </span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                      No granular SHAP feature attributions available for this record.
                    </div>
                  )}
                </div>

                {/* Evidence Bundle Hash */}
                <div className="card" style={{ padding: '1rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>
                    Tamper-Evident Evidence Digest
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>
                    SHA-256 canonical hash of the investigative evidence bundle:
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      background: 'rgba(0, 0, 0, 0.4)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--cyan-primary)', wordBreak: 'break-all', flex: 1 }}>
                      {selectedAlert.evidence?.bundle_hash || 'SHA256-DIGEST-PENDING'}
                    </span>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleCopyHash(selectedAlert.evidence?.bundle_hash)}
                      title="Copy SHA-256 Bundle Hash"
                    >
                      {copiedHash ? <Check size={14} style={{ color: 'var(--emerald)' }} /> : <Copy size={14} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
