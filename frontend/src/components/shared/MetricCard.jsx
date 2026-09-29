import React from 'react';
import AnimatedNumber from './AnimatedNumber';
import Skeleton from './Skeleton';

/**
 * MetricCard - Consistent forensic telemetry KPI card.
 * Colors: cyan, crimson, emerald, btc, amber, purple
 */
export default function MetricCard({
  label,
  value,
  numericValue,
  decimals = 0,
  suffix = '',
  prefix = '',
  unit = '',
  meta,
  icon: Icon,
  variant = 'cyan', // 'cyan' | 'crimson' | 'emerald' | 'btc' | 'amber' | 'purple'
  badge,
  loading = false,
  className = '',
  onClick,
}) {
  return (
    <div
      className={`card kpi-card ${variant} ${className} ${onClick ? 'cursor-pointer hover:border-accent' : ''}`}
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        cursor: onClick ? 'pointer' : 'default',
        minHeight: '110px',
      }}
    >
      <div className="kpi-top" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>
          {label}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {badge}
          {Icon && (
            <div className={`kpi-icon-wrap ${variant}`}>
              <Icon size={18} />
            </div>
          )}
        </div>
      </div>

      <div className="kpi-value mono" style={{ margin: '0.4rem 0', display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
        {loading ? (
          <Skeleton width="100px" height="1.8rem" />
        ) : typeof numericValue === 'number' ? (
          <>
            {prefix}
            <AnimatedNumber value={numericValue} decimals={decimals} suffix={suffix} />
            {unit && <span style={{ fontSize: '0.9rem', color: 'var(--text-dim)', marginLeft: '2px' }}>{unit}</span>}
          </>
        ) : (
          <span>{value ?? '—'}</span>
        )}
      </div>

      {meta && (
        <div className="kpi-meta" style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>
          {meta}
        </div>
      )}
    </div>
  );
}
