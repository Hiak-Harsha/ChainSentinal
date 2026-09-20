import React from 'react';
import { ChainSentinelLogo } from './icons';

/**
 * RadarEmptyState
 * Forensic radar sweep animation for empty alert queues, filter zeroes, or idle monitors.
 */
export const RadarEmptyState = ({
  title = 'MEMPOOL & LEDGER RADAR ACTIVE',
  subtitle = 'No anomalous Bitcoin transactions detected matching current filter criteria.',
  action = null,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1.5rem',
        textAlign: 'center',
      }}
    >
      {/* Radar Graphic */}
      <div className="radar-display-box" style={{ marginBottom: '1.5rem' }}>
        <div className="radar-ring radar-ring-1" />
        <div className="radar-ring radar-ring-2" />
        <div className="radar-ring radar-ring-3" />
        <div className="radar-crosshair-h" />
        <div className="radar-crosshair-v" />
        <div className="radar-sweep-beam" />

        {/* Center Forensic Beacon */}
        <div style={{ zIndex: 2, position: 'relative' }}>
          <ChainSentinelLogo size={36} glow={false} />
        </div>
      </div>

      {/* Status Labels */}
      <div
        style={{
          fontSize: '0.95rem',
          fontWeight: 800,
          color: 'var(--text-main)',
          letterSpacing: '0.04em',
          marginBottom: '0.4rem',
        }}
      >
        {title}
      </div>

      <div
        style={{
          fontSize: '0.82rem',
          color: 'var(--text-dim)',
          maxWidth: '420px',
          lineHeight: '1.5',
          marginBottom: action ? '1.25rem' : '0',
        }}
      >
        {subtitle}
      </div>

      {action && <div>{action}</div>}
    </div>
  );
};
