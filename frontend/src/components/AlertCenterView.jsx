import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertTriangle,
  Search,
  Filter,
  ShieldAlert,
  GitBranch,
  FileCheck,
  Radio,
  Clock,
  X,
  Sliders,
} from 'lucide-react';
import { api } from '../api';
import { CopyHash, RiskGauge, StatusBadge, useToast } from './shared';

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
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const toast = useToast();

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

  const handleUpdateStatus = async (alertId, newStatus) => {
    setUpdatingStatus(true);
    try {
      await api.updateAlertStatus(alertId, newStatus);
      if (onStatusUpdated) onStatusUpdated(alertId, newStatus);
    } catch (err) {
      toast?.showToast(`Failed to update status: ${err.message}`, 'error');
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
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
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flex: 1, minWidth: '280px' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
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

      {/* Alerts Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <AlertTriangle size={18} style={{ color: 'var(--amber)' }} />
              Ranked Investigative Leads ({filteredAlerts.length})
            </div>
            <div className="card-subtitle">
              Section 7 NTRO Compliance with Conformal Set Bounds &amp; TreeSHAP Rationale
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
                  const priority = a.priority ?? a.risk_score ?? 0;
                  const topTyp = a.typologies?.[0]?.name || 'UNKNOWN';
                  const topStr = a.typologies?.[0]?.strength ?? 0;
                  const grade = a.confidence?.grade || 'B';
                  const ip = a.attribution?.ip || 'N/A';
                  const status = a.status || 'NEW';

                  return (
                    <tr key={a.alert_id}>
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
      <AnimatePresence>
        {selectedAlert && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onCloseDetail}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(6, 9, 17, 0.75)',
              backdropFilter: 'blur(6px)',
              zIndex: 999,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1.5rem',
            }}
          >
            <motion.div
              className="modal-card"
              initial={{ scale: 0.95, opacity: 0, y: 15 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 15 }}
              transition={{ type: 'spring', stiffness: 450, damping: 30 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                width: '100%',
                maxWidth: '920px',
                maxHeight: '90vh',
                overflowY: 'auto',
                backgroundColor: '#0b1120',
                border: '1px solid rgba(0, 240, 255, 0.25)',
                borderRadius: '12px',
                padding: '1.5rem',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
              }}
            >
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
                    <ShieldAlert size={22} style={{ color: 'var(--crimson)' }} />
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
                      Investigative Dossier: {selectedAlert.entity_id}
                    </h3>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.35rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Alert:</span>
                    <CopyHash value={selectedAlert.alert_id} label="Alert ID" truncateLength={8} />
                  </div>
                </div>

                <button
                  className="btn btn-secondary btn-sm"
                  onClick={onCloseDetail}
                  style={{ padding: '0.35rem 0.5rem' }}
                  aria-label="Close detail modal"
                >
                  <X size={18} />
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
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem' }}>
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

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
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
                  {/* Risk & Conformal Reliability Card */}
                  <div className="card" style={{ marginBottom: '1rem', padding: '1.25rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '1rem', color: 'var(--text-main)' }}>
                      Risk Magnitude &amp; Statistical Reliability
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around', marginBottom: '1.25rem' }}>
                      <RiskGauge
                        score={selectedAlert.priority ?? selectedAlert.risk_score ?? 0}
                        variant="radial"
                        size="lg"
                      />

                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.35rem' }}>
                        <StatusBadge
                          status={selectedAlert.confidence?.grade || 'B'}
                          size="md"
                          showDot={false}
                          className="font-bold"
                        />
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                          Conformal Reliability
                        </span>
                      </div>
                    </div>

                    <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '0.75rem' }}>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                        Guaranteed 90% coverage prediction set:
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {selectedAlert.confidence?.conformal_set?.map((cls) => (
                          <span key={cls} className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                            {cls.replace('T', '').replace(/_/g, ' ')}
                          </span>
                        )) || <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>No set recorded</span>}
                      </div>
                    </div>
                  </div>

                  {/* Network Attribution Card */}
                  <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Radio size={16} style={{ color: 'var(--purple-primary)' }} />
                      Network-Layer Attribution
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.82rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Origin IP:</span>
                        <CopyHash value={selectedAlert.attribution?.ip || 'N/A'} label="IP Address" />
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
                          {selectedAlert.attribution?.confidence != null
                            ? `${(selectedAlert.attribution.confidence * 100).toFixed(1)}%`
                            : selectedAlert.attribution?.score != null
                            ? `${(selectedAlert.attribution.score * 100).toFixed(1)}%`
                            : '—'}
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
                  <div className="card" style={{ marginBottom: '1rem', padding: '1.25rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '0.85rem', color: 'var(--text-main)' }}>
                      TreeSHAP Forensic Risk Drivers
                    </div>

                    {selectedAlert.reasons && selectedAlert.reasons.length > 0 ? (
                      selectedAlert.reasons.map((r, idx) => {
                        const hasShap = r.shap_value !== undefined && r.shap_value !== null;
                        const shap = hasShap ? r.shap_value : null;
                        const isPositive = shap !== null && shap >= 0;
                        const pctWidth = shap !== null ? Math.min(100, Math.max(12, Math.abs(shap) * 65)) : 0;

                        return (
                          <div key={idx} style={{ marginBottom: '0.85rem' }}>
                            <div className="shap-bar-row">
                              <span className="shap-label" title={r.feature}>
                                {r.feature?.replace(/_/g, ' ')}
                              </span>
                              <div className="shap-bar-track" style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.06)', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                                {shap !== null && (
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${pctWidth}%` }}
                                    transition={{ duration: 0.5, delay: idx * 0.05 }}
                                    style={{
                                      height: '100%',
                                      backgroundColor: isPositive ? 'var(--cyan-primary)' : 'var(--crimson)',
                                      borderRadius: '4px',
                                      boxShadow: `0 0 6px ${isPositive ? 'var(--cyan-primary)' : 'var(--crimson)'}`,
                                    }}
                                  />
                                )}
                              </div>
                              <span className="shap-val" style={{ fontFamily: 'monospace', fontSize: '0.75rem', minWidth: '42px', textAlign: 'right' }}>
                                {shap !== null ? (isPositive ? `+${shap.toFixed(2)}` : shap.toFixed(2)) : '—'}
                              </span>
                            </div>

                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', paddingLeft: '0.25rem', marginTop: '0.2rem' }}>
                              {r.text}
                              {r.percentile != null && (
                                <>
                                  {' '}&bull;{' '}
                                  <span style={{ color: 'var(--amber)', fontWeight: 600 }}>
                                    {r.percentile.toFixed(1)}% percentile
                                  </span>
                                </>
                              )}
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
                  <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '0.4rem', color: 'var(--text-main)' }}>
                      Tamper-Evident Evidence Digest
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>
                      SHA-256 canonical hash of the investigative evidence bundle:
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <CopyHash
                        value={selectedAlert.evidence?.bundle_hash || 'SHA256-DIGEST-PENDING'}
                        label="Bundle Hash"
                        truncate={false}
                        className="w-full justify-between"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
