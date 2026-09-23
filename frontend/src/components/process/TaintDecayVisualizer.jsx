import React from 'react';
import { motion } from 'framer-motion';
import { TrendingDown, ShieldAlert, ArrowRight } from 'lucide-react';

/**
 * TaintDecayVisualizer — Animates progressive saturation loss and volume dilution
 * across multi-hop taint propagation corridors.
 */
export default function TaintDecayVisualizer({
  hops = [],
  decayModel = 'proportional',
}) {
  if (!hops || hops.length === 0) return null;

  return (
    <div
      className="card"
      style={{
        background: 'rgba(18, 14, 10, 0.95)',
        border: '1px solid var(--border-subtle)',
        padding: '1.25rem',
        marginBottom: '1.5rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.85rem' }}>
          <TrendingDown size={16} style={{ color: 'var(--btc-orange)' }} />
          <span>Taint Attenuation Corridor ({decayModel.toUpperCase()} LAW)</span>
        </div>
        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
          {hops.length} Hops Simulated
        </span>
      </div>

      {/* Visual Conduit Bar Stack */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem', height: '120px', padding: '0 0.5rem' }}>
        {hops.map((hop, idx) => {
          const taintPct = hop.taint_pct ?? 100;
          const barHeight = Math.max(16, (taintPct / 100) * 90);
          const isStop = !!hop.stop_reason;

          return (
            <div
              key={idx}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                height: '100%',
                justifyContent: 'flex-end',
                position: 'relative',
              }}
            >
              {/* Value Tooltip Label */}
              <span className="mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                {taintPct}%
              </span>

              {/* Decay Bar */}
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${barHeight}px` }}
                transition={{ duration: 0.4, delay: idx * 0.08 }}
                style={{
                  width: '100%',
                  maxWidth: '36px',
                  borderRadius: '4px 4px 0 0',
                  background: isStop
                    ? 'var(--emerald)'
                    : taintPct > 60
                    ? 'var(--crimson)'
                    : 'var(--btc-orange)',
                  boxShadow: `0 0 8px ${
                    isStop ? 'var(--emerald)' : taintPct > 60 ? 'var(--crimson)' : 'var(--btc-orange-glow)'
                  }`,
                }}
              />

              {/* Hop Index Label */}
              <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '6px' }}>
                H{hop.hop_index ?? idx + 1}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
