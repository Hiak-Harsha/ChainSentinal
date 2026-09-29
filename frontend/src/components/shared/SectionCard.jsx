import React from 'react';

/**
 * SectionCard - Structured container with clear header, title, badge, actions, and body.
 */
export default function SectionCard({
  icon: Icon,
  iconColor = 'var(--text-main)',
  title,
  subtitle,
  badge,
  actions,
  children,
  className = '',
  style = {},
  noPadding = false,
}) {
  return (
    <div className={`card section-card ${className}`} style={{ ...style }}>
      {(title || Icon || actions) && (
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {Icon && <Icon size={18} style={{ color: iconColor }} />}
            <div>
              <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>{title}</span>
                {badge}
              </div>
              {subtitle && <div className="card-subtitle">{subtitle}</div>}
            </div>
          </div>
          {actions && <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>{actions}</div>}
        </div>
      )}
      <div style={noPadding ? { margin: '-1rem', marginTop: 0 } : undefined}>
        {children}
      </div>
    </div>
  );
}
