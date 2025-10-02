import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

function ModemStats({ modems }) {
  if (!modems || modems.length === 0) {
    return <div>No modem data available</div>;
  }

  // Prepare data for bandwidth chart
  const bandwidthData = modems.map(modem => ({
    name: `Modem ${modem.modem_id}`,
    Low: modem.stats.bandwidth?.low || 0,
    Average: modem.stats.bandwidth?.avg || 0,
    High: modem.stats.bandwidth?.high || 0,
  }));

  // Prepare data for packet loss chart
  const lossData = modems.map(modem => ({
    name: `Modem ${modem.modem_id}`,
    Low: modem.stats.loss?.low || 0,
    Average: modem.stats.loss?.avg || 0,
    High: modem.stats.loss?.high || 0,
  }));

  // Prepare data for delay chart
  const delayData = modems.map(modem => ({
    name: `Modem ${modem.modem_id}`,
    Low: modem.stats.delay?.low || 0,
    Average: modem.stats.delay?.avg || 0,
    High: modem.stats.delay?.high || 0,
  }));

  return (
    <div>
      <div className="stats-grid">
        {modems.map(modem => (
          <div key={modem.modem_id} className="stat-card">
            <h3>Modem {modem.modem_id}</h3>
            <div className="value">
              {modem.stats.bandwidth?.avg.toFixed(0) || 'N/A'}
              <span className="unit">kbps</span>
            </div>
            <p style={{ marginTop: '10px', fontSize: '0.9rem' }}>
              Loss: {modem.stats.loss?.avg.toFixed(1) || 'N/A'}%
            </p>
          </div>
        ))}
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Bandwidth Analysis (kbps)</h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bandwidthData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="Low" fill="#82ca9d" />
            <Bar dataKey="Average" fill="#667eea" />
            <Bar dataKey="High" fill="#764ba2" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Packet Loss (%)</h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={lossData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="Low" stroke="#82ca9d" strokeWidth={2} />
            <Line type="monotone" dataKey="Average" stroke="#667eea" strokeWidth={2} />
            <Line type="monotone" dataKey="High" stroke="#ff6b6b" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Delay Analysis (ms)</h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={delayData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="Low" fill="#82ca9d" />
            <Bar dataKey="Average" fill="#667eea" />
            <Bar dataKey="High" fill="#ff6b6b" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '15px' }}>Detailed Statistics</h3>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Modem</th>
              <th>Bandwidth (kbps)</th>
              <th>Loss (%)</th>
              <th>Delay (ms)</th>
            </tr>
          </thead>
          <tbody>
            {modems.map(modem => (
              <tr key={modem.modem_id}>
                <td><strong>Modem {modem.modem_id}</strong></td>
                <td>
                  L: {modem.stats.bandwidth?.low || 'N/A'}<br />
                  A: {modem.stats.bandwidth?.avg.toFixed(1) || 'N/A'}<br />
                  H: {modem.stats.bandwidth?.high || 'N/A'}
                </td>
                <td>
                  L: {modem.stats.loss?.low || 'N/A'}<br />
                  A: {modem.stats.loss?.avg.toFixed(1) || 'N/A'}<br />
                  H: {modem.stats.loss?.high || 'N/A'}
                </td>
                <td>
                  L: {modem.stats.delay?.low || 'N/A'}<br />
                  A: {modem.stats.delay?.avg.toFixed(1) || 'N/A'}<br />
                  H: {modem.stats.delay?.high || 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ModemStats;
