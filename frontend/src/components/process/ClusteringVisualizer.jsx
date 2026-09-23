import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Network, GitMerge, CheckCircle, Loader } from 'lucide-react';

/**
 * ClusteringVisualizer — Visualizes live Union-Find clustering and CoinJoin exclusion events.
 */
export default function ClusteringVisualizer({
  active = false,
  mergeEvents = [],
  progress = 0,
  stage = 'Idle',
}) {
  if (!active && mergeEvents.length === 0) return null;

  return (
    <div
      className="card"
      style={{
        background: 'rgba(18, 14, 10, 0.95)',
        border: '1px solid var(--btc-orange)',
        boxShadow: '0 0 20px var(--btc-orange-glow)',
        padding: '1rem',
        marginBottom: '1rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: 'var(--btc-orange)', fontSize: '0.85rem' }}>
          {active ? (
            <Loader size={16} className="animate-spin" />
          ) : (
            <CheckCircle size={16} style={{ color: 'var(--emerald)' }} />
          )}
          <span>Entity Resolution Pipeline: {stage}</span>
        </div>
        <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--btc-gold)' }}>
          {(progress * 100).toFixed(0)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.85rem' }}>
        <motion.div
          style={{ height: '100%', background: 'linear-gradient(90deg, var(--btc-orange), var(--btc-gold))' }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(5, progress * 100))}%` }}
          transition={{ duration: 0.2 }}
        />
      </div>

      {/* Recent Merge Stream */}
      <div style={{ maxHeight: '110px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.72rem' }}>
        <AnimatePresence>
          {mergeEvents.slice(0, 5).map((evt, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--text-muted)',
                fontFamily: 'monospace',
              }}
            >
              <GitMerge size={12} style={{ color: 'var(--btc-orange)', flexShrink: 0 }} />
              <span>
                {evt.stage || 'merge'}: {evt.merged ? `${evt.merged} merged` : JSON.stringify(evt.data || evt).slice(0, 60)}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
