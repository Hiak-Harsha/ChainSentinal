import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  GitBranch,
  ArrowRight,
  TrendingDown,
  Navigation,
  Play,
  CheckCircle2,
  Sliders,
} from 'lucide-react';
import { AnimatedNumber, CopyHash, StatusBadge, useToast } from './shared';
import { BTCCoinIcon, TaintFlowIcon, BlockLedgerIcon } from './visuals/icons';
import TaintDecayVisualizer from './process/TaintDecayVisualizer';

export default function TaintPathfinderView({ prefilledTarget = '', onTraceCompleted }) {
  const [subTab, setSubTab] = useState('taint'); // 'taint' or 'path'

  // Taint Trace State
  const [target, setTarget] = useState(prefilledTarget || '');
  const [direction, setDirection] = useState('forward');
  const [decayModel, setDecayModel] = useState('proportional');
  const [maxHops, setMaxHops] = useState(4);
  const [amount, setAmount] = useState('');
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [traceResult, setTraceResult] = useState(null);

  // Pathfinder State
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [pathStrategy, setPathStrategy] = useState('highest_volume');
  const [loadingPath, setLoadingPath] = useState(false);
  const [pathResult, setPathResult] = useState(null);

  const toast = useToast();

  const handleRunTrace = async () => {
    if (!target) return;
    setLoadingTrace(true);
    setTraceResult(null);
    toast?.showToast(`Initiating ${decayModel} taint analysis for ${target.slice(0, 10)}...`, 'info');
    try {
      const res = await api.runTrace({
        target: target.trim(),
        direction,
        decay_model: decayModel,
        max_hops: parseInt(maxHops),
        amount: amount ? parseInt(amount) : null,
      });
      setTraceResult(res);
      if (onTraceCompleted) onTraceCompleted(res);
      toast?.showToast(`Trace complete: ${res.hops?.length ?? 0} downstream hops mapped`, 'success');
    } catch (err) {
      toast?.showToast(`Trace failed: ${err.message}`, 'error');
    } finally {
      setLoadingTrace(false);
    }
  };

  const handleComputePath = async () => {
    if (!pathSource || !pathTarget) return;
    setLoadingPath(true);
    setPathResult(null);
    toast?.showToast('Computing optimal forensic flow corridor...', 'info');
    try {
      const res = await api.computePath({
        source: pathSource.trim(),
        target: pathTarget.trim(),
        strategy: pathStrategy,
      });
      setPathResult(res);
      if (res.found) {
        toast?.showToast(`Forensic route discovered (${res.hop_count} hops)`, 'success');
      } else {
        toast?.showToast('No directed route found between entities in dataset', 'info');
      }
    } catch (err) {
      toast?.showToast(`Path computation failed: ${err.message}`, 'error');
    } finally {
      setLoadingPath(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Sub-navigation Switcher */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <button
          className={`btn ${subTab === 'taint' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setSubTab('taint')}
        >
          <TrendingDown size={15} />
          Multi-Model Taint Tracker
        </button>
        <button
          className={`btn ${subTab === 'path' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setSubTab('path')}
        >
          <Navigation size={15} />
          Forensic Route Pathfinder
        </button>
      </div>

      <AnimatePresence mode="wait">
        {subTab === 'taint' ? (
          /* TAINT TRACKER VIEW */
          <motion.div
            key="taint-view"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            {/* Configuration Form Card */}
            <div className="card" style={{ marginBottom: '1.5rem', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)' }}>
              <div className="card-header">
                <div>
                  <div className="card-title">
                    <GitBranch size={18} style={{ color: 'var(--btc-orange)' }} />
                    Dynamic Taint Dispersion Simulator
                  </div>
                  <div className="card-subtitle">
                    Trace tainted fund propagation downstream or backtrack funding origins upstream
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Target Identifier (Entity ID, Address, or TXID)
                  </label>
                  <input
                    type="text"
                    className="input mono"
                    style={{ width: '100%' }}
                    placeholder="e.g. ENT_fb65f697c5b3 or bc1q..."
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Direction
                  </label>
                  <select
                    className="select"
                    style={{ width: '100%' }}
                    value={direction}
                    onChange={(e) => setDirection(e.target.value)}
                  >
                    <option value="forward">Forward (Cash-out Flows)</option>
                    <option value="backward">Backward (Funding Sources)</option>
                    <option value="both">Both (Dual Horizon)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Decay Propagation Model
                  </label>
                  <select
                    className="select"
                    style={{ width: '100%' }}
                    value={decayModel}
                    onChange={(e) => setDecayModel(e.target.value)}
                  >
                    <option value="proportional">Proportional (Haircut Model)</option>
                    <option value="fifo">FIFO (Chronological Serialization)</option>
                    <option value="poison">Poison (All-or-Nothing 100%)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Max Exploration Hops: {maxHops}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={maxHops}
                    onChange={(e) => setMaxHops(e.target.value)}
                    style={{ width: '100%', marginTop: '0.5rem' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Initial Taint Satoshis (Optional)
                  </label>
                  <input
                    type="number"
                    className="input mono"
                    style={{ width: '100%' }}
                    placeholder="Auto (Full Balance)"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </div>
              </div>

              {/* Active Model Physics Callout */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.65rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background:
                    decayModel === 'poison'
                      ? 'rgba(239, 68, 68, 0.08)'
                      : decayModel === 'fifo'
                      ? 'rgba(245, 158, 11, 0.08)'
                      : 'rgba(0, 242, 254, 0.08)',
                  border: `1px solid ${
                    decayModel === 'poison'
                      ? 'rgba(239, 68, 68, 0.3)'
                      : decayModel === 'fifo'
                      ? 'rgba(245, 158, 11, 0.3)'
                      : 'rgba(0, 242, 254, 0.3)'
                  }`,
                  marginBottom: '1.25rem',
                  fontSize: '0.78rem',
                }}
              >
                <TaintFlowIcon
                  size={18}
                  color={
                    decayModel === 'poison'
                      ? 'var(--crimson)'
                      : decayModel === 'fifo'
                      ? 'var(--amber)'
                      : 'var(--btc-orange)'
                  }
                />
                <div>
                  <span style={{ fontWeight: 700, textTransform: 'uppercase', color: '#fff' }}>
                    {decayModel === 'poison' && 'Poison Law: '}
                    {decayModel === 'fifo' && 'FIFO Chronological Law: '}
                    {decayModel === 'proportional' && 'Proportional Haircut Law: '}
                  </span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {decayModel === 'poison' && 'Contaminates 100% of all downstream outputs regardless of co-mingled clean balances.'}
                    {decayModel === 'fifo' && 'Tracks serial output spending in strict chronological FIFO UTXO sequence.'}
                    {decayModel === 'proportional' && 'Dilutes taint fraction across output splits based on input value ratio.'}
                  </span>
                </div>
              </div>

              <button
                id="btn-execute-trace"
                className="btn btn-primary"
                onClick={handleRunTrace}
                disabled={loadingTrace || !target}
              >
                <Play size={15} />
                {loadingTrace ? 'Tracking Satoshi Propagation...' : 'Execute Taint Trace'}
              </button>
            </div>

            {/* Trace Results */}
            {traceResult && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
              >
                {/* Summary KPIs */}
                <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
                  <div className="card kpi-card cyan">
                    <div className="kpi-top">
                      <span>Traversed Hops</span>
                    </div>
                    <div className="kpi-value mono" style={{ color: 'var(--btc-orange)' }}>
                      <AnimatedNumber value={traceResult.hops?.length ?? 0} />
                    </div>
                    <div className="kpi-meta">
                      Direction: {traceResult.summary?.direction}
                    </div>
                  </div>

                  <div className="card kpi-card crimson">
                    <div className="kpi-top">
                      <span>Cashout Exchanges</span>
                    </div>
                    <div className="kpi-value mono" style={{ color: 'var(--crimson)' }}>
                      <AnimatedNumber value={traceResult.summary?.cashout_exchanges?.length ?? 0} />
                    </div>
                    <div className="kpi-meta">
                      {traceResult.summary?.cashout_exchanges?.join(', ') || 'None in Horizon'}
                    </div>
                  </div>

                  <div className="card kpi-card emerald">
                    <div className="kpi-top">
                      <span>Terminal Endpoints</span>
                    </div>
                    <div className="kpi-value mono" style={{ color: 'var(--emerald)' }}>
                      <AnimatedNumber value={traceResult.endpoints?.length ?? 0} />
                    </div>
                    <div className="kpi-meta">
                      Dormant / Exchange Deposited
                    </div>
                  </div>

                  <div className="card kpi-card purple">
                    <div className="kpi-top">
                      <span>Decay Algorithm</span>
                    </div>
                    <div className="kpi-value mono" style={{ color: 'var(--btc-gold)', textTransform: 'uppercase', fontSize: '1.25rem' }}>
                      {traceResult.summary?.decay_model}
                    </div>
                    <div className="kpi-meta">
                      <CopyHash value={traceResult.trace_id} label="Trace ID" truncateLength={6} />
                    </div>
                  </div>
                </div>

                {/* Taint Saturation Decay Corridor */}
                {traceResult.hops && traceResult.hops.length > 0 && (
                  <TaintDecayVisualizer
                    hops={traceResult.hops}
                    decayModel={traceResult.summary?.decay_model || decayModel}
                  />
                )}

                {/* Horizontal Hop Conduit */}
                {traceResult.hops && traceResult.hops.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.65rem',
                      overflowX: 'auto',
                      padding: '1rem',
                      background: 'rgba(6, 9, 17, 0.7)',
                      borderRadius: 'var(--radius-lg)',
                      border: '1px solid rgba(0, 242, 254, 0.2)',
                      marginBottom: '1.5rem',
                    }}
                  >
                    {traceResult.hops.map((h, i) => (
                      <React.Fragment key={i}>
                        <div
                          style={{
                            padding: '0.65rem 0.9rem',
                            borderRadius: 'var(--radius-md)',
                            background: 'rgba(15, 23, 42, 0.85)',
                            border: `1px solid ${h.taint_pct > 50 ? 'rgba(239, 68, 68, 0.45)' : 'rgba(0, 242, 254, 0.35)'}`,
                            minWidth: '170px',
                            flexShrink: 0,
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                            <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>Hop {h.hop_index}</span>
                            <span style={{ fontSize: '0.72rem', fontWeight: 800, color: h.taint_pct > 50 ? 'var(--crimson)' : 'var(--amber)' }}>
                              {h.taint_pct}% Taint
                            </span>
                          </div>
                          <div className="mono" style={{ fontSize: '0.75rem', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {h.to_entity}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--btc-orange)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                            <BTCCoinIcon size={12} />
                            <span>{h.transferred_sat != null ? `${(h.transferred_sat / 1e8).toFixed(4)} BTC` : '—'}</span>
                          </div>
                        </div>
                        {i < traceResult.hops.length - 1 && (
                          <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, padding: '0 0.3rem' }}>
                            <div className="satoshi-packet" style={{ color: 'var(--btc-orange)', fontSize: '0.75rem' }}>●</div>
                            <div style={{ width: '18px', height: '2px', background: 'var(--btc-orange)', opacity: 0.5 }} />
                          </div>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                )}

                {/* Step-by-Step Flow List */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <TrendingDown size={18} style={{ color: 'var(--btc-orange)' }} />
                      Multi-Hop Taint Flow Ledger ({traceResult.hops?.length ?? 0} Steps)
                    </div>
                  </div>

                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Hop</th>
                          <th>Source Entity</th>
                          <th>Target Entity</th>
                          <th>Volume &amp; Taint %</th>
                          <th>Dwell Time</th>
                          <th>Origin IP</th>
                          <th>Terminal Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {traceResult.hops?.length === 0 ? (
                          <tr>
                            <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' }}>
                              No downstream movements detected for this target within the selected hop horizon.
                            </td>
                          </tr>
                        ) : (
                          traceResult.hops.map((h, i) => (
                            <tr key={i}>
                              <td>
                                <span className="badge badge-cyan">Hop {h.hop_index}</span>
                              </td>
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                  <CopyHash value={h.from_entity} label="Source Entity" truncateLength={6} />
                                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{h.from_entity_type}</span>
                                </div>
                              </td>
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                  <CopyHash value={h.to_entity} label="Target Entity" truncateLength={6} />
                                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{h.to_entity_type}</span>
                                </div>
                              </td>
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                  <span className="mono" style={{ fontWeight: 700 }}>
                                    {h.transferred_sat != null ? h.transferred_sat.toLocaleString() : '—'} sat
                                  </span>
                                  <span style={{ fontSize: '0.75rem', color: h.taint_pct > 50 ? 'var(--crimson)' : 'var(--amber)' }}>
                                    {h.taint_pct != null ? `${h.taint_pct}% Tainted` : 'Taint N/A'}{' '}
                                    ({h.tainted_sat != null ? `${h.tainted_sat.toLocaleString()} sat` : '—'})
                                  </span>
                                </div>
                              </td>
                              <td>
                                <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                  {h.dwell_time_sec}s
                                </span>
                              </td>
                              <td>
                                <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--btc-gold)' }}>
                                  {h.origin_ip || 'UNKNOWN'}
                                </span>
                              </td>
                              <td>
                                {h.stop_reason ? (
                                  <StatusBadge status={h.stop_reason} size="sm" />
                                ) : (
                                  <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Active Flow</span>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        ) : (
          /* PATHFINDER VIEW */
          <motion.div
            key="path-view"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            <div className="card" style={{ marginBottom: '1.5rem', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)' }}>
              <div className="card-header">
                <div>
                  <div className="card-title">
                    <Navigation size={18} style={{ color: 'var(--btc-orange)' }} />
                    Forensic Corridor &amp; Bottleneck Pathfinder
                  </div>
                  <div className="card-subtitle">
                    Calculates shortest path or maximum bottleneck capacity (Widest Path) between entities
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Source Identifier (Entity ID, Address, or TXID)
                  </label>
                  <input
                    type="text"
                    className="input mono"
                    style={{ width: '100%' }}
                    placeholder="e.g. ENT_fb65f697c5b3"
                    value={pathSource}
                    onChange={(e) => setPathSource(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Target Identifier (Entity ID, Address, or TXID)
                  </label>
                  <input
                    type="text"
                    className="input mono"
                    style={{ width: '100%' }}
                    placeholder="e.g. ENT_02787a673ae0"
                    value={pathTarget}
                    onChange={(e) => setPathTarget(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Algorithm Strategy
                  </label>
                  <select
                    className="select"
                    style={{ width: '100%' }}
                    value={pathStrategy}
                    onChange={(e) => setPathStrategy(e.target.value)}
                  >
                    <option value="highest_volume">Highest-Volume Bottleneck Path (Widest Path)</option>
                    <option value="shortest">Shortest Path (Minimum Hops)</option>
                  </select>
                </div>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleComputePath}
                disabled={loadingPath || !pathSource || !pathTarget}
              >
                <Navigation size={15} />
                {loadingPath ? 'Calculating Route Topology...' : 'Calculate Forensic Route'}
              </button>
            </div>

            {/* Path Results */}
            {pathResult && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="card"
              >
                <div className="card-header">
                  <div>
                    <div className="card-title">
                      <CheckCircle2 size={18} style={{ color: pathResult.found ? 'var(--emerald)' : 'var(--crimson)' }} />
                      {pathResult.found ? 'Forensic Route Discovered' : 'No Directed Route Found'}
                    </div>
                    <div className="card-subtitle">
                      Strategy: {pathResult.strategy} &bull; Total Hops: {pathResult.hop_count ?? '—'}
                    </div>
                  </div>
                </div>

                {pathResult.found ? (
                  <div>
                    {/* Route Stat Badges */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                      <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Bottleneck Capacity</div>
                        <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--network-cyan)' }}>
                          {pathResult.bottleneck_sat != null ? `${pathResult.bottleneck_sat.toLocaleString()} sat` : '—'}
                        </div>
                      </div>

                      <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Total Transferred Volume</div>
                        <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--emerald)' }}>
                          {pathResult.total_volume_sat != null ? `${pathResult.total_volume_sat.toLocaleString()} sat` : '—'}
                        </div>
                      </div>

                      <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Total Intermediary Dwell Delay</div>
                        <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--amber)' }}>
                          {pathResult.total_dwell_time_sec != null ? `${pathResult.total_dwell_time_sec}s` : '—'}
                        </div>
                      </div>
                    </div>

                    {/* Visual Route Hop Sequence */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {pathResult.hops?.map((h, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '1rem',
                            background: 'rgba(15, 23, 42, 0.6)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span className="badge badge-cyan">Hop {h.hop_index}</span>
                            <CopyHash value={h.source_entity} label="Source Entity" truncateLength={6} />
                            <ArrowRight size={16} style={{ color: 'var(--btc-orange)' }} />
                            <CopyHash value={h.target_entity} label="Target Entity" truncateLength={6} />
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                            <span className="mono" style={{ fontWeight: 700, color: '#fff' }}>
                              {h.volume_sat != null ? `${h.volume_sat.toLocaleString()} sat` : '—'}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--btc-gold)' }}>
                              IP: {h.origin_ips?.[0] || 'Relay'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '1.5rem', color: 'var(--text-muted)' }}>
                    {pathResult.reason || 'No directed route exists between the specified entities in the monitored graph.'}
                  </div>
                )}
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
