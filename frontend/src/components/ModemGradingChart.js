import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

const ModemGradingChart = ({ data }) => {
  const [selectedModem, setSelectedModem] = useState('all');

  // Process data for visualization
  const { modemStats, serviceTimeline, qualityData } = useMemo(() => {
    if (!data || !data.modems || data.modems.length === 0) {
      return { modemStats: [], serviceTimeline: [], qualityData: [] };
    }

    const stats = data.modems.map(modem => {
      const fullServiceCount = modem.service_changes.filter(
        s => s.service_level === 'Full'
      ).length;
      const limitedServiceCount = modem.service_changes.filter(
        s => s.service_level === 'Limited'
      ).length;
      const goodQualityCount = modem.quality_metrics.filter(
        m => m.is_good_quality
      ).length;
      const badQualityCount = modem.quality_metrics.filter(
        m => !m.is_good_quality
      ).length;

      // Get current service level (last change)
      const currentService = modem.service_changes.length > 0
        ? modem.service_changes[modem.service_changes.length - 1].service_level
        : 'Unknown';

      return {
        modem_id: modem.modem_id,
        full_service: fullServiceCount,
        limited_service: limitedServiceCount,
        good_quality: goodQualityCount,
        bad_quality: badQualityCount,
        current_service: currentService,
        total_events: modem.events.length
      };
    });

    // Create timeline data for service changes
    const timeline = [];
    data.modems.forEach(modem => {
      modem.service_changes.forEach(change => {
        timeline.push({
          timestamp: change.timestamp,
          modem_id: modem.modem_id,
          service_level: change.service_level,
          service_value: change.service_level === 'Full' ? 1 : 0
        });
      });
    });
    timeline.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

    // Create quality metrics data
    const quality = [];
    data.modems.forEach(modem => {
      modem.quality_metrics.forEach(metric => {
        quality.push({
          timestamp: metric.timestamp,
          modem_id: modem.modem_id,
          metric1: metric.metric1,
          metric2: metric.metric2,
          is_good: metric.is_good_quality
        });
      });
    });
    quality.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

    return { modemStats: stats, serviceTimeline: timeline, qualityData: quality };
  }, [data]);

  // Filter data by selected modem
  const filteredTimeline = useMemo(() => {
    if (selectedModem === 'all') return serviceTimeline;
    return serviceTimeline.filter(t => t.modem_id === parseInt(selectedModem));
  }, [serviceTimeline, selectedModem]);

  const filteredQuality = useMemo(() => {
    if (selectedModem === 'all') return qualityData;
    return qualityData.filter(q => q.modem_id === parseInt(selectedModem));
  }, [qualityData, selectedModem]);

  if (!data || !data.modems || data.modems.length === 0) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        color: '#666',
        background: '#f8f9fa',
        borderRadius: '8px',
        margin: '20px 0'
      }}>
        No modem grading data available
      </div>
    );
  }

  return (
    <div style={{ padding: '20px 0' }}>
      {/* Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px'
      }}>
        {modemStats.map(stat => (
          <div
            key={stat.modem_id}
            style={{
              background: 'white',
              padding: '20px',
              borderRadius: '12px',
              border: `3px solid ${stat.current_service === 'Full' ? '#059669' : '#dc2626'}`,
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              opacity: selectedModem === 'all' || selectedModem === stat.modem_id.toString() ? 1 : 0.6,
              transform: selectedModem === stat.modem_id.toString() ? 'scale(1.02)' : 'scale(1)'
            }}
            onClick={() => setSelectedModem(
              selectedModem === stat.modem_id.toString() ? 'all' : stat.modem_id.toString()
            )}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '10px'
            }}>
              <h3 style={{ margin: 0, color: '#333', fontSize: '18px' }}>
                Modem {stat.modem_id}
              </h3>
              <span style={{
                background: stat.current_service === 'Full' ? '#059669' : '#dc2626',
                color: 'white',
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                {stat.current_service}
              </span>
            </div>
            <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.8' }}>
              <div><strong>Full Service:</strong> {stat.full_service}×</div>
              <div><strong>Limited Service:</strong> {stat.limited_service}×</div>
              <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #eee' }}>
                <div><strong>Good Quality:</strong> {stat.good_quality}</div>
                <div><strong>Bad Quality:</strong> {stat.bad_quality}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Info */}
      {selectedModem !== 'all' && (
        <div style={{
          padding: '12px 20px',
          background: '#e3f2fd',
          borderRadius: '8px',
          marginBottom: '20px',
          color: '#1976d2',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span>Showing: <strong>Modem {selectedModem}</strong></span>
          <button
            onClick={() => setSelectedModem('all')}
            style={{
              background: '#1976d2',
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

      {/* Service Level Timeline */}
      <div style={{
        background: 'white',
        padding: '20px',
        borderRadius: '12px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        marginBottom: '30px'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#333' }}>
          Service Level Timeline
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={filteredTimeline}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={Math.floor(filteredTimeline.length / 10) || 1}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 1]}
              tickFormatter={(value) => value === 1 ? 'Full' : 'Limited'}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div style={{
                      background: 'white',
                      padding: '10px',
                      border: '1px solid #ddd',
                      borderRadius: '8px'
                    }}>
                      <div><strong>Modem:</strong> {data.modem_id}</div>
                      <div><strong>Service:</strong> {data.service_level}</div>
                      <div><strong>Time:</strong> {data.timestamp}</div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px' }} />
            <Line
              type="stepAfter"
              dataKey="service_value"
              stroke="#2563eb"
              strokeWidth={3}
              dot={{ r: 5, fill: '#2563eb' }}
              name="Service Level"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Quality Metrics Chart */}
      <div style={{
        background: 'white',
        padding: '20px',
        borderRadius: '12px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        marginBottom: '30px'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#333' }}>
          Quality Metrics Over Time
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={filteredQuality.slice(0, 50)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={100}
              interval={Math.floor(filteredQuality.slice(0, 50).length / 8) || 1}
            />
            <YAxis />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div style={{
                      background: 'white',
                      padding: '10px',
                      border: '1px solid #ddd',
                      borderRadius: '8px'
                    }}>
                      <div><strong>Modem:</strong> {data.modem_id}</div>
                      <div><strong>Metric 1:</strong> {data.metric1}</div>
                      <div><strong>Metric 2:</strong> {data.metric2}</div>
                      <div><strong>Status:</strong> {data.is_good ? 'Good' : 'Bad'}</div>
                      <div><strong>Time:</strong> {data.timestamp}</div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px' }} />
            <Bar dataKey="metric1" name="Metric 1">
              {filteredQuality.slice(0, 50).map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.is_good ? '#059669' : '#dc2626'} />
              ))}
            </Bar>
            <Bar dataKey="metric2" fill="#d97706" name="Metric 2" />
          </BarChart>
        </ResponsiveContainer>
        {filteredQuality.length > 50 && (
          <div style={{ textAlign: 'center', marginTop: '10px', color: '#666', fontSize: '14px' }}>
            Showing first 50 of {filteredQuality.length} quality measurements
          </div>
        )}
      </div>

      {/* Events Table */}
      <div style={{
        background: 'white',
        padding: '20px',
        borderRadius: '12px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '15px', color: '#333' }}>
          Service Change Events
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '14px'
          }}>
            <thead>
              <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Timestamp</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Modem ID</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Service Level</th>
                <th style={{ padding: '12px', textAlign: 'center' }}>Event Type</th>
              </tr>
            </thead>
            <tbody>
              {data.all_events
                .filter(event => selectedModem === 'all' || event.modem_id === parseInt(selectedModem))
                .filter(event => event.event_type === 'service_change')
                .slice(0, 100)
                .map((event, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: '1px solid #f0f0f0',
                      background: event.service_level === 'Limited' ? '#fff3cd' : 'white'
                    }}
                  >
                    <td style={{ padding: '10px' }}>{event.timestamp}</td>
                    <td style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                      {event.modem_id}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'center' }}>
                      <span style={{
                        background: event.service_level === 'Full' ? '#059669' : '#dc2626',
                        color: 'white',
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {event.service_level}
                      </span>
                    </td>
                    <td style={{ padding: '10px', textAlign: 'center', color: '#666' }}>
                      Service Change
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ModemGradingChart;
