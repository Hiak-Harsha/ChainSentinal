import React from 'react';

/**
 * PageHeader - Uniform header for first-class workspaces.
 * Displays title, icon, descriptive subtitle, and action buttons.
 */
export default function PageHeader({
  icon: Icon,
  iconColor = 'var(--btc-orange)',
  title,
  subtitle,
  badges,
  actions,
  className = '',
}) {
  return (
    <div
      className={`card page-header ${className}`}
      style={{
        marginBottom: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {Icon && (
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: iconColor,
              flexShrink: 0,
            }}
          >
            <Icon size={20} />
          </div>
        )}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h1
              style={{
                fontSize: '1.3rem',
                fontWeight: 800,
                color: 'var(--text-emphasis)',
                margin: 0,
                letterSpacing: '-0.01em',
              }}
            >
              {title}
            </h1>
            {badges}
          </div>
          {subtitle && (
            <div
              style={{
                color: 'var(--text-muted)',
                fontSize: '0.82rem',
                marginTop: '0.2rem',
                lineHeight: 1.4,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      </div>

      {actions && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {actions}
        </div>
      )}
    </div>
  );
}
