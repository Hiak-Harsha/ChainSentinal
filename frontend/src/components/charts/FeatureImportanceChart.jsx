import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';

/**
 * FeatureImportanceChart — Horizontal BarChart displaying top TreeSHAP feature attributions.
 */
export default function FeatureImportanceChart({
  features = [],
  height = 320,
}) {
  if (!features || features.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
        No feature importance data available. Trigger training to compute TreeSHAP attributions.
      </div>
    );
  }

  // Format data: feature names cleaned up, importance as percentage
  const chartData = features.slice(0, 10).map((f) => ({
    name: (f.feature || '').replace(/_/g, ' '),
    importance: +(f.importance * 100).toFixed(1),
    rawImportance: f.importance,
  }));

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 10, right: 30, left: 90, bottom: 10 }}
        >
          <XAxis
            type="number"
            domain={[0, 'auto']}
            unit="%"
            tick={{ fill: 'var(--text-dim)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={{ stroke: 'var(--border-subtle)' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
            width={85}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(18, 14, 10, 0.95)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '12px',
            }}
            formatter={(value) => [`${value}%`, 'Importance Weight']}
          />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={index === 0 ? 'var(--btc-orange)' : index < 3 ? 'var(--btc-gold)' : '#a89d8c'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
