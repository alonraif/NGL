import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

function BandwidthChart({ data, mode }) {
  // Check if data is valid array
  if (!data || !Array.isArray(data) || data.length === 0) {
    return <div>No bandwidth data available</div>;
  }

  // Check if first element exists
  if (!data[0]) {
    return <div>No bandwidth data available</div>;
  }

  // Get all numeric columns (excluding timestamp/date columns)
  const headers = Object.keys(data[0]);
  const numericColumns = headers.filter(key => {
    const value = data[0][key];
    return !isNaN(parseFloat(value)) && isFinite(value);
  });

  const colors = ['#667eea', '#764ba2', '#82ca9d', '#ff6b6b', '#ffd93d', '#6bcf7f'];

  // Calculate summary statistics
  const stats = numericColumns.map((col, idx) => {
    const values = data.map(row => parseFloat(row[col]) || 0);
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

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>
        {mode === 'bw' ? 'Stream Bandwidth Over Time' :
         mode === 'md-bw' ? 'Modem Bandwidth Over Time' :
         'Data Bridge Bandwidth Over Time'}
      </h3>
      <div className="chart-container" style={{ height: '500px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={headers[0]}
              angle={-45}
              textAnchor="end"
              height={100}
              interval="preserveStartEnd"
            />
            <YAxis />
            <Tooltip />
            <Legend />
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

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Line Chart View</h3>
      <div className="chart-container" style={{ height: '500px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={headers[0]}
              angle={-45}
              textAnchor="end"
              height={100}
              interval="preserveStartEnd"
            />
            <YAxis />
            <Tooltip />
            <Legend />
            {numericColumns.map((col, idx) => (
              <Line
                key={col}
                type="monotone"
                dataKey={col}
                stroke={colors[idx % colors.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Data Table</h3>
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
