import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

/**
 * InspectorSection - Collapsible section container for the InspectorPanel.
 */
export default function InspectorSection({
  title,
  icon: Icon,
  count,
  badge,
  defaultOpen = true,
  children,
  className = '',
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={`inspector-section ${className}`}
      style={{
        padding: '0.6rem 0',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
      }}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'none',
          border: 'none',
          padding: '0.2rem 0',
          cursor: 'pointer',
          color: 'inherit',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {Icon && <Icon size={13} style={{ color: 'var(--text-dim)' }} />}
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-dim)',
            }}
          >
            {title}
          </span>
          {count !== undefined && (
            <span
              className="mono"
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                background: 'rgba(255, 255, 255, 0.06)',
                padding: '1px 5px',
                borderRadius: '8px',
              }}
            >
              {count}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {badge}
          {isOpen ? (
            <ChevronDown size={14} style={{ color: 'var(--text-dim)' }} />
          ) : (
            <ChevronRight size={14} style={{ color: 'var(--text-dim)' }} />
          )}
        </div>
      </button>

      {isOpen && (
        <div style={{ marginTop: '0.5rem' }}>
          {children}
        </div>
      )}
    </div>
  );
}
