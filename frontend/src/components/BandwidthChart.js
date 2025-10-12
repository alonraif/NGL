import React, { useRef } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import CopyChartButton from './CopyChartButton';

function BandwidthChart({ data, mode }) {
  const chartRef = useRef(null);
  const borderColor = 'var(--border-color)';
  const textSecondary = 'var(--text-secondary)';
  const textPrimary = 'var(--text-primary)';
  const cardBackground = 'var(--bg-card)';

  // Check if data is valid array
  if (!data || !Array.isArray(data) || data.length === 0) {
    return <div style={{ margin: '20px 0', textAlign: 'center', color: textSecondary }}>No bandwidth data available</div>;
  }

  // Check if first element exists
  if (!data[0]) {
    return <div style={{ margin: '20px 0', textAlign: 'center', color: textSecondary }}>No bandwidth data available</div>;
  }

  // Get all numeric columns (excluding timestamp/date columns)
  const headers = Object.keys(data[0]);
  const numericColumns = headers.filter(key => {
    const value = data[0][key];
    return !isNaN(parseFloat(value)) && isFinite(value);
  });

  const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2'];

  // Parse numeric columns once so the chart domain uses numeric comparisons
  const chartData = data.map(row => {
    const converted = { ...row };
    numericColumns.forEach(col => {
      const parsed = parseFloat(row[col]);
      converted[col] = Number.isFinite(parsed) ? parsed : 0;
    });
    return converted;
  });

  // Calculate summary statistics
  const stats = numericColumns.map((col, idx) => {
    const values = chartData.map(row => row[col] || 0);
    const sum = values.reduce((a, b) => a + b, 0);
    const avg = sum / values.length;
    const max = Math.max(...values);
    const min = Math.min(...values);

    return {
      column: col,
      avg: avg.toFixed(2),
      max: max.toFixed(2),
      min: min.toFixed(2),
      color: colors[idx % colors.length],
    };
  });

  const title =
    mode === 'bw'
      ? 'Stream Bandwidth Over Time'
      : mode === 'md-bw'
        ? 'Modem Bandwidth Over Time'
        : 'Data Bridge Bandwidth Over Time';
  const fileName =
    mode === 'bw'
      ? 'stream-bandwidth.png'
      : mode === 'md-bw'
        ? 'modem-bandwidth.png'
        : 'databridge-bandwidth.png';

  return (
    <div>
      <div className="stats-grid">
        {stats.map(stat => (
          <div key={stat.column} className="stat-card">
            <h3>{stat.column}</h3>
            <div className="value">
              {stat.avg}
              <span className="unit">avg</span>
            </div>
            <p style={{ marginTop: '10px', fontSize: '0.9rem' }}>
              Min: {stat.min} | Max: {stat.max}
            </p>
          </div>
        ))}
      </div>

      <div className="chart-header">
        <h3>{title}</h3>
        <CopyChartButton targetRef={chartRef} fileName={fileName} />
      </div>
      <div ref={chartRef} className="chart-container" style={{ height: '500px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
            <XAxis
              dataKey={headers[0]}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={Math.floor(data.length / 10) || 1}
              tick={{ fontSize: 11, fill: textSecondary }}
            />
            <YAxis
              label={{ value: 'Bandwidth (Kbps)', angle: -90, position: 'insideLeft', fill: textSecondary }}
              domain={[0, 'dataMax']}
              tick={{ fill: textSecondary }}
            />
            <Tooltip
              contentStyle={{
                background: cardBackground,
                border: `1px solid ${borderColor}`,
                borderRadius: '8px',
                color: textPrimary
              }}
            />
            <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px' }} />
            {numericColumns.map((col, idx) => (
              <Area
                key={col}
                type="monotone"
                dataKey={col}
                stroke={colors[idx % colors.length]}
                fill={colors[idx % colors.length]}
                fillOpacity={0.3}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px', color: textPrimary }}>Data Table</h3>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              {headers.map(header => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr key={idx}>
                {headers.map(header => (
                  <td key={header}>{row[header]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default BandwidthChart;
