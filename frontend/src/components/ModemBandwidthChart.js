import React, { useRef } from 'react';
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
import CopyChartButton from './CopyChartButton';

function ModemBandwidthChart({ data }) {
  const aggregatedRef = useRef(null);
  const bandwidthRefs = useRef({});
  const rttRefs = useRef({});
  const borderColor = 'var(--border-color)';
  const cardBackground = 'var(--bg-card)';
  const surfaceTertiary = 'var(--bg-tertiary)';
  const textSecondary = 'var(--text-secondary)';
  const textPrimary = 'var(--text-primary)';
  const infoLight = 'var(--info-light)';
  const infoColor = 'var(--info)';
  const brandPrimary = 'var(--brand-primary)';
  const successColor = 'var(--success)';
  const warningColor = 'var(--warning)';
  const errorColor = 'var(--error)';
  const infoAccent = 'var(--info)';

  if (!data || !data.modems || Object.keys(data.modems).length === 0) {
    return <div style={{ margin: '20px 0', textAlign: 'center', color: textSecondary }}>No modem bandwidth data available</div>;
  }

  const modemIds = Object.keys(data.modems).sort((a, b) => parseInt(a) - parseInt(b));
  const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#ea580c', '#be123c'];

  return (
    <div>
      {/* Aggregated Total Bandwidth Chart */}
      <div className="chart-header" style={{ marginBottom: '15px' }}>
        <h3>Total Bandwidth (All Modems Aggregated)</h3>
        <CopyChartButton targetRef={aggregatedRef} fileName="modem-bandwidth-aggregated.png" />
      </div>
      <div ref={aggregatedRef} className="chart-container" style={{ height: '400px', marginBottom: '40px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.aggregated}>
            <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
            <XAxis
              dataKey="datetime"
              angle={-45}
              textAnchor="end"
              height={100}
              interval={Math.floor(data.aggregated.length / 10) || 1}
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
            <Area
              type="monotone"
              dataKey="total_bw"
              name="Total Bandwidth"
              stroke={brandPrimary}
              fill={brandPrimary}
              fillOpacity={0.3}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Modem Charts */}
      <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
        Per-Modem Analysis
      </h3>

      {modemIds.map((modemId, idx) => {
        const modemData = data.modems[modemId];
        const color = colors[idx % colors.length];
        const bandwidthRef = bandwidthRefs.current[modemId] || (bandwidthRefs.current[modemId] = React.createRef());
        const rttRef = rttRefs.current[modemId] || (rttRefs.current[modemId] = React.createRef());

        return (
          <div key={modemId} style={{ marginBottom: '50px' }}>
            <h4 style={{
              marginBottom: '20px',
              padding: '10px 15px',
              background: brandPrimary,
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
                <div className="chart-header chart-header-sm">
                  <h5>Bandwidth Metrics</h5>
                  <CopyChartButton targetRef={bandwidthRef} fileName={`modem-${modemId}-bandwidth.png`} />
                </div>
                <div ref={bandwidthRef} className="chart-container" style={{ height: '350px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={modemData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                      <XAxis
                        dataKey="datetime"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        interval={Math.floor(modemData.length / 8) || 1}
                        tick={{ fontSize: 10, fill: textSecondary }}
                      />
                      <YAxis label={{ value: 'Kbps', angle: -90, position: 'insideLeft', fill: textSecondary }} tick={{ fill: textSecondary }} />
                      <Tooltip
                        contentStyle={{
                          background: cardBackground,
                          border: `1px solid ${borderColor}`,
                          borderRadius: '8px',
                          color: textPrimary
                        }}
                      />
                      <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '0.85rem', paddingBottom: '8px' }} />
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
                        stroke={errorColor}
                        strokeWidth={2}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* RTT Chart */}
              <div>
                <div className="chart-header chart-header-sm">
                  <h5>Round Trip Time</h5>
                  <CopyChartButton targetRef={rttRef} fileName={`modem-${modemId}-rtt.png`} />
                </div>
                <div ref={rttRef} className="chart-container" style={{ height: '350px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={modemData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                      <XAxis
                        dataKey="datetime"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        interval={Math.floor(modemData.length / 8) || 1}
                        tick={{ fontSize: 10, fill: textSecondary }}
                      />
                      <YAxis label={{ value: 'ms', angle: -90, position: 'insideLeft', fill: textSecondary }} tick={{ fill: textSecondary }} />
                      <Tooltip
                        contentStyle={{
                          background: cardBackground,
                          border: `1px solid ${borderColor}`,
                          borderRadius: '8px',
                          color: textPrimary
                        }}
                      />
                      <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '0.85rem', paddingBottom: '8px' }} />
                      <Line
                        type="monotone"
                        dataKey="shortest_rtt"
                        name="Shortest RTT"
                        stroke={successColor}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="smooth_rtt"
                        name="Smooth RTT"
                        stroke={warningColor}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="min_rtt"
                        name="Min RTT"
                        stroke={infoAccent}
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
              background: surfaceTertiary,
              borderRadius: '8px'
            }}>
              {Object.entries({
                'Avg BW': modemData.reduce((sum, d) => sum + d.potential_bw, 0) / modemData.length,
                'Avg Upstream': modemData.reduce((sum, d) => sum + d.upstream, 0) / modemData.length,
                'Avg RTT': modemData.reduce((sum, d) => sum + d.smooth_rtt, 0) / modemData.length,
                'Samples': modemData.length
              }).map(([key, value]) => (
                <div key={key} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: textSecondary }}>{key}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: textPrimary }}>
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
        background: infoLight,
        borderLeft: `4px solid ${brandPrimary}`,
        borderRadius: '4px'
      }}>
        <strong>Tip:</strong> Check the "Raw Output" tab for detailed CSV data
      </div>
    </div>
  );
}

export default ModemBandwidthChart;
