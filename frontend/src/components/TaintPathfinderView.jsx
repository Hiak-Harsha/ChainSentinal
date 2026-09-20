import React, { useState } from 'react';
import {
  GitBranch,
  ArrowRight,
  TrendingDown,
  Clock,
  Radio,
  Building2,
  Shuffle,
  ShieldAlert,
  Play,
  CheckCircle2,
  Navigation,
} from 'lucide-react';
import { api } from '../api';

export default function TaintPathfinderView({ prefilledTarget = '' }) {
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

  const handleRunTrace = async () => {
    if (!target) return;
    setLoadingTrace(true);
    setTraceResult(null);
    try {
      const res = await api.runTrace({
        target: target.trim(),
        direction,
        decay_model: decayModel,
        max_hops: parseInt(maxHops),
        amount: amount ? parseInt(amount) : null,
      });
      setTraceResult(res);
    } catch (err) {
      alert(`Trace failed: ${err.message}`);
    } finally {
      setLoadingTrace(false);
    }
  };

  const handleComputePath = async () => {
    if (!pathSource || !pathTarget) return;
    setLoadingPath(true);
    setPathResult(null);
    try {
      const res = await api.computePath({
        source: pathSource.trim(),
        target: pathTarget.trim(),
        strategy: pathStrategy,
      });
      setPathResult(res);
    } catch (err) {
      alert(`Path computation failed: ${err.message}`);
    } finally {
      setLoadingPath(false);
    }
  };

  return (
    <div>
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

      {subTab === 'taint' ? (
        /* TAINT TRACKER VIEW */
        <div>
          {/* Configuration Form Card */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <div>
                <div className="card-title">
                  <GitBranch size={18} style={{ color: 'var(--cyan-primary)' }} />
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
            <div>
              {/* Summary KPIs */}
              <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
                <div className="card kpi-card cyan">
                  <div className="kpi-top">
                    <span>Traversed Hops</span>
                  </div>
                  <div className="kpi-value mono" style={{ color: 'var(--cyan-primary)' }}>
                    {traceResult.hops?.length || 0}
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
                    {traceResult.summary?.cashout_exchanges?.length || 0}
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
                    {traceResult.endpoints?.length || 0}
                  </div>
                  <div className="kpi-meta">
                    Dormant / Exchange Deposited
                  </div>
                </div>

                <div className="card kpi-card purple">
                  <div className="kpi-top">
                    <span>Decay Algorithm</span>
                  </div>
                  <div className="kpi-value mono" style={{ color: 'var(--purple-primary)', textTransform: 'uppercase', fontSize: '1.4rem' }}>
                    {traceResult.summary?.decay_model}
                  </div>
                  <div className="kpi-meta">
                    Trace ID: {traceResult.trace_id}
                  </div>
                </div>
              </div>

              {/* Step-by-Step Flow List */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    <TrendingDown size={18} style={{ color: 'var(--cyan-primary)' }} />
                    Multi-Hop Taint Flow Ledger ({traceResult.hops?.length || 0} Steps)
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
                        <th>Terminal Reason</th>
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
                              <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span className="mono" style={{ fontWeight: 600 }}>{h.from_entity}</span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{h.from_entity_type}</span>
                              </div>
                            </td>
                            <td>
                              <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span className="mono" style={{ fontWeight: 600, color: 'var(--cyan-primary)' }}>{h.to_entity}</span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{h.to_entity_type}</span>
                              </div>
                            </td>
                            <td>
                              <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span className="mono" style={{ fontWeight: 700 }}>
                                  {(h.transferred_sat || 0).toLocaleString()} sat
                                </span>
                                <span style={{ fontSize: '0.75rem', color: h.taint_pct > 50 ? 'var(--crimson)' : 'var(--amber)' }}>
                                  {h.taint_pct}% Tainted ({(h.tainted_sat || 0).toLocaleString()} sat)
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                {h.dwell_time_sec}s
                              </span>
                            </td>
                            <td>
                              <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--purple-primary)' }}>
                                {h.origin_ip || 'UNKNOWN'}
                              </span>
                            </td>
                            <td>
                              {h.stop_reason ? (
                                <span className="badge badge-amber">{h.stop_reason}</span>
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
            </div>
          )}
        </div>
      ) : (
        /* PATHFINDER VIEW */
        <div>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <div>
                <div className="card-title">
                  <Navigation size={18} style={{ color: 'var(--cyan-primary)' }} />
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
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">
                    <CheckCircle2 size={18} style={{ color: pathResult.found ? 'var(--emerald)' : 'var(--crimson)' }} />
                    {pathResult.found ? 'Forensic Route Discovered' : 'No Directed Route Found'}
                  </div>
                  <div className="card-subtitle">
                    Strategy: {pathResult.strategy} &bull; Total Hops: {pathResult.hop_count || 0}
                  </div>
                </div>
              </div>

              {pathResult.found ? (
                <div>
                  {/* Route Stat Badges */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                    <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Bottleneck Capacity</div>
                      <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--cyan-primary)' }}>
                        {(pathResult.bottleneck_sat || 0).toLocaleString()} sat
                      </div>
                    </div>

                    <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Total Transferred Volume</div>
                      <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--emerald)' }}>
                        {(pathResult.total_volume_sat || 0).toLocaleString()} sat
                      </div>
                    </div>

                    <div style={{ padding: '0.75rem 1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Total Intermediary Dwell Delay</div>
                      <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--amber)' }}>
                        {pathResult.total_dwell_time_sec || 0}s
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
                          <span className="mono" style={{ fontWeight: 700 }}>{h.source_entity}</span>
                          <ArrowRight size={16} style={{ color: 'var(--cyan-primary)' }} />
                          <span className="mono" style={{ fontWeight: 700, color: 'var(--cyan-primary)' }}>{h.target_entity}</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                          <span className="mono" style={{ fontWeight: 700, color: '#fff' }}>
                            {(h.volume_sat || 0).toLocaleString()} sat
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--purple-primary)' }}>
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
            </div>
          )}
        </div>
      )}
    </div>
  );
}
