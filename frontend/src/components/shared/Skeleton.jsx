import React from 'react';

/**
 * Shimmer skeleton loading placeholder.
 * Usage: <Skeleton width="100px" height="2rem" />
 */
export default function Skeleton({ width = '100%', height = '1em', style = {}, className = '' }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  );
}

/** Pre-composed skeleton variants */
export function SkeletonText({ lines = 3, className = '' }) {
  return (
    <div className={className}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="skeleton skeleton-text"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
}

export function SkeletonKPI({ className = '' }) {
  return (
    <div className={`card kpi-card ${className}`} style={{ minHeight: '120px' }}>
      <div className="skeleton skeleton-text" style={{ width: '50%', marginBottom: '0.75rem' }} />
      <div className="skeleton skeleton-kpi" />
      <div className="skeleton skeleton-text-sm" style={{ marginTop: '0.5rem' }} />
    </div>
  );
}
