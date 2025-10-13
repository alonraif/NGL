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

const CpuChart = ({ data }) => {
  const [selectedComponent, setSelectedComponent] = useState('all');
  const [activeView, setActiveView] = useState('utilization'); // 'utilization' or 'idle'
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

  // Process data to organize by component and core
  const { chartData, components, coreData, stats } = useMemo(() => {
    if (!data || data.length === 0) {
      return { chartData: [], components: [], coreData: {}, stats: {} };
    }

    // Group data by timestamp
    const timeMap = {};
    const componentSet = new Set();
    const componentStats = {};
    const componentCores = {};

    data.forEach(point => {
      const comp = point.component;
      componentSet.add(comp);

      // Track which cores this component has
      if (point.core_index !== null && point.core_index !== undefined) {
        if (!componentCores[comp]) {
          componentCores[comp] = new Set();
        }
        componentCores[comp].add(point.core_index);
      }

      // Initialize stats for component
      if (!componentStats[comp]) {
        componentStats[comp] = {
          maxIdle: 0,
          minIdle: 100,
          avgIdle: 0,
          maxUsage: 0,
          minUsage: 0,
          avgUsage: 0,
          count: 0,
          sum: 0,
          warnings: 0,
          cores: new Set()
        };
      }

      const stats = componentStats[comp];

      // Calculate idle and usage values
      const idleValue = point.idle_percent !== null && point.idle_percent !== undefined
        ? point.idle_percent
        : (point.total_percent !== null && point.total_percent !== undefined
          ? (100 - point.total_percent)
          : null);

      const usageValue = idleValue !== null ? (100 - idleValue) : null;

      if (idleValue !== null) {
        stats.maxIdle = Math.max(stats.maxIdle, idleValue);
        stats.minIdle = Math.min(stats.minIdle, idleValue);
        stats.maxUsage = Math.max(stats.maxUsage, usageValue);
        stats.minUsage = Math.min(stats.minUsage, usageValue);
        stats.sum += usageValue;
        stats.count++;

        if (point.core_index !== null && point.core_index !== undefined) {
          stats.cores.add(point.core_index);
        }

        // Warning if idle is less than 20% (CPU usage > 80%)
        if (point.level === 'WARNING' || idleValue < 20) {
          stats.warnings++;
        }

        // Group by timestamp - use component+core as key for multi-core
        if (!timeMap[point.timestamp]) {
          timeMap[point.timestamp] = { timestamp: point.timestamp };
        }

        // Store per-core data if available
        if (point.core_index !== null && point.core_index !== undefined) {
          const coreKey = `${comp}_core${point.core_index}`;
          timeMap[point.timestamp][`${coreKey}_idle`] = idleValue;
          timeMap[point.timestamp][`${coreKey}_usage`] = usageValue;
        } else {
          // Overall component data
          timeMap[point.timestamp][`${comp}_idle`] = idleValue;
          timeMap[point.timestamp][`${comp}_usage`] = usageValue;
        }

        if (point.level === 'WARNING' || idleValue < 20) {
          timeMap[point.timestamp][`${comp}_warning`] = true;
        }
      }
    });

    // Calculate averages
    Object.keys(componentStats).forEach(comp => {
      if (componentStats[comp].count > 0) {
        componentStats[comp].avgUsage = (componentStats[comp].sum / componentStats[comp].count).toFixed(1);
        componentStats[comp].avgIdle = (100 - componentStats[comp].avgUsage).toFixed(1);
      }
    });

    // Convert to array and sort by timestamp
    const sortedData = Object.values(timeMap).sort((a, b) =>
      a.timestamp.localeCompare(b.timestamp)
    );

    return {
      chartData: sortedData,
      components: Array.from(componentSet),
      coreData: componentCores,
      stats: componentStats
    };
  }, [data]);

  // Generate colors for cores
  const getCoreColors = (component, coreCount) => {
    const baseColors = {
      'VIC': ['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'],
      'Corecard': ['#06b6d4', '#22d3ee', '#67e8f9', '#a5f3fc'],
      'Server': ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'],
      'Unknown': ['#6b7280', '#9ca3af', '#d1d5db', '#e5e7eb']
    };
    return baseColors[component] || baseColors['Unknown'];
  };

  const componentColors = {
    'VIC': '#3b82f6',
    'Corecard': '#06b6d4',
    'Server': '#8b5cf6',
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
        No CPU usage data available
      </div>
    );
  }

  // Determine what lines to show based on selected component
  const getLinesToRender = () => {
    const lines = [];
    const valueKey = activeView === 'idle' ? '_idle' : '_usage';

    if (selectedComponent === 'all') {
      // Show all components
      components.forEach(comp => {
        const cores = coreData[comp];
        if (cores && cores.size > 0) {
          // Show per-core lines
          const colors = getCoreColors(comp, cores.size);
          Array.from(cores).sort((a, b) => a - b).forEach((core, idx) => {
            lines.push({
              key: `${comp}_core${core}${valueKey}`,
              name: `${comp} Core ${core}`,
              color: colors[idx % colors.length]
            });
          });
        } else {
          // Show overall component line
          lines.push({
            key: `${comp}${valueKey}`,
            name: comp,
            color: componentColors[comp]
          });
        }
      });
    } else {
      // Show selected component only
      const cores = coreData[selectedComponent];
      if (cores && cores.size > 0) {
        const colors = getCoreColors(selectedComponent, cores.size);
        Array.from(cores).sort((a, b) => a - b).forEach((core, idx) => {
          lines.push({
            key: `${selectedComponent}_core${core}${valueKey}`,
            name: `Core ${core}`,
            color: colors[idx % colors.length]
          });
        });
      } else {
        lines.push({
          key: `${selectedComponent}${valueKey}`,
          name: selectedComponent,
          color: componentColors[selectedComponent]
        });
      }
    }

    return lines;
  };

  const linesToRender = getLinesToRender();

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
          const coreCount = stat.cores.size;
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
                {coreCount > 0 && (
                  <div style={{ marginBottom: '8px' }}>
                    <strong>Cores:</strong> {coreCount}
                  </div>
                )}
                <div><strong>Avg Usage:</strong> {stat.avgUsage}%</div>
                <div><strong>Max Usage:</strong> {stat.maxUsage.toFixed(1)}%</div>
                <div><strong>Min Usage:</strong> {stat.minUsage.toFixed(1)}%</div>
                <div style={{ marginTop: '8px', color: textTertiary, fontSize: '12px' }}>
                  {stat.count} data points
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* View Toggle */}
      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        justifyContent: 'center'
      }}>
        <button
          onClick={() => setActiveView('utilization')}
          style={{
            background: activeView === 'utilization' ? infoColor : surfaceTertiary,
            color: activeView === 'utilization' ? 'white' : textSecondary,
            border: `2px solid ${activeView === 'utilization' ? infoColor : borderColor}`,
            padding: '10px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            transition: 'all 0.2s'
          }}
        >
          CPU Utilization %
        </button>
        <button
          onClick={() => setActiveView('idle')}
          style={{
            background: activeView === 'idle' ? successColor : surfaceTertiary,
            color: activeView === 'idle' ? 'white' : textSecondary,
            border: `2px solid ${activeView === 'idle' ? successColor : borderColor}`,
            padding: '10px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            transition: 'all 0.2s'
          }}
        >
          CPU Idle %
        </button>
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
          <span>
            Showing: <strong>{selectedComponent}</strong>
            {coreData[selectedComponent] && coreData[selectedComponent].size > 0 &&
              ` (${coreData[selectedComponent].size} cores)`}
          </span>
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

      {/* CPU Chart */}
      <div style={{
        background: cardBackground,
        padding: '20px',
        borderRadius: '12px',
        boxShadow: `0 2px 10px ${shadowColor}`
      }}>
        <div className="chart-header" style={{ marginTop: 0, marginBottom: '20px' }}>
          <h3>
            {activeView === 'idle' ? 'CPU Idle %' : 'CPU Utilization %'} Over Time
            {selectedComponent !== 'all' && ` - ${selectedComponent}`}
          </h3>
          <CopyChartButton targetRef={chartRef} fileName={`cpu-${activeView}.png`} />
        </div>
        <div ref={chartRef}>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 11, fill: textSecondary }}
                angle={-45}
                textAnchor="end"
                height={100}
                interval={Math.floor(chartData.length / 10) || 1}
              />
              <YAxis
                label={{
                  value: activeView === 'idle' ? 'CPU Idle (%)' : 'CPU Utilization (%)',
                  angle: -90,
                  position: 'insideLeft',
                  fill: textSecondary
                }}
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
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px' }}
                iconType="line"
              />

              {/* Reference line at 80% usage / 20% idle */}
              {activeView === 'idle' ? (
                <ReferenceLine
                  y={20}
                  label="Warning (80% usage)"
                  stroke={warningColor}
                  strokeDasharray="3 3"
                />
              ) : (
                <ReferenceLine
                  y={80}
                  label="Warning Threshold"
                  stroke={warningColor}
                  strokeDasharray="3 3"
                />
              )}

              {/* Lines for each component/core */}
              {linesToRender.map(line => (
                <Line
                  key={line.key}
                  type="monotone"
                  dataKey={line.key}
                  stroke={line.color}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  activeDot={{ r: 4 }}
                  name={line.name}
                  connectNulls
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
          CPU Usage Details
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
                <th style={{ padding: '12px', textAlign: 'center' }}>Core</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Idle %</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Usage %</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Level</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {data
                .filter(point => selectedComponent === 'all' || point.component === selectedComponent)
                .slice(0, 100)
                .map((point, idx) => {
                  const idleValue = point.idle_percent !== null && point.idle_percent !== undefined
                    ? point.idle_percent
                    : (point.total_percent !== null && point.total_percent !== undefined
                      ? (100 - point.total_percent)
                      : null);
                  const usageValue = idleValue !== null ? (100 - idleValue).toFixed(1) : '-';
                  const isWarning = point.level === 'WARNING' || (idleValue !== null && idleValue < 20);

                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: `1px solid ${borderColor}`,
                        background: isWarning ? warningBg : cardBackground
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
                      <td style={{ padding: '10px', textAlign: 'center' }}>
                        {point.core_index !== null && point.core_index !== undefined ? point.core_index : '-'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', fontWeight: 'bold' }}>
                        {idleValue !== null ? idleValue.toFixed(1) : '-'}%
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right' }}>
                        {usageValue}%
                      </td>
                      <td style={{ padding: '10px', textAlign: 'center' }}>
                        <span style={{
                          color: point.level === 'WARNING' ? warningColor : infoColor,
                          fontWeight: 'bold',
                          fontSize: '12px'
                        }}>
                          {point.level || 'INFO'}
                        </span>
                      </td>
                      <td style={{ padding: '10px', textAlign: 'center' }}>
                        {isWarning ? (
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
                  );
                })}
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

export default CpuChart;
