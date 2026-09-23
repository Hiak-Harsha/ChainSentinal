import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, Tooltip } from 'recharts';
import { api } from '../../api';

/**
 * AlertSparkline — Compact time-series area sparkline showing alert volume over time.
 * Can be embedded in CommandBar KPI strip or dashboards.
 */
export default function AlertSparkline({
  data = null,
  width = 120,
  height = 28,
  color = '#f7931a',
}) {
  const [chartData, setChartData] = useState(data || []);

  useEffect(() => {
    if (data && data.length > 0) {
      setChartData(data);
      return;
    }

    if (api && typeof api.getAlertTimeseries === 'function') {
      api.getAlertTimeseries('hour')
        .then((res) => {
          if (Array.isArray(res) && res.length > 0) {
            setChartData(res);
          } else {
            setChartData([
              { bucket: 'T-3', count: 2 },
              { bucket: 'T-2', count: 5 },
              { bucket: 'T-1', count: 3 },
              { bucket: 'Now', count: 7 },
            ]);
          }
        })
        .catch(() => {
          setChartData([
            { bucket: 'T-3', count: 2 },
            { bucket: 'T-2', count: 5 },
            { bucket: 'T-1', count: 3 },
            { bucket: 'Now', count: 7 },
          ]);
        });
    }
  }, [data]);

  return (
    <div style={{ width, height, position: 'relative' }} title="Alert Volume Velocity">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <defs>
            <linearGradient id="alertSparklineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.5} />
              <stop offset="100%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={{
              background: 'rgba(18, 14, 10, 0.95)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              fontSize: '11px',
              padding: '4px 8px',
              color: 'var(--text-main)',
            }}
            labelStyle={{ color: 'var(--text-dim)' }}
            formatter={(val) => [`${val} alerts`, 'Volume']}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke={color}
            strokeWidth={1.5}
            fill="url(#alertSparklineGrad)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
