import React, { useRef } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import CopyChartButton from './CopyChartButton';

function ModemStats({ modems }) {
  const bandwidthChartRef = useRef(null);
  const lossChartRef = useRef(null);
  const delayChartRef = useRef(null);

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
    Average: modem.stats.loss?.avg || 0,
  }));

  // Prepare data for delay chart
  const delayData = modems.map(modem => ({
    name: `Modem ${modem.modem_id}`,
    'Upstream Delay': modem.stats.up_delay?.avg || 0,
    'Smooth RTT': modem.stats.smooth_rtt?.avg || 0,
    'Shortest RTT': modem.stats.shortest_rtt?.avg || 0,
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

      <div className="chart-header">
        <h3>Bandwidth Analysis (kbps)</h3>
        <CopyChartButton targetRef={bandwidthChartRef} fileName="modem-bandwidth-analysis.png" />
      </div>
      <div ref={bandwidthChartRef} className="chart-container">
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

      <div className="chart-header">
        <h3>Packet Loss (%)</h3>
        <CopyChartButton targetRef={lossChartRef} fileName="modem-packet-loss.png" />
      </div>
      <div ref={lossChartRef} className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={lossData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="Average" fill="#667eea" />
          </BarChart>
        </ResponsiveContainer>
      </div>

     <div className="chart-header">
       <h3>Delay Analysis (ms)</h3>
       <CopyChartButton targetRef={delayChartRef} fileName="modem-delay-analysis.png" />
     </div>
     <div ref={delayChartRef} className="chart-container">
       <ResponsiveContainer width="100%" height="100%">
          <BarChart data={delayData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="Upstream Delay" fill="#82ca9d" />
            <Bar dataKey="Smooth RTT" fill="#667eea" />
            <Bar dataKey="Shortest RTT" fill="#ff6b6b" />
            <Bar dataKey="Min RTT" fill="#ffd93d" />
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
                  Avg: {modem.stats.loss?.avg.toFixed(1) || 'N/A'}
                </td>
                <td>
                  Up Delay Avg: {modem.stats.up_delay?.avg?.toFixed(1) || 'N/A'}<br />
                  Smooth RTT Avg: {modem.stats.smooth_rtt?.avg?.toFixed(1) || 'N/A'}<br />
                  Shortest RTT Avg: {modem.stats.shortest_rtt?.avg?.toFixed(1) || 'N/A'}<br />
                  Min RTT Avg: {modem.stats.min_rtt?.avg?.toFixed(1) || 'N/A'}
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
