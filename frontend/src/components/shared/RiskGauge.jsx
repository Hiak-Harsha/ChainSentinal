import React from 'react';
import { motion } from 'framer-motion';

/**
 * RiskGauge — Visual representation of risk score (0.0 to 1.0)
 * 
 * Supports two variants:
 * - 'radial': Semi-circular SVG gauge with pointer / stroke arc
 * - 'bar': Compact horizontal progress bar with numeric badge
 */
export default function RiskGauge({
  score = 0,
  variant = 'bar',
  size = 'md',
  showLabel = true,
  className = '',
}) {
  const rawVal = Number(score);
  const numericScore = Math.max(0, Math.min(1, Number.isFinite(rawVal) ? rawVal : 0));
  const percent = Math.round(numericScore * 100);

  // Determine color based on threshold
  let color = 'var(--risk-low, #10b981)';
  let bgTint = 'rgba(16, 185, 129, 0.12)';
  let tier = 'LOW';

  if (numericScore >= 0.75) {
    color = 'var(--risk-critical, #f43f5e)';
    bgTint = 'rgba(244, 63, 94, 0.15)';
    tier = 'CRITICAL';
  } else if (numericScore >= 0.50) {
    color = 'var(--risk-high, #f97316)';
    bgTint = 'rgba(249, 115, 22, 0.12)';
    tier = 'HIGH';
  } else if (numericScore >= 0.30) {
    color = 'var(--risk-medium, #fbbf24)';
    bgTint = 'rgba(251, 191, 36, 0.12)';
    tier = 'MEDIUM';
  }

  if (variant === 'radial') {
    const radius = size === 'lg' ? 42 : size === 'sm' ? 24 : 32;
    const strokeWidth = size === 'lg' ? 7 : size === 'sm' ? 4 : 5;
    const circumference = Math.PI * radius; // Half-circle
    const strokeDashoffset = circumference - (circumference * numericScore);
    const svgSize = radius * 2 + strokeWidth * 2;

    return (
      <div className={`risk-gauge-radial inline-flex flex-col items-center ${className}`}>
        <svg
          width={svgSize}
          height={radius + strokeWidth + 6}
          viewBox={`0 0 ${svgSize} ${radius + strokeWidth + 6}`}
        >
          {/* Background Arc */}
          <path
            d={`M ${strokeWidth},${radius + strokeWidth} A ${radius} ${radius} 0 0 1 ${svgSize - strokeWidth},${radius + strokeWidth}`}
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Active Arc */}
          <motion.path
            d={`M ${strokeWidth},${radius + strokeWidth} A ${radius} ${radius} 0 0 1 ${svgSize - strokeWidth},${radius + strokeWidth}`}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 4px ${color})` }}
          />
        </svg>
        <div style={{ marginTop: '-12px', textAlign: 'center' }}>
          <span style={{ fontSize: size === 'lg' ? '1.2rem' : '0.9rem', fontWeight: 700, color }}>
            {numericScore.toFixed(2)}
          </span>
          {showLabel && (
            <div style={{ fontSize: '0.62rem', color: 'var(--text-dim, #64748b)', letterSpacing: '0.05em' }}>
              {tier}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Horizontal bar variant (default)
  return (
    <div className={`risk-gauge-bar flex items-center gap-2 ${className}`} style={{ width: '100%' }}>
      <div
        style={{
          flex: 1,
          height: size === 'sm' ? '5px' : '7px',
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '999px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <motion.div
          style={{
            height: '100%',
            backgroundColor: color,
            borderRadius: '999px',
            boxShadow: `0 0 8px ${color}`,
          }}
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span
        style={{
          fontFamily: 'monospace',
          fontSize: size === 'sm' ? '0.72rem' : '0.8rem',
          fontWeight: 600,
          color,
          minWidth: '38px',
          textAlign: 'right',
        }}
      >
        {numericScore.toFixed(2)}
      </span>
      {showLabel && (
        <span
          style={{
            fontSize: '0.65rem',
            padding: '1px 5px',
            borderRadius: '4px',
            backgroundColor: bgTint,
            color,
            border: `1px solid ${color}33`,
            fontWeight: 600,
          }}
        >
          {tier}
        </span>
      )}
    </div>
  );
}
