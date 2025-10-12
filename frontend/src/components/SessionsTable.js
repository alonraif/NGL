import React, { useState } from 'react';

function SessionsTable({ sessions }) {
  const [filter, setFilter] = useState('all');
  const textSecondary = 'var(--text-secondary)';
  const textPrimary = 'var(--text-primary)';
  const borderColor = 'var(--border-color)';
  const successColor = 'var(--success)';
  const successLight = 'var(--success-light)';
  const warningColor = 'var(--warning)';
  const warningLight = 'var(--warning-bg)';
  const errorColor = 'var(--error)';
  const errorLight = 'var(--error-bg)';
  const cardBackground = 'var(--bg-card)';

  if (!sessions || sessions.length === 0) {
    return <div style={{ margin: '20px 0', textAlign: 'center', color: textSecondary }}>No session data available</div>;
  }

  const filteredSessions = sessions.filter(session => {
    if (filter === 'all') return true;
    return session.type === filter;
  });

  const completeSessions = sessions.filter(s => s.type === 'complete');
  const incompleteSessions = sessions.filter(s => s.type !== 'complete');

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Sessions</h3>
          <div className="value">{sessions.length}</div>
        </div>
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #82ca9d 0%, #51a378 100%)' }}>
          <h3>Complete Sessions</h3>
          <div className="value">{completeSessions.length}</div>
        </div>
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #ff6b6b 0%, #c92a2a 100%)' }}>
          <h3>Incomplete Sessions</h3>
          <div className="value">{incompleteSessions.length}</div>
        </div>
      </div>

      <div style={{ marginTop: '30px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '15px' }}>
        <h3 style={{ color: textPrimary }}>Session Details</h3>
        <div style={{ marginLeft: 'auto' }}>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              padding: '8px 15px',
              borderRadius: '6px',
              border: `2px solid ${borderColor}`,
              fontSize: '0.9rem',
              background: cardBackground,
              color: textPrimary
            }}
          >
            <option value="all">All Sessions</option>
            <option value="complete">Complete Only</option>
            <option value="start_only">Start Only</option>
            <option value="end_only">End Only</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Session ID</th>
              <th>Start Time</th>
              <th>End Time</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {filteredSessions.map((session, idx) => (
              <React.Fragment key={idx}>
                <tr>
                  <td>{idx + 1}</td>
                  <td>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        background:
                          session.type === 'complete' ? successLight :
                          session.type === 'start_only' ? warningLight :
                          errorLight,
                        color:
                          session.type === 'complete' ? successColor :
                          session.type === 'start_only' ? warningColor :
                          errorColor,
                      }}
                    >
                      {session.type === 'complete' ? 'Complete' :
                       session.type === 'start_only' ? 'Start Only' :
                       'End Only'}
                    </span>
                  </td>
                  <td>{session.session_id || 'N/A'}</td>
                  <td style={{ fontSize: '0.9rem' }}>{session.start || '-'}</td>
                  <td style={{ fontSize: '0.9rem' }}>{session.end || '-'}</td>
                  <td style={{ fontWeight: '600' }}>{session.duration || '-'}</td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {filteredSessions.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px', color: textSecondary }}>
          <p>No sessions match the selected filter.</p>
        </div>
      )}
    </div>
  );
}

export default SessionsTable;
