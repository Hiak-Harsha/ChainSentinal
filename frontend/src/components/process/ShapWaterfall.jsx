import React from 'react';
import { motion } from 'framer-motion';

/**
 * ShapWaterfall — Animated waterfall diagram visualizing TreeSHAP additive feature contributions.
 * Shows base expected value, feature positive/negative forces, and final composite risk score.
 */
export default function ShapWaterfall({
  reasons = [],
  baseValue = 0.35,
  finalScore = 0.85,
}) {
  if (!reasons || reasons.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: '0.2rem' }}>
        <span>Base Expected: {(baseValue * 100).toFixed(0)}%</span>
        <span className="mono" style={{ color: 'var(--btc-orange)', fontWeight: 700 }}>
          Score: {(finalScore * 100).toFixed(0)}%
        </span>
      </div>

      {reasons.slice(0, 6).map((r, idx) => {
        const shap = typeof r.shap_value === 'number' ? r.shap_value : typeof r.value === 'number' ? r.value : typeof r.importance === 'number' ? r.importance : 0;
        const isPositive = shap >= 0;
        const widthPct = Math.min(100, Math.max(12, Math.abs(shap) * 80));
        const featName = (r.feature || r.name || r.rule || `Factor ${idx + 1}`).replace(/_/g, ' ');

        return (
          <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>{featName}</span>
              <span className="mono" style={{ color: isPositive ? 'var(--crimson)' : 'var(--emerald)' }}>
                {isPositive ? `+${shap.toFixed(2)}` : shap.toFixed(2)}
              </span>
            </div>

            <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '3px', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${widthPct}%` }}
                transition={{ duration: 0.35, delay: idx * 0.06 }}
                style={{
                  height: '100%',
                  background: isPositive ? 'var(--crimson)' : 'var(--emerald)',
                  borderRadius: '3px',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
