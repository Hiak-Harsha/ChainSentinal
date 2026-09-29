import React from 'react';
import Skeleton from './Skeleton';

/**
 * LoadingState - Clean loading state with spinner, status message, and optional skeletons.
 */
export default function LoadingState({
  message = 'Loading forensic data...',
  detail = 'Synchronizing with backend ledger...',
  skeletons = 3,
  className = '',
}) {
  return (
    <div
      className={`loading-state ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1.5rem',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          border: '2px solid rgba(247, 147, 26, 0.2)',
          borderTopColor: 'var(--color-primary)',
          animation: 'spin 0.9s linear infinite',
          marginBottom: '1rem',
        }}
      />
      <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-emphasis)', marginBottom: '0.25rem' }}>
        {message}
      </div>
      {detail && (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          {detail}
        </div>
      )}
      {skeletons > 0 && (
        <div style={{ width: '100%', maxWidth: '380px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {Array.from({ length: skeletons }).map((_, i) => (
            <Skeleton key={i} width="100%" height="16px" style={{ borderRadius: '3px' }} />
          ))}
        </div>
      )}
    </div>
  );
}
