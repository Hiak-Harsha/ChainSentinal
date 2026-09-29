import React from 'react';
import { Shield } from 'lucide-react';

/**
 * EmptyState - High-clarity empty state prompt with icon, heading, details, and optional action.
 */
export default function EmptyState({
  icon: Icon = Shield,
  title = 'No Data Available',
  description = 'No matching forensic records found for this workspace.',
  action,
  className = '',
  style = {},
}) {
  return (
    <div
      className={`empty-state ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1.5rem',
        textAlign: 'center',
        background: 'rgba(255, 255, 255, 0.01)',
        borderRadius: 'var(--radius-md)',
        border: '1px dashed var(--border-subtle)',
        ...style,
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.03)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-dim)',
          marginBottom: '1rem',
        }}
      >
        <Icon size={24} />
      </div>
      <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-emphasis)', marginBottom: '0.35rem' }}>
        {title}
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: 1.4, marginBottom: action ? '1rem' : 0 }}>
        {description}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
