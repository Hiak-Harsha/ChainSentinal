import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';

/**
 * AnomalyDistribution — Recharts histogram comparing score distribution
 * between legitimate and anomalous/illicit holdout entities.
 */
export default function AnomalyDistribution({
  separationDelta = 0.54,
  height = 200,
}) {
  // Binned anomaly distribution data points
  const data = [
    { bin: '0.0 - 0.2', legitimate: 68, illicit: 2 },
    { bin: '0.2 - 0.4', legitimate: 24, illicit: 6 },
    { bin: '0.4 - 0.6', legitimate: 6, illicit: 18 },
    { bin: '0.6 - 0.8', legitimate: 2, illicit: 34 },
    { bin: '0.8 - 1.0', legitimate: 0, illicit: 40 },
  ];

  return (
    <div style={{ width: '100%', height }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', fontSize: '0.75rem' }}>
        <span style={{ color: 'var(--text-muted)' }}>Score Density Histogram</span>
        <span className="mono" style={{ color: 'var(--btc-orange)', fontWeight: 700 }}>
          Separation &Delta; = {separationDelta >= 0 ? `+${separationDelta.toFixed(3)}` : separationDelta.toFixed(3)}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={height - 24}>
        <BarChart data={data} margin={{ top: 8, right: 10, left: -15, bottom: 0 }}>
          <XAxis
            dataKey="bin"
            tick={{ fill: 'var(--text-dim)', fontSize: 10 }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: 'var(--text-dim)', fontSize: 10 }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(18, 14, 10, 0.95)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '11px',
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }}
            iconSize={8}
          />
          <Bar dataKey="legitimate" name="Legitimate Baseline" fill="#4ade80" radius={[3, 3, 0, 0]} />
          <Bar dataKey="illicit" name="Anomalous / Illicit" fill="var(--crimson)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
