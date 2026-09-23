import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Shield,
  AlertTriangle,
  GitBranch,
  FolderOpen,
  Search as SearchIcon,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { RiskGauge, StatusBadge, CopyHash } from '../shared';
import ShapWaterfall from '../process/ShapWaterfall';

function truncateId(id, maxLen = 18) {
  if (!id || id.length <= maxLen) return id;
  return `${id.slice(0, 10)}\u2026${id.slice(-6)}`;
}

/**
 * InspectorPanel — Persistent right drawer showing context for the current selection.
 * Renders different content depending on `selection.type`:
 *   - 'entity'  → metadata, risk gauge, similar entities, actions
 *   - 'alert'   → alert detail, triage, SHAP explanation
 *   - 'trace'   → trace hops + decay
 *   - 'case'    → case timeline + entities
 *   - null      → empty prompt
 */
export default function InspectorPanel({
  selection,
  onClearSelection,
  // Entity data
  entityDetail,
  similarEntities,
  // Alert data
  alertDetail,
  onAlertAction,
  // Trace data
  traceDetail,
  // Case data
  caseDetail,
  // Actions
  onLaunchTrace,
  onInvestigate,
}) {
  if (!selection) {
    return (
      <aside className="inspector-panel" id="inspector-panel">
        <div className="inspector-empty">
          <Shield size={48} style={{ color: 'var(--text-dim)', opacity: 0.3 }} />
          <div style={{ fontWeight: 600 }}>No Selection</div>
          <div style={{ fontSize: '0.75rem' }}>
            Click an entity, alert, or trace result to inspect it here.
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="inspector-panel" id="inspector-panel">
      <AnimatePresence mode="wait">
        <motion.div
          key={`${selection.type}-${selection.id}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
          style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
        >
          {/* Header */}
          <div className="inspector-header">
            <h3>
              {selection.type === 'entity' && <Shield size={15} />}
              {selection.type === 'alert' && <AlertTriangle size={15} />}
              {selection.type === 'trace' && <GitBranch size={15} />}
              {selection.type === 'case' && <FolderOpen size={15} />}
              <span style={{ textTransform: 'capitalize' }}>{selection.type}</span>
              <CopyHash hash={selection.id} truncate={14} />
            </h3>
            <button className="inspector-close-btn" onClick={onClearSelection} title="Clear selection">
              <X size={16} />
            </button>
          </div>

          {/* ========== ENTITY INSPECTOR ========== */}
          {selection.type === 'entity' && entityDetail && (
            <>
              <div className="inspector-section">
                <div className="inspector-section-title">Risk Assessment</div>
                <div style={{ display: 'flex', justifyContent: 'center', padding: '0.5rem 0' }}>
                  <RiskGauge score={entityDetail.risk_score} size={100} />
                </div>
              </div>

              <div className="inspector-section">
                <div className="inspector-section-title">Metadata</div>
                <table style={{ width: '100%', fontSize: '0.78rem' }}>
                  <tbody>
                    {[
                      ['Type', entityDetail.entity_type],
                      ['Addresses', entityDetail.member_count ?? '—'],
                      ['Received', typeof entityDetail.total_received_sat === 'number' ? `${(entityDetail.total_received_sat / 1e8).toFixed(4)} BTC` : '—'],
                      ['Sent', typeof entityDetail.total_sent_sat === 'number' ? `${(entityDetail.total_sent_sat / 1e8).toFixed(4)} BTC` : '—'],
                    ].map(([label, val]) => (
                      <tr key={label}>
                        <td style={{ color: 'var(--text-dim)', paddingRight: '0.75rem', paddingBottom: '0.35rem' }}>{label}</td>
                        <td style={{ fontWeight: 600, fontFamily: 'monospace', paddingBottom: '0.35rem' }}>{val}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {similarEntities && similarEntities.length > 0 && (
                <div className="inspector-section">
                  <div className="inspector-section-title">Similar Entities</div>
                  {similarEntities.slice(0, 4).map((se) => (
                    <div
                      key={se.entity_id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0.3rem 0',
                        fontSize: '0.75rem',
                        borderBottom: '1px solid rgba(255,255,255,0.03)',
                      }}
                    >
                      <span className="mono" style={{ color: 'var(--text-muted)' }}>
                        {truncateId(se.entity_id)}
                      </span>
                      <span style={{ color: 'var(--btc-orange)', fontWeight: 700 }}>
                        {(se.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onLaunchTrace && onLaunchTrace(entityDetail.entity_id)}
                >
                  <GitBranch size={13} /> Trace
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onInvestigate && onInvestigate(entityDetail.entity_id)}
                >
                  <SearchIcon size={13} /> Investigate
                </button>
              </div>
            </>
          )}

          {/* ========== ALERT INSPECTOR ========== */}
          {selection.type === 'alert' && alertDetail && (
            <>
              <div className="inspector-section">
                <div className="inspector-section-title">Alert Summary</div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                  {alertDetail.rule || 'Detection Alert'}
                </div>
                <StatusBadge
                  status={alertDetail.status || 'new'}
                  variant={alertDetail.priority >= 4 ? 'crimson' : alertDetail.priority >= 2 ? 'amber' : 'emerald'}
                />
                <div style={{ marginTop: '0.75rem' }}>
                  <RiskGauge score={alertDetail.risk_score} size={80} />
                </div>
              </div>

              <div className="inspector-section">
                <div className="inspector-section-title">Triage Actions</div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-sm"
                    style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--emerald)', border: '1px solid rgba(16,185,129,0.3)' }}
                    onClick={() => onAlertAction && onAlertAction(alertDetail.alert_id, 'confirmed_malicious')}
                  >
                    <ThumbsUp size={13} /> Confirm
                  </button>
                  <button
                    className="btn btn-sm"
                    style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--crimson)', border: '1px solid rgba(239,68,68,0.3)' }}
                    onClick={() => onAlertAction && onAlertAction(alertDetail.alert_id, 'false_positive')}
                  >
                    <ThumbsDown size={13} /> Dismiss
                  </button>
                </div>
              </div>

              {alertDetail.explanation && alertDetail.explanation.length > 0 && (
                <div className="inspector-section">
                  <div className="inspector-section-title">TreeSHAP Feature Contributions</div>
                  <ShapWaterfall
                    reasons={alertDetail.explanation}
                    baseValue={0.35}
                    finalScore={typeof alertDetail.risk_score === 'number' ? alertDetail.risk_score : 0}
                  />
                </div>
              )}
            </>
          )}

          {/* ========== TRACE INSPECTOR ========== */}
          {selection.type === 'trace' && traceDetail && (
            <>
              <div className="inspector-section">
                <div className="inspector-section-title">Trace Summary</div>
                <table style={{ width: '100%', fontSize: '0.78rem' }}>
                  <tbody>
                    {[
                      ['Method', traceDetail.method],
                      ['Hops', traceDetail.hops ? traceDetail.hops.length : '—'],
                      ['Decay', traceDetail.decay_type || 'proportional'],
                      ['Origin', truncateId(traceDetail.origin)],
                    ].map(([label, val]) => (
                      <tr key={label}>
                        <td style={{ color: 'var(--text-dim)', paddingRight: '0.75rem', paddingBottom: '0.35rem' }}>{label}</td>
                        <td style={{ fontWeight: 600, fontFamily: 'monospace', paddingBottom: '0.35rem' }}>{String(val)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {traceDetail.hops && traceDetail.hops.length > 0 && (
                <div className="inspector-section">
                  <div className="inspector-section-title">Hop Decay</div>
                  {traceDetail.hops.map((hop, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0.25rem 0',
                        fontSize: '0.75rem',
                        borderBottom: '1px solid rgba(255,255,255,0.03)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Hop {i + 1}</span>
                      <span className="mono" style={{ color: 'var(--btc-orange)' }}>
                        {typeof hop.amount === 'number' ? `${(hop.amount / 1e8).toFixed(6)} BTC` : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* ========== CASE INSPECTOR ========== */}
          {selection.type === 'case' && caseDetail && (
            <>
              <div className="inspector-section">
                <div className="inspector-section-title">Case Details</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                  {caseDetail.title || `Case ${truncateId(caseDetail.case_id)}`}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  {caseDetail.entities ? caseDetail.entities.length : 0} entities &bull; {caseDetail.timeline ? caseDetail.timeline.length : 0} events
                </div>
              </div>

              {caseDetail.timeline && caseDetail.timeline.length > 0 && (
                <div className="inspector-section">
                  <div className="inspector-section-title">Timeline</div>
                  {caseDetail.timeline.slice(0, 8).map((evt, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '0.35rem 0',
                        fontSize: '0.72rem',
                        borderLeft: '2px solid var(--btc-orange)',
                        paddingLeft: '0.6rem',
                        marginBottom: '0.3rem',
                      }}
                    >
                      <div style={{ color: 'var(--text-dim)', fontSize: '0.65rem' }}>
                        {evt.timestamp ? new Date(evt.timestamp * 1000).toLocaleString() : ''}
                      </div>
                      <div style={{ color: 'var(--text-main)' }}>{evt.description || evt.type}</div>
                    </div>
                  ))}
                </div>
              )}

              <button className="btn btn-secondary btn-sm" style={{ width: '100%' }}>
                <ExternalLink size={13} /> Export Dossier
              </button>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </aside>
  );
}
