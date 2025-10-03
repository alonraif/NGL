import React, { useState, useEffect } from 'react';

const ParserProgress = ({ parserQueue, currentParser, completedCount, totalCount }) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [liveEstimate, setLiveEstimate] = useState(null);

  // Update elapsed time for current parser every second
  useEffect(() => {
    if (!currentParser) return;

    const interval = setInterval(() => {
      const elapsed = (Date.now() - currentParser.startTime) / 1000;
      setElapsedTime(elapsed);
    }, 1000);

    return () => clearInterval(interval);
  }, [currentParser]);

  // Update live estimate countdown every second
  useEffect(() => {
    if (liveEstimate === null || liveEstimate <= 0) return;

    const interval = setInterval(() => {
      setLiveEstimate(prev => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(interval);
  }, [liveEstimate]);

  // Calculate raw estimate in seconds
  const calculateRawEstimate = () => {
    const remainingCount = totalCount - completedCount;

    if (completedCount === 0) {
      // Use 30s baseline instead of "Calculating..."
      const baselinePerParser = 30; // seconds
      const totalEstimate = baselinePerParser * totalCount;
      const currentElapsed = elapsedTime;
      return Math.max(0, totalEstimate - currentElapsed);
    }

    // After first parser: use actual average
    const completedParsers = parserQueue.filter(p => p.status === 'completed');
    const totalTimeCompleted = completedParsers.reduce((sum, p) => sum + p.time, 0);
    const avgTimePerParser = totalTimeCompleted / completedCount;

    // Account for current parser's elapsed time
    const estimateForRemaining = avgTimePerParser * remainingCount;
    const currentParserElapsed = elapsedTime;

    return Math.max(0, estimateForRemaining - currentParserElapsed);
  };

  // Recalculate estimate when completedCount changes or current parser changes
  useEffect(() => {
    const estimate = calculateRawEstimate();
    setLiveEstimate(estimate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completedCount, currentParser, elapsedTime]);

  // Format estimate for display
  const formatEstimate = () => {
    if (liveEstimate === null) return 'Calculating...';

    const seconds = Math.ceil(liveEstimate);
    const isRoughEstimate = completedCount === 0;

    if (seconds < 60) {
      return `~${seconds} second${seconds !== 1 ? 's' : ''}${isRoughEstimate ? ' (rough estimate)' : ''}`;
    } else {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      const timeStr = `~${mins} minute${mins > 1 ? 's' : ''}${secs > 0 ? ` ${secs} second${secs !== 1 ? 's' : ''}` : ''}`;
      return isRoughEstimate ? `${timeStr} (rough estimate)` : timeStr;
    }
  };

  // Calculate average time per parser
  const getAvgTime = () => {
    if (completedCount === 0) return 0;
    const completedParsers = parserQueue.filter(p => p.status === 'completed');
    const totalTime = completedParsers.reduce((sum, p) => sum + p.time, 0);
    return totalTime / completedCount;
  };

  // Format elapsed time
  const formatElapsed = (seconds) => {
    if (seconds < 60) {
      return `${Math.floor(seconds)}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  // Get status badge
  const StatusBadge = ({ status, size = 'normal' }) => {
    const badges = {
      pending: { icon: '⏳', color: '#6b7280', label: 'Pending' },
      running: { icon: '⚙️', color: '#2563eb', label: 'Running' },
      completed: { icon: '✓', color: '#059669', label: 'Completed' },
      failed: { icon: '✗', color: '#dc2626', label: 'Failed' }
    };

    const badge = badges[status] || badges.pending;
    const fontSize = size === 'small' ? '12px' : '14px';

    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          color: badge.color,
          fontWeight: '500',
          fontSize: fontSize
        }}
      >
        <span style={{ fontSize: size === 'small' ? '14px' : '16px' }}>{badge.icon}</span>
        {size === 'normal' && <span>{badge.label}</span>}
      </span>
    );
  };

  const progressPercentage = (completedCount / totalCount) * 100;
  const remainingCount = totalCount - completedCount;
  const avgTime = getAvgTime();

  return (
    <div className="parser-progress-card">
      <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#1f2937' }}>
        Processing Parsers ({completedCount}/{totalCount})
      </h3>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Time Estimates */}
      <div className="time-estimates">
        {currentParser && (
          <div className="current-parser-status">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span style={{ color: '#6b7280', fontSize: '14px' }}>Currently running:</span>
              <strong style={{ color: '#1f2937', fontSize: '16px' }}>{currentParser.label}</strong>
              <span className="spinner-animated">⚙️</span>
              <span style={{ color: '#2563eb', fontSize: '14px', fontFamily: 'monospace' }}>
                {formatElapsed(elapsedTime)}
              </span>
            </div>
          </div>
        )}

        {completedCount < totalCount && (
          <div className="time-remaining">
            <span style={{ color: '#6b7280', fontSize: '14px' }}>Estimated time remaining:</span>
            <strong style={{ color: '#2563eb', fontSize: '16px', fontFamily: 'monospace', marginLeft: '8px' }}>
              {formatEstimate()}
            </strong>
          </div>
        )}

        {completedCount > 0 && (
          <div className="timing-stats">
            <span>
              <strong>Avg time per parser:</strong> {avgTime.toFixed(1)}s
            </span>
            <span>
              <strong>Completed:</strong> {completedCount}
            </span>
            <span>
              <strong>Remaining:</strong> {remainingCount}
            </span>
          </div>
        )}
      </div>

      {/* Parser List */}
      <div className="parser-list">
        {parserQueue.map((parser, idx) => (
          <div
            key={parser.mode}
            className={`parser-status parser-status-${parser.status}`}
          >
            <StatusBadge status={parser.status} />
            <span className="parser-name">{parser.label}</span>
            <div className="parser-meta">
              {parser.status === 'completed' && (
                <span className="completion-time">{parser.time.toFixed(1)}s</span>
              )}
              {parser.status === 'running' && (
                <span className="spinner-animated">⚙️</span>
              )}
              {parser.status === 'pending' && (
                <span className="queue-position">#{idx - completedCount + 1} in queue</span>
              )}
              {parser.status === 'failed' && parser.error && (
                <span className="error-hint" title={parser.error}>
                  {parser.error.substring(0, 50)}...
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ParserProgress;
