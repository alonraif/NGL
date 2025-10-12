import React, { useState, useMemo, useRef } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import CopyChartButton from './CopyChartButton';

const MemoryChart = ({ data }) => {
  const [selectedComponent, setSelectedComponent] = useState('all');
  const chartRef = useRef(null);
  const cardBackground = 'var(--bg-card)';
  const surfaceTertiary = 'var(--bg-tertiary)';
  const borderColor = 'var(--border-color)';
  const textPrimary = 'var(--text-primary)';
  const textSecondary = 'var(--text-secondary)';
  const textTertiary = 'var(--text-tertiary)';
  const shadowColor = 'var(--shadow-color)';
  const infoColor = 'var(--info)';
  const infoLight = 'var(--info-light)';
  const warningColor = 'var(--warning)';
  const warningBg = 'var(--warning-bg)';
  const successColor = 'var(--success)';

  // Process data to organize by component
  const { chartData, components, stats } = useMemo(() => {
    if (!data || data.length === 0) {
      return { chartData: [], components: [], stats: {} };
    }

    // Group data by timestamp
    const timeMap = {};
    const componentSet = new Set();
    const componentStats = {};

    data.forEach(point => {
      componentSet.add(point.component);

      // Initialize stats for component
      if (!componentStats[point.component]) {
        componentStats[point.component] = {
          max: 0,
          min: 100,
          avg: 0,
          count: 0,
          sum: 0,
          warnings: 0,
          maxUsedMB: 0,
          totalMB: point.total_mb
        };
      }

      const stats = componentStats[point.component];
      stats.max = Math.max(stats.max, point.percent);
      stats.min = Math.min(stats.min, point.percent);
      stats.sum += point.percent;
      stats.count++;
      if (point.is_warning) stats.warnings++;
      if (point.used_mb) stats.maxUsedMB = Math.max(stats.maxUsedMB, point.used_mb);
      if (point.total_mb) stats.totalMB = point.total_mb;

      // Group by timestamp
      if (!timeMap[point.timestamp]) {
        timeMap[point.timestamp] = { timestamp: point.timestamp };
      }
      timeMap[point.timestamp][point.component] = point.percent;
      if (point.is_warning) {
        timeMap[point.timestamp][`${point.component}_warning`] = true;
      }
    });

    // Calculate averages
    Object.keys(componentStats).forEach(comp => {
      componentStats[comp].avg = (componentStats[comp].sum / componentStats[comp].count).toFixed(1);
    });

    // Convert to array and sort by timestamp
    const sortedData = Object.values(timeMap).sort((a, b) =>
      a.timestamp.localeCompare(b.timestamp)
    );

    return {
      chartData: sortedData,
      components: Array.from(componentSet),
      stats: componentStats
    };
  }, [data]);

  // Filter data based on selected component
  const filteredData = useMemo(() => {
    if (selectedComponent === 'all') {
      return chartData;
    }
    return chartData.map(point => ({
      timestamp: point.timestamp,
      [selectedComponent]: point[selectedComponent]
    }));
  }, [chartData, selectedComponent]);

  const componentColors = {
    'VIC': '#2563eb',
    'Corecard': '#059669',
    'Server': '#d97706',
    'Unknown': '#6b7280'
  };

  if (!data || data.length === 0) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        color: textSecondary,
        background: surfaceTertiary,
        borderRadius: '8px',
        margin: '20px 0'
      }}>
        No memory usage data available
      </div>
    );
  }

  return (
    <div style={{ padding: '20px 0' }}>
      {/* Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '15px',
        marginBottom: '30px'
      }}>
        {components.map(component => {
          const stat = stats[component];
          return (
            <div
              key={component}
              style={{
                background: cardBackground,
                padding: '20px',
                borderRadius: '12px',
                border: `2px solid ${borderColor}`,
                boxShadow: `0 2px 8px ${shadowColor}`,
                cursor: 'pointer',
                transition: 'all 0.2s',
                opacity: selectedComponent === 'all' || selectedComponent === component ? 1 : 0.6,
                transform: selectedComponent === component ? 'scale(1.02)' : 'scale(1)'
              }}
              onClick={() => setSelectedComponent(
                selectedComponent === component ? 'all' : component
              )}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '10px'
              }}>
                <h3 style={{
                  margin: 0,
                  color: componentColors[component],
                  fontSize: '18px'
                }}>
                  {component}
                </h3>
                {stat.warnings > 0 && (
                  <span style={{
                    background: warningColor,
                    color: 'white',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: 'bold'
                  }}>
                    {stat.warnings} warnings
                  </span>
                )}
              </div>
              <div style={{ fontSize: '14px', color: textSecondary, lineHeight: '1.8' }}>
                <div><strong>Avg:</strong> {stat.avg}%</div>
                <div><strong>Max:</strong> {stat.max}%</div>
                <div><strong>Min:</strong> {stat.min}%</div>
                {stat.maxUsedMB > 0 && (
                  <div><strong>Peak:</strong> {stat.maxUsedMB} MB / {stat.totalMB} MB</div>
                )}
                <div style={{ marginTop: '5px', color: textTertiary, fontSize: '12px' }}>
                  {stat.count} data points
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filter Info */}
      {selectedComponent !== 'all' && (
        <div style={{
          padding: '12px 20px',
          background: infoLight,
          borderRadius: '8px',
          marginBottom: '20px',
          color: infoColor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span>Showing: <strong>{selectedComponent}</strong></span>
          <button
            onClick={() => setSelectedComponent('all')}
            style={{
              background: infoColor,
              color: 'white',
              border: 'none',
              padding: '6px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Show All
          </button>
        </div>
      )}

      {/* Memory Usage Chart */}
      <div style={{
        background: cardBackground,
        padding: '20px',
        borderRadius: '12px',
        boxShadow: `0 2px 10px ${shadowColor}`
      }}>
        <div className="chart-header" style={{ marginTop: 0, marginBottom: '20px' }}>
          <h3>Memory Usage Over Time</h3>
          <CopyChartButton targetRef={chartRef} fileName="memory-usage.png" />
        </div>
        <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 11, fill: textSecondary }}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={Math.floor(filteredData.length / 10) || 1}
            />
            <YAxis
              label={{ value: 'Memory Usage (%)', angle: -90, position: 'insideLeft', fill: textSecondary }}
              domain={[0, 100]}
              tick={{ fill: textSecondary }}
            />
            <Tooltip
              contentStyle={{
                background: cardBackground,
                border: `1px solid ${borderColor}`,
                borderRadius: '8px',
                padding: '10px',
                color: textPrimary
              }}
            />
            <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px' }} />

            {/* Warning threshold line */}
            <ReferenceLine
              y={80}
              label="Warning Threshold"
              stroke={warningColor}
              strokeDasharray="3 3"
            />

            {/* Lines for each component */}
            {(selectedComponent === 'all' ? components : [selectedComponent]).map(component => (
              <Line
                key={component}
                type="monotone"
                dataKey={component}
                stroke={componentColors[component]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name={component}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        </div>
      </div>

      {/* Data Table */}
      <div style={{
        marginTop: '30px',
        background: cardBackground,
        padding: '20px',
        borderRadius: '12px',
        boxShadow: `0 2px 10px ${shadowColor}`
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '15px', color: textPrimary }}>
          Memory Usage Details
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '14px'
          }}>
            <thead>
              <tr style={{ background: surfaceTertiary, borderBottom: `2px solid ${borderColor}` }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Timestamp</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Component</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Usage %</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Used (MB)</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Total (MB)</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Cached (MB)</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {data
                .filter(point => selectedComponent === 'all' || point.component === selectedComponent)
                .slice(0, 100)
                .map((point, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: `1px solid ${borderColor}`,
                    background: point.is_warning ? warningBg : cardBackground
                  }}
                >
                  <td style={{ padding: '10px' }}>{point.timestamp}</td>
                  <td style={{ padding: '10px' }}>
                    <span style={{
                      color: componentColors[point.component],
                      fontWeight: 'bold'
                    }}>
                      {point.component}
                    </span>
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right', fontWeight: 'bold' }}>
                    {point.percent.toFixed(1)}%
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {point.used_mb || '-'}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {point.total_mb || '-'}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {point.cached_mb > 0 ? point.cached_mb : '-'}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'center' }}>
                    {point.is_warning ? (
                      <span style={{
                        background: warningColor,
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: 'bold'
                      }}>
                        WARNING
                      </span>
                    ) : (
                      <span style={{ color: successColor, fontWeight: 'bold' }}>OK</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.length > 100 && (
            <div style={{
              padding: '15px',
              textAlign: 'center',
              color: textSecondary,
              fontSize: '14px'
            }}>
              Showing first 100 of {data.length} data points
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MemoryChart;
