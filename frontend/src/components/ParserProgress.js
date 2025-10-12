import React, { useState, useEffect } from 'react';

const ParserProgress = ({ parserQueue, currentParser, completedCount, totalCount }) => {
  // Calculate average time per parser
  const getAvgTime = () => {
    if (completedCount === 0) return 0;
    const completedParsers = parserQueue.filter(p => p.status === 'completed');
    const totalTime = completedParsers.reduce((sum, p) => sum + p.time, 0);
    return totalTime / completedCount;
  };

  // Get status badge
  const StatusBadge = ({ status, size = 'normal' }) => {
    const badges = {
      pending: { icon: '⏳', color: 'var(--text-secondary)', label: 'Pending' },
      running: { icon: '⚙️', color: 'var(--brand-primary)', label: 'Running' },
      completed: { icon: '✓', color: 'var(--success)', label: 'Completed' },
      failed: { icon: '✗', color: 'var(--error)', label: 'Failed' }
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
      <h3 style={{ marginTop: 0, marginBottom: '20px', color: 'var(--text-primary)' }}>
        Processing Parsers ({completedCount}/{totalCount})
      </h3>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Processing status */}
      <div className="time-estimates">
        {currentParser && (
          <div className="current-parser-status">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Currently running:</span>
              <strong style={{ color: 'var(--text-primary)', fontSize: '16px' }}>{currentParser.label}</strong>
              <span className="spinner-animated">⚙️</span>
            </div>
            <span style={{ color: 'var(--brand-primary)', fontSize: '13px' }}>Processing in progress…</span>
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
