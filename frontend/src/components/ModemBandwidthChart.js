import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

function ModemBandwidthChart({ data }) {
  if (!data || !data.modems || Object.keys(data.modems).length === 0) {
    return <div>No modem bandwidth data available</div>;
  }

  const modemIds = Object.keys(data.modems).sort((a, b) => parseInt(a) - parseInt(b));
  const colors = ['#667eea', '#764ba2', '#82ca9d', '#ff6b6b', '#ffd93d', '#6bcf7f', '#4ecdc4', '#ff9ff3'];

  return (
    <div>
      {/* Aggregated Total Bandwidth Chart */}
      <h3 style={{ marginBottom: '15px', fontSize: '1.3rem' }}>
        📊 Total Bandwidth (All Modems Aggregated)
      </h3>
      <div className="chart-container" style={{ height: '400px', marginBottom: '40px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.aggregated}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="datetime"
              angle={-45}
              textAnchor="end"
              height={100}
              interval="preserveStartEnd"
            />
            <YAxis label={{ value: 'Bandwidth (Kbps)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="total_bw"
              name="Total Bandwidth"
              stroke="#667eea"
              fill="#667eea"
              fillOpacity={0.6}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Modem Charts */}
      <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
        📡 Per-Modem Analysis
      </h3>

      {modemIds.map((modemId, idx) => {
        const modemData = data.modems[modemId];
        const color = colors[idx % colors.length];

        return (
          <div key={modemId} style={{ marginBottom: '50px' }}>
            <h4 style={{
              marginBottom: '20px',
              padding: '10px 15px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              borderRadius: '8px',
              fontSize: '1.1rem'
            }}>
              Modem {modemId}
            </h4>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '20px',
              marginBottom: '20px'
            }}>
              {/* Bandwidth Chart */}
              <div>
                <h5 style={{ marginBottom: '10px', color: '#555' }}>Bandwidth Metrics</h5>
                <div className="chart-container" style={{ height: '350px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={modemData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="datetime"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        interval="preserveStartEnd"
                        style={{ fontSize: '0.8rem' }}
                      />
                      <YAxis label={{ value: 'Kbps', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: '0.85rem' }} />
                      <Area
                        type="monotone"
                        dataKey="potential_bw"
                        name="Potential BW"
                        stroke={color}
                        fill={color}
                        fillOpacity={0.6}
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="upstream"
                        name="Upstream"
                        stroke="#ff6b6b"
                        strokeWidth={2}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* RTT Chart */}
              <div>
                <h5 style={{ marginBottom: '10px', color: '#555' }}>Round Trip Time</h5>
                <div className="chart-container" style={{ height: '350px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={modemData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="datetime"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        interval="preserveStartEnd"
                        style={{ fontSize: '0.8rem' }}
                      />
                      <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: '0.85rem' }} />
                      <Line
                        type="monotone"
                        dataKey="shortest_rtt"
                        name="Shortest RTT"
                        stroke="#82ca9d"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="smooth_rtt"
                        name="Smooth RTT"
                        stroke="#ffd93d"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="min_rtt"
                        name="Min RTT"
                        stroke="#4ecdc4"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Stats Summary for this modem */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '10px',
              padding: '15px',
              background: '#f8f9fa',
              borderRadius: '8px'
            }}>
              {Object.entries({
                'Avg BW': modemData.reduce((sum, d) => sum + d.potential_bw, 0) / modemData.length,
                'Avg Upstream': modemData.reduce((sum, d) => sum + d.upstream, 0) / modemData.length,
                'Avg RTT': modemData.reduce((sum, d) => sum + d.smooth_rtt, 0) / modemData.length,
                'Samples': modemData.length
              }).map(([key, value]) => (
                <div key={key} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: '#666' }}>{key}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#333' }}>
                    {typeof value === 'number' ? value.toFixed(1) : value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div style={{
        marginTop: '30px',
        padding: '15px',
        background: '#e3f2fd',
        borderLeft: '4px solid #667eea',
        borderRadius: '4px'
      }}>
        <strong>💡 Tip:</strong> Check the "Raw Output" tab for detailed CSV data
      </div>
    </div>
  );
}

export default ModemBandwidthChart;
