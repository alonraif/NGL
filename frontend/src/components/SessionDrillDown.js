import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ModemStats from './ModemStats';
import BandwidthChart from './BandwidthChart';
import ModemBandwidthChart from './ModemBandwidthChart';
import MemoryChart from './MemoryChart';
import ModemGradingChart from './ModemGradingChart';
import CpuChart from './CpuChart';

// Parsers with visualizations (used for rendering)
const VISUALIZATION_PARSERS = ['bw', 'md-bw', 'md-db-bw', 'md', 'memory', 'grading', 'cpu'];

function SessionDrillDown({ session, analysisData, savedResults, onResultsChange }) {
  const [availableParsers, setAvailableParsers] = useState([]);
  const [selectedParsers, setSelectedParsers] = useState(new Set());
  const [endTime, setEndTime] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState(savedResults || []);
  const [error, setError] = useState('');
  const [expandedResults, setExpandedResults] = useState(new Set());
  const [parserStatuses, setParserStatuses] = useState({}); // Track status of each parser: queued, running, completed, failed
  const [loadingParsers, setLoadingParsers] = useState(true);
  const pollingRef = useRef(null);

  const isComplete = session.type === 'complete';
  const needsEndTime = !isComplete && !session.end;

  // Fetch available parsers from API
  useEffect(() => {
    const fetchParsers = async () => {
      try {
        const response = await axios.get('/api/parse-modes');
        // Map parsers to include hasVisualization flag
        const parsers = response.data.map(parser => ({
          value: parser.value,
          label: parser.label,
          hasVisualization: VISUALIZATION_PARSERS.includes(parser.value)
        }));
        setAvailableParsers(parsers);
      } catch (error) {
        console.error('Failed to fetch parsers:', error);
        // Fallback to empty list
        setAvailableParsers([]);
      } finally {
        setLoadingParsers(false);
      }
    };

    fetchParsers();
  }, []);

  // Set end time from session if available
  useEffect(() => {
    if (session.end && !isComplete) {
      setEndTime(session.end);
    }
  }, [session.end, isComplete]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);

  const toggleParser = (parserValue) => {
    const newSelected = new Set(selectedParsers);
    if (newSelected.has(parserValue)) {
      newSelected.delete(parserValue);
    } else {
      newSelected.add(parserValue);
    }
    setSelectedParsers(newSelected);
  };

  const toggleResultExpand = (index) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedResults(newExpanded);
  };

  const startPolling = (analysisEntries, parsersArray) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    setError('');

    if (!analysisEntries || analysisEntries.length === 0) {
      setIsRunning(false);
      return;
    }

    const idMap = {};
    analysisEntries.forEach(entry => {
      if (entry && entry.parse_mode && entry.analysis_id) {
        idMap[entry.parse_mode] = entry.analysis_id;
      }
    });

    const modes = Object.keys(idMap);
    if (modes.length === 0) {
      setIsRunning(false);
      return;
    }

    const missingModes = parsersArray.filter(mode => !idMap[mode]);
    if (missingModes.length > 0) {
      setParserStatuses(prev => {
        const updated = { ...prev };
        missingModes.forEach(mode => {
          updated[mode] = {
            ...(updated[mode] || {}),
            status: 'failed',
            error: 'Analysis not created'
          };
        });
        return updated;
      });
    }

    const failureSet = new Set();
    const pending = new Set(modes);
    const order = [...parsersArray];
    missingModes.forEach(mode => failureSet.add(mode));

    const fetchStatuses = async () => {
      if (pending.size === 0) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setIsRunning(false);
        setError(failureSet.size > 0 ? `Some analyses failed: ${Array.from(failureSet).join(', ')}` : '');
        return;
      }

      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      await Promise.all([...pending].map(async (mode) => {
        const analysisId = idMap[mode];
        if (!analysisId) {
          pending.delete(mode);
          failureSet.add(mode);
          setParserStatuses(prev => ({
            ...prev,
            [mode]: { ...(prev[mode] || {}), status: 'failed', error: 'Missing analysis ID' }
          }));
          return;
        }

        try {
          const response = await axios.get(`/api/analyses/${analysisId}`, { headers });
          const { analysis, result } = response.data;
          if (!analysis) {
            return;
          }

          const status = analysis.status;

          if (status === 'completed') {
            pending.delete(mode);
            setParserStatuses(prev => ({
              ...prev,
              [mode]: { ...(prev[mode] || {}), status: 'completed' }
            }));

            if (result) {
              const completedResult = {
                ...result,
                parse_mode: analysis.parse_mode,
                analysis_id: analysis.id
              };

              setResults(prev => {
                const filtered = prev.filter(item => item.analysis_id !== analysis.id);
                const updated = [...filtered, completedResult];
                updated.sort((a, b) => order.indexOf(a.parse_mode) - order.indexOf(b.parse_mode));
                if (onResultsChange) {
                  onResultsChange(updated);
                }
                return updated;
              });
            }
          } else if (status === 'failed' || status === 'cancelled') {
            pending.delete(mode);
            failureSet.add(mode);
            setParserStatuses(prev => ({
              ...prev,
              [mode]: {
                ...(prev[mode] || {}),
                status,
                error: analysis.error_message || 'Analysis failed'
              }
            }));
          } else {
            setParserStatuses(prev => ({
              ...prev,
              [mode]: { ...(prev[mode] || {}), status: 'running' }
            }));
          }
        } catch (err) {
          pending.delete(mode);
          failureSet.add(mode);
          setParserStatuses(prev => ({
            ...prev,
            [mode]: {
              ...(prev[mode] || {}),
              status: 'failed',
              error: err.response?.data?.error || err.message || 'Failed to fetch status'
            }
          }));
        }
      }));

      if (pending.size === 0) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setIsRunning(false);
        setError(failureSet.size > 0 ? `Some analyses failed: ${Array.from(failureSet).join(', ')}` : '');
      }
    };

    fetchStatuses();
    if (pending.size > 0) {
      pollingRef.current = setInterval(fetchStatuses, 4000);
    }
  };

  const handleRunAnalysis = async () => {
    if (selectedParsers.size === 0) {
      setError('Please select at least one parser');
      return;
    }

    if (needsEndTime && !endTime) {
      setError('Please specify an end time for this incomplete session');
      return;
    }

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    setIsRunning(true);
    setError('');
    setResults([]);
    if (onResultsChange) {
      onResultsChange([]);
    }

    const parsersArray = Array.from(selectedParsers);

    const initialStatuses = {};
    parsersArray.forEach((parser, idx) => {
      initialStatuses[parser] = { status: 'queued', position: idx + 1 };
    });
    setParserStatuses(initialStatuses);

    try {
      const response = await axios.post('/api/analyses/from-session', {
        parent_analysis_id: analysisData.analysisId,
        log_file_id: analysisData.logFileId,
        session_start: session.start,
        session_end: isComplete ? session.end : endTime,
        parse_modes: parsersArray,
        timezone: analysisData.timezone || 'UTC',
        session_name: analysisData.sessionName || 'Session Analysis',
        zendesk_case: analysisData.zendeskCase || ''
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.data.success) {
        const analysisEntries = response.data.analyses || [];
        setParserStatuses(prev => {
          const updated = { ...prev };
          parsersArray.forEach(parseMode => {
            updated[parseMode] = { ...(updated[parseMode] || {}), status: 'running' };
          });
          return updated;
        });

        startPolling(analysisEntries, parsersArray);
      } else {
        setParserStatuses(prev => {
          const updated = { ...prev };
          parsersArray.forEach(parseMode => {
            updated[parseMode] = { ...updated[parseMode], status: 'failed' };
          });
          return updated;
        });
        setIsRunning(false);
        setError(response.data.error || 'Failed to run drill-down analysis');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || 'Failed to run drill-down analysis';
      setParserStatuses(prev => {
        const updated = { ...prev };
        parsersArray.forEach(parseMode => {
          updated[parseMode] = { ...updated[parseMode], status: 'failed' };
        });
        return updated;
      });
      setError(errorMsg);
      console.error('Drill-down error:', err);
      setIsRunning(false);
    }
  };

  const renderVisualization = (result) => {
    if (!result.parsed_data) return null;

    switch (result.parse_mode) {
      case 'md':
        return <ModemStats modems={result.parsed_data} />;
      case 'md-bw':
        return <ModemBandwidthChart data={result.parsed_data} />;
      case 'bw':
      case 'md-db-bw':
        return <BandwidthChart data={result.parsed_data} mode={result.parse_mode} />;
      case 'memory':
        return <MemoryChart data={result.parsed_data} />;
      case 'grading':
        return <ModemGradingChart data={result.parsed_data} />;
      case 'cpu':
        return <CpuChart data={result.parsed_data} />;
      default:
        return null;
    }
  };

  const textPrimary = 'var(--text-primary)';
  const textSecondary = 'var(--text-secondary)';
  const borderColor = 'var(--border-color)';
  const primaryColor = 'var(--primary)';
  const cardBackground = 'var(--bg-card)';
  const totalParsers = Object.keys(parserStatuses).length;
  const completedCount = Object.values(parserStatuses).filter(
    status => ['completed', 'failed', 'cancelled'].includes(status?.status)
  ).length;

  return (
    <div style={{
      padding: '20px',
      background: 'var(--bg-secondary)',
      borderTop: `2px solid ${borderColor}`
    }}>
      <h4 style={{ color: textPrimary, marginTop: 0, marginBottom: '15px' }}>
        Session Drill-Down Analysis
      </h4>

      {/* Session Info */}
      <div style={{
        background: cardBackground,
        padding: '15px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: `1px solid ${borderColor}`
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          <div>
            <strong style={{ color: textSecondary }}>Session ID:</strong>
            <div style={{ color: textPrimary }}>{session.session_id || 'N/A'}</div>
          </div>
          <div>
            <strong style={{ color: textSecondary }}>Start Time:</strong>
            <div style={{ color: textPrimary }}>{session.start || '-'}</div>
          </div>
          <div>
            <strong style={{ color: textSecondary }}>End Time:</strong>
            <div style={{ color: textPrimary }}>{session.end || '-'}</div>
          </div>
          <div>
            <strong style={{ color: textSecondary }}>Duration:</strong>
            <div style={{ color: textPrimary }}>{session.duration || '-'}</div>
          </div>
        </div>
      </div>

      {/* End Time Input for Incomplete Sessions */}
      {needsEndTime && (
        <div style={{
          background: 'var(--warning-bg)',
          padding: '15px',
          borderRadius: '8px',
          marginBottom: '20px',
          border: `1px solid var(--warning)`
        }}>
          <strong style={{ color: 'var(--warning)' }}>Incomplete Session:</strong>
          <p style={{ color: textSecondary, marginBottom: '10px', marginTop: '5px' }}>
            This session doesn't have an end time. Please specify one to run the analysis.
          </p>
          <input
            type="text"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            placeholder="e.g., 14:35:20 or 2025-10-13 14:35:20"
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              border: `2px solid ${borderColor}`,
              fontSize: '0.9rem',
              background: cardBackground,
              color: textPrimary,
              width: '100%',
              maxWidth: '400px'
            }}
          />
        </div>
      )}

      {/* Parser Selection */}
      <div style={{ marginBottom: '20px' }}>
        <strong style={{ color: textPrimary, display: 'block', marginBottom: '10px' }}>
          Select Parsers to Run:
        </strong>
        {loadingParsers ? (
          <div style={{ color: textSecondary, padding: '10px' }}>Loading parsers...</div>
        ) : availableParsers.length === 0 ? (
          <div style={{ color: 'var(--error)', padding: '10px' }}>No parsers available</div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '10px'
          }}>
            {availableParsers.map(parser => (
            <label
              key={parser.value}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px',
                background: selectedParsers.has(parser.value) ? 'var(--primary-light)' : cardBackground,
                border: `2px solid ${selectedParsers.has(parser.value) ? primaryColor : borderColor}`,
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <input
                type="checkbox"
                checked={selectedParsers.has(parser.value)}
                onChange={() => toggleParser(parser.value)}
                style={{ cursor: 'pointer' }}
              />
              <span style={{ color: textPrimary, fontSize: '0.9rem' }}>{parser.label}</span>
            </label>
          ))}
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div style={{
          background: 'var(--error-bg)',
          color: 'var(--error)',
          padding: '12px',
          borderRadius: '6px',
          marginBottom: '15px',
          border: '1px solid var(--error)'
        }}>
          {error}
        </div>
      )}

      {/* Run Button */}
      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={handleRunAnalysis}
          disabled={isRunning || selectedParsers.size === 0 || (needsEndTime && !endTime)}
          className="btn btn-primary"
          style={{
            padding: '12px 24px',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: isRunning || selectedParsers.size === 0 ? 'not-allowed' : 'pointer',
            opacity: isRunning || selectedParsers.size === 0 ? 0.6 : 1
          }}
        >
          {isRunning ? 'Running Analyses...' : `Run ${selectedParsers.size} Selected Analysis${selectedParsers.size !== 1 ? 'es' : ''}`}
        </button>
      </div>

      {/* Progress Indicators */}
      {totalParsers > 0 && (
        <div style={{
          background: 'var(--info-light)',
          padding: '15px',
          borderRadius: '8px',
          marginBottom: '20px',
          border: '1px solid var(--info)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <strong style={{ color: 'var(--info)' }}>
              {isRunning ? 'Processing Drill-Down Analyses' : 'Drill-Down Analyses'}
            </strong>
            <span style={{ color: textSecondary, fontSize: '0.9rem' }}>
              {completedCount} / {totalParsers} completed
            </span>
          </div>

          {/* Progress Bar */}
          <div style={{
            width: '100%',
            height: '8px',
            background: borderColor,
            borderRadius: '4px',
            overflow: 'hidden',
            marginBottom: '15px'
          }}>
            <div style={{
              height: '100%',
              background: 'linear-gradient(90deg, var(--brand-primary) 0%, var(--brand-primary-hover) 100%)',
              width: `${totalParsers === 0 ? 0 : (completedCount / totalParsers) * 100}%`,
              transition: 'width 0.5s ease'
            }} />
          </div>

          {/* Parser Status List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Array.from(selectedParsers).map(parserValue => {
              const parser = availableParsers.find(p => p.value === parserValue);
              const status = parserStatuses[parserValue]?.status || 'queued';

              let statusIcon = '⏳';
              let statusText = 'Queued';
              let statusColor = textSecondary;

              if (status === 'running') {
                statusIcon = '⚙️';
                statusText = 'Running';
                statusColor = 'var(--info)';
              } else if (status === 'completed') {
                statusIcon = '✅';
                statusText = 'Completed';
                statusColor = 'var(--success)';
              } else if (status === 'failed') {
                statusIcon = '❌';
                statusText = 'Failed';
                statusColor = 'var(--error)';
              } else if (status === 'cancelled') {
                statusIcon = '🚫';
                statusText = 'Cancelled';
                statusColor = 'var(--error)';
              }

              return (
                <div
                  key={parserValue}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: status === 'running' ? 'var(--info-bg)' : cardBackground,
                    borderRadius: '6px',
                    border: `1px solid ${status === 'running' ? 'var(--info)' : borderColor}`
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '1.2rem' }}>{statusIcon}</span>
                    <span style={{ color: textPrimary, fontWeight: status === 'running' ? '600' : '400' }}>
                      {parser?.label || parserValue}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                    <span style={{ color: statusColor, fontSize: '0.85rem', fontWeight: '600' }}>
                      {statusText}
                    </span>
                    {parserStatuses[parserValue]?.error && (
                      <span style={{ color: 'var(--error)', fontSize: '0.75rem' }}>
                        {parserStatuses[parserValue]?.error}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div style={{
          background: cardBackground,
          padding: '15px',
          borderRadius: '8px',
          border: `1px solid ${borderColor}`
        }}>
          <h5 style={{ color: textPrimary, marginTop: 0 }}>
            Drill-Down Results ({results.length})
          </h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {results.map((result, idx) => {
              const parser = availableParsers.find(p => p.value === result.parse_mode);
              const hasVisualization = parser?.hasVisualization || VISUALIZATION_PARSERS.includes(result.parse_mode);
              const isExpanded = expandedResults.has(idx);

              return (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${borderColor}`,
                    borderRadius: '6px',
                    overflow: 'hidden'
                  }}
                >
                  <div
                    onClick={() => hasVisualization && toggleResultExpand(idx)}
                    style={{
                      padding: '12px 15px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: hasVisualization ? 'pointer' : 'default',
                      background: isExpanded ? 'var(--primary-light)' : 'transparent'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {hasVisualization && (
                        <span style={{
                          transition: 'transform 0.2s',
                          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'
                        }}>
                          ▶
                        </span>
                      )}
                      <strong style={{ color: textPrimary }}>{parser?.label || result.parse_mode}</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                      <span style={{
                        padding: '4px 10px',
                        background: 'var(--success-light)',
                        color: 'var(--success)',
                        borderRadius: '12px',
                        fontSize: '0.85rem',
                        fontWeight: '600'
                      }}>
                        {result.status}
                      </span>
                      <span style={{ color: textSecondary, fontSize: '0.85rem' }}>
                        {result.processing_time}s
                      </span>
                    </div>
                  </div>

                  {hasVisualization && isExpanded && (
                    <div style={{
                      padding: '15px',
                      background: cardBackground,
                      borderTop: `1px solid ${borderColor}`
                    }}>
                      {renderVisualization(result)}
                    </div>
                  )}

                  {!hasVisualization && (
                    <div style={{
                      padding: '10px 15px',
                      color: textSecondary,
                      fontSize: '0.85rem',
                      fontStyle: 'italic'
                    }}>
                      View full results in Analysis History
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default SessionDrillDown;
