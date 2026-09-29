import React from 'react';
import { Filter, X } from 'lucide-react';

/**
 * FilterBar - Pill-style or dropdown filter group with active counts and quick clear.
 */
export default function FilterBar({
  options = [],
  activeValue,
  onChange,
  label,
  icon: Icon = Filter,
  showClear = false,
  onClear,
  className = '',
}) {
  return (
    <div
      className={`filter-bar ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.2rem 0.35rem',
        background: 'rgba(255, 255, 255, 0.02)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
        fontSize: '0.78rem',
      }}
    >
      {label && (
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--text-dim)', padding: '0 0.3rem' }}>
          {Icon && <Icon size={13} />}
          <span>{label}</span>
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        {options.map((opt) => {
          const val = typeof opt === 'object' ? opt.value : opt;
          const lbl = typeof opt === 'object' ? opt.label : opt;
          const count = typeof opt === 'object' ? opt.count : undefined;
          const isActive = activeValue === val;

          return (
            <button
              key={val}
              type="button"
              onClick={() => onChange(val)}
              style={{
                background: isActive ? 'var(--color-primary)' : 'transparent',
                color: isActive ? '#000' : 'var(--text-muted)',
                fontWeight: isActive ? 700 : 500,
                border: 'none',
                borderRadius: 'var(--radius-xs)',
                padding: '0.2rem 0.55rem',
                fontSize: '0.74rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                transition: 'all 0.15s ease',
              }}
            >
              <span>{lbl}</span>
              {count !== undefined && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    padding: '0 4px',
                    borderRadius: '8px',
                    background: isActive ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.08)',
                  }}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {showClear && onClear && (
        <button
          type="button"
          onClick={onClear}
          title="Clear Filter"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            cursor: 'pointer',
            padding: '2px 4px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}
