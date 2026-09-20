import React from 'react';

/**
 * StatusBadge - Uniform badge for NTRO triage statuses and alert severities.
 * 
 * Supports:
 * - Triage statuses: NEW, INVESTIGATING, ESCALATED, CLOSED_FALSE_POSITIVE, RESOLVED
 * - Severities: CRITICAL, HIGH, MEDIUM, LOW, INFO
 */
const STATUS_CONFIGS = {
  // NTRO Triage Statuses
  NEW: { label: 'NEW', bg: 'rgba(56, 189, 248, 0.12)', border: 'rgba(56, 189, 248, 0.3)', text: '#38bdf8', dot: '#38bdf8' },
  INVESTIGATING: { label: 'INVESTIGATING', bg: 'rgba(251, 191, 36, 0.12)', border: 'rgba(251, 191, 36, 0.3)', text: '#fbbf24', dot: '#fbbf24' },
  ESCALATED: { label: 'ESCALATED', bg: 'rgba(244, 63, 94, 0.15)', border: 'rgba(244, 63, 94, 0.4)', text: '#f43f5e', dot: '#f43f5e' },
  CLOSED_FALSE_POSITIVE: { label: 'FALSE POSITIVE', bg: 'rgba(148, 163, 184, 0.1)', border: 'rgba(148, 163, 184, 0.25)', text: '#94a3b8', dot: '#64748b' },
  RESOLVED: { label: 'RESOLVED', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.3)', text: '#10b981', dot: '#10b981' },
  
  // Severities
  CRITICAL: { label: 'CRITICAL', bg: 'rgba(244, 63, 94, 0.18)', border: 'rgba(244, 63, 94, 0.45)', text: '#f43f5e', dot: '#f43f5e' },
  HIGH: { label: 'HIGH', bg: 'rgba(249, 115, 22, 0.15)', border: 'rgba(249, 115, 22, 0.35)', text: '#f97316', dot: '#f97316' },
  MEDIUM: { label: 'MEDIUM', bg: 'rgba(251, 191, 36, 0.12)', border: 'rgba(251, 191, 36, 0.3)', text: '#fbbf24', dot: '#fbbf24' },
  LOW: { label: 'LOW', bg: 'rgba(56, 189, 248, 0.1)', border: 'rgba(56, 189, 248, 0.25)', text: '#38bdf8', dot: '#38bdf8' },
  INFO: { label: 'INFO', bg: 'rgba(148, 163, 184, 0.1)', border: 'rgba(148, 163, 184, 0.25)', text: '#94a3b8', dot: '#94a3b8' },
};

export default function StatusBadge({ status, size = 'sm', showDot = true, className = '' }) {
  const normalized = (status || 'INFO').toUpperCase().replace(/[-\s]/g, '_');
  const cfg = STATUS_CONFIGS[normalized] || {
    label: status || 'UNKNOWN',
    bg: 'rgba(148, 163, 184, 0.1)',
    border: 'rgba(148, 163, 184, 0.25)',
    text: '#94a3b8',
    dot: '#94a3b8',
  };

  const isLg = size === 'md';

  return (
    <span
      className={`status-badge inline-flex items-center gap-1.5 font-mono font-medium rounded-full ${className}`}
      style={{
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.border}`,
        color: cfg.text,
        fontSize: isLg ? '0.78rem' : '0.7rem',
        padding: isLg ? '3px 10px' : '2px 8px',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
      }}
    >
      {showDot && (
        <span
          style={{
            width: isLg ? '6px' : '5px',
            height: isLg ? '6px' : '5px',
            borderRadius: '50%',
            backgroundColor: cfg.dot,
            boxShadow: `0 0 6px ${cfg.dot}`,
            display: 'inline-block',
          }}
        />
      )}
      {cfg.label}
    </span>
  );
}
