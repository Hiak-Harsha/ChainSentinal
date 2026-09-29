import React from 'react';

/**
 * ActionGroup - Grouped action buttons with consistent spacing, sizing, and styling.
 */
export default function ActionGroup({ children, className = '', style = {} }) {
  return (
    <div
      className={`action-group ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4rem',
        flexWrap: 'wrap',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
