import React from 'react';
import { AlertOctagon, RotateCw } from 'lucide-react';

/**
 * ErrorState - Recovers forensic failures with clear diagnostics and a retry trigger.
 */
export default function ErrorState({
  title = 'Forensic Query Failed',
  message = 'Unable to complete the requested operation.',
  onRetry,
  className = '',
}) {
  return (
    <div
      className={`card error-state ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2.5rem 1.5rem',
        textAlign: 'center',
        background: 'rgba(244, 63, 94, 0.05)',
        border: '1px solid rgba(244, 63, 94, 0.3)',
      }}
    >
      <div
        style={{
          width: '42px',
          height: '42px',
          borderRadius: '50%',
          background: 'rgba(244, 63, 94, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--crimson)',
          marginBottom: '0.85rem',
        }}
      >
        <AlertOctagon size={22} />
      </div>
      <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--crimson)', marginBottom: '0.35rem' }}>
        {title}
      </div>
      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', maxWidth: '440px', lineHeight: 1.4, marginBottom: onRetry ? '1.25rem' : 0 }}>
        {message}
      </div>
      {onRetry && (
        <button className="btn btn-secondary btn-sm" onClick={onRetry}>
          <RotateCw size={14} /> Retry Operation
        </button>
      )}
    </div>
  );
}
