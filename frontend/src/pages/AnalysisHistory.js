import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useParsing } from '../context/ParsingContext';
import axios from 'axios';
import Results from '../components/Results';
import ThemeToggle from '../components/ThemeToggle';
import '../App.css';

const AnalysisHistory = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const { getActiveJob, isParsingActive } = useParsing();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [viewingResult, setViewingResult] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState(new Set());

  const activeJob = getActiveJob();

  // Collapse all groups by default when analyses are loaded
  useEffect(() => {
    if (analyses.length > 0) {
      const groupsWithChildren = new Set();
      analyses.forEach(analysis => {
        // If this analysis has children, add it to collapsed groups
        if (!analysis.is_drill_down && analyses.some(a => a.parent_analysis_id === analysis.id)) {
          groupsWithChildren.add(analysis.id);
        }
      });
      setCollapsedGroups(groupsWithChildren);
    }
  }, [analyses]);

  useEffect(() => {
    fetchAnalyses();
  }, []); // Fetch only on mount

  // Separate effect for polling when needed
  useEffect(() => {
    // Only poll if there's active parsing
    if (!isParsingActive()) {
      return;
    }

    const pollInterval = setInterval(() => {
      fetchAnalyses();
    }, 5000); // Poll every 5 seconds only when parsing is active

    return () => clearInterval(pollInterval);
  }, [isParsingActive]);

  const fetchAnalyses = async () => {
    try {
      const response = await axios.get('/api/analyses');
      setAnalyses(response.data.analyses);
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchAnalyses();
      return;
    }

    try {
      setLoading(true);
      const response = await axios.get('/api/analyses/search', {
        params: { q: searchQuery }
      });
      setAnalyses(response.data.analyses);
    } catch (error) {
      console.error('Failed to search analyses:', error);
      alert('Failed to search analyses');
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    fetchAnalyses();
  };

  const viewAnalysis = async (analysisId) => {
    try {
      const response = await axios.get(`/api/analyses/${analysisId}`);
      setSelectedAnalysis(response.data);
      setViewingResult(true);
    } catch (error) {
      console.error('Failed to fetch analysis:', error);
      alert('Failed to load analysis results');
    }
  };

  const downloadLogFile = async (analysisId, filename) => {
    try {
      const response = await axios.get(`/api/analyses/${analysisId}/download`);

      console.log('[Download] Response type:', typeof response.data);
      console.log('[Download] Has download_url:', !!response.data?.download_url);
      console.log('[Download] Response data:', response.data);

      // Check if response contains S3 download URL (JSON response)
      if (response.data && response.data.download_url) {
        // S3 file - open presigned URL directly (avoids CORS)
        console.log('[Download] Opening S3 URL:', response.data.download_url.substring(0, 100) + '...');
        window.location.href = response.data.download_url;
      } else {
        // Local file - handle as blob
        console.log('[Download] Downloading as blob, size:', response.data.size);
        const blobResponse = await axios.get(`/api/analyses/${analysisId}/download`, {
          responseType: 'blob'
        });

        console.log('[Download] Blob size:', blobResponse.data.size);
        console.log('[Download] Blob type:', blobResponse.data.type);

        const url = window.URL.createObjectURL(new Blob([blobResponse.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to download file:', error);
      alert('Failed to download log file');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getStatusBadge = (status) => {
    const colors = {
      completed: 'success',
      failed: 'error',
      running: 'warning',
      pending: 'info'
    };
    return (
      <span className={`status-badge status-${colors[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const toggleGroup = (analysisId) => {
    const newCollapsed = new Set(collapsedGroups);
    if (newCollapsed.has(analysisId)) {
      newCollapsed.delete(analysisId);
    } else {
      newCollapsed.add(analysisId);
    }
    setCollapsedGroups(newCollapsed);
  };

  // Group analyses: parent sessions with their drill-downs
  const groupedAnalyses = () => {
    const groups = [];
    const processedIds = new Set();

    analyses.forEach(analysis => {
      // Skip if already processed as a child
      if (processedIds.has(analysis.id)) return;

      // If it's a drill-down, skip (will be shown under parent)
      if (analysis.is_drill_down) {
        processedIds.add(analysis.id);
        return;
      }

      const children = analyses.filter(a => a.parent_analysis_id === analysis.id);

      // Calculate progress stats for drill-downs
      const completedChildren = children.filter(c => c.status === 'completed').length;
      const failedChildren = children.filter(c => c.status === 'failed').length;
      const runningChildren = children.filter(c => c.status === 'running').length;
      const pendingChildren = children.filter(c => c.status === 'pending').length;
      const activeChildren = runningChildren + pendingChildren;

      // Add parent analysis
      groups.push({
        parent: analysis,
        children: children,
        stats: {
          total: children.length,
          completed: completedChildren,
          failed: failedChildren,
          running: runningChildren,
          pending: pendingChildren,
          active: activeChildren
        }
      });

      // Mark as processed
      processedIds.add(analysis.id);
      children.forEach(child => {
        processedIds.add(child.id);
      });
    });

    return groups;
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading analyses...</p>
      </div>
    );
  }

  if (viewingResult && selectedAnalysis) {
    return (
      <div className="App">
        <div className="container">
          <header className="header">
            <div className="header-content">
              <h1>Analysis Results</h1>
            </div>
            <div className="header-actions">
              <ThemeToggle />
              <button
                onClick={() => downloadLogFile(selectedAnalysis.analysis.id, selectedAnalysis.analysis.filename)}
                className="btn btn-primary"
              >
                📥 Download Log File
              </button>
              <button onClick={() => setViewingResult(false)} className="btn btn-secondary">
                ← Back to History
              </button>
              <button onClick={() => navigate('/')} className="btn btn-secondary">
                Home
              </button>
            </div>
          </header>

          <div className="card">
            <h2>Analysis Details</h2>
            <div className="analysis-details">
              <p><strong>Session Name:</strong> {selectedAnalysis.analysis.session_name}</p>
              {selectedAnalysis.analysis.zendesk_case && (
                <p><strong>Zendesk Case:</strong> {selectedAnalysis.analysis.zendesk_case}</p>
              )}
              <p><strong>File:</strong> {selectedAnalysis.analysis.filename}</p>
              <p><strong>Parser:</strong> {selectedAnalysis.analysis.parse_mode}</p>
              <p><strong>Status:</strong> {getStatusBadge(selectedAnalysis.analysis.status)}</p>
              <p><strong>Created:</strong> {formatDate(selectedAnalysis.analysis.created_at)}</p>
              {selectedAnalysis.analysis.completed_at && (
                <p><strong>Completed:</strong> {formatDate(selectedAnalysis.analysis.completed_at)}</p>
              )}
              {selectedAnalysis.analysis.processing_time_seconds && (
                <p><strong>Processing Time:</strong> {selectedAnalysis.analysis.processing_time_seconds}s</p>
              )}
            </div>

            {selectedAnalysis.analysis.error_message && (
              <div className="error" style={{ marginTop: '20px' }}>
                <strong>Error:</strong> {selectedAnalysis.analysis.error_message}
              </div>
            )}
          </div>

          {selectedAnalysis.result && selectedAnalysis.analysis.status === 'completed' && (() => {
            const resultData = {
              parse_mode: selectedAnalysis.analysis.parse_mode,
              filename: selectedAnalysis.analysis.filename,
              output: selectedAnalysis.result.raw_output,
              parsed_data: selectedAnalysis.result.parsed_data,
              success: true,
              analysis_id: selectedAnalysis.analysis.id,
              log_file_id: selectedAnalysis.analysis.log_file_id,
              session_name: selectedAnalysis.analysis.session_name,
              zendesk_case: selectedAnalysis.analysis.zendesk_case,
              timezone: selectedAnalysis.analysis.timezone
            };
            return <Results results={[resultData]} />;
          })()}
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <div className="header-content">
            <h1>Analysis History</h1>
          </div>
          <div className="header-actions">
            <div className="user-info">
              <span className="username">{user?.username}</span>
              {isAdmin() && <span className="admin-badge">Admin</span>}
            </div>
            <ThemeToggle />
            <button onClick={() => navigate('/')} className="btn btn-secondary">
              Upload
            </button>
            {isAdmin() && (
              <button onClick={() => navigate('/admin')} className="btn btn-secondary">
                Admin
              </button>
            )}
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </header>

        {isParsingActive() && activeJob && (
          <div className="parsing-banner">
            <div className="parsing-banner-content">
              <div className="parsing-banner-header">
                <span className="parsing-indicator"></span>
                <h3>Parsing in Progress</h3>
              </div>
              <p>
                <strong>{activeJob.sessionName}</strong>
                {activeJob.zendeskCase && <> - Case: {activeJob.zendeskCase}</>}
              </p>
              <p style={{ margin: '4px 0', fontSize: '13px', opacity: 0.9 }}>
                📁 {activeJob.filename}
              </p>
              <p className="parsing-banner-status">
                ⚙️ {activeJob.completedCount} of {activeJob.parsers.length} parsers completed
                {activeJob.parserQueue && activeJob.currentParserIndex !== undefined && activeJob.parserQueue[activeJob.currentParserIndex] && (
                  <> - Currently: <strong>{activeJob.parserQueue[activeJob.currentParserIndex].label}</strong></>
                )}
              </p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="btn btn-secondary"
              style={{ marginLeft: 'auto' }}
            >
              View Details
            </button>
          </div>
        )}

        <div className="card">
          <div style={{ marginBottom: '24px' }}>
            <h2>Your Analyses</h2>
            <form onSubmit={handleSearch} style={{ marginTop: '16px' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by session name or Zendesk case..."
                  style={{
                    flex: 1,
                    padding: '10px 12px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    fontSize: '14px',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)'
                  }}
                />
                <button type="submit" className="btn btn-primary" style={{ width: 'auto' }}>
                  Search
                </button>
                {searchQuery && (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="btn btn-secondary"
                    style={{ width: 'auto' }}
                  >
                    Clear
                  </button>
                )}
              </div>
            </form>
          </div>

          {analyses.length === 0 ? (
            <p className="empty-message">
              {searchQuery
                ? `No analyses found matching "${searchQuery}"`
                : 'No analyses found. Upload a file to get started!'
              }
            </p>
          ) : (
            <div className="analysis-list">
              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>Session Name</th>
                    <th>Zendesk Case</th>
                    <th>File</th>
                    <th>Parser</th>
                    <th>Storage</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Time</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groupedAnalyses().map(group => {
                    const analysis = group.parent;
                    const hasChildren = group.children.length > 0;
                    const isCollapsed = collapsedGroups.has(analysis.id);
                    const hasActiveDrillDowns = group.stats.active > 0;

                    return (
                      <React.Fragment key={analysis.id}>
                        {/* Parent Row */}
                        <tr style={{
                          background: hasChildren ? 'var(--bg-secondary)' : undefined,
                          fontWeight: hasChildren ? '500' : 'normal'
                        }}>
                          <td>
                            {hasChildren && (
                              <button
                                onClick={() => toggleGroup(analysis.id)}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: '1rem',
                                  color: 'var(--text-primary)',
                                  padding: '0 8px 0 0',
                                  transition: 'transform 0.2s',
                                  transform: isCollapsed ? 'rotate(0deg)' : 'rotate(90deg)'
                                }}
                              >
                                ▶
                              </button>
                            )}
                            <strong>{analysis.session_name}</strong>
                            {hasChildren && (
                              <>
                                {hasActiveDrillDowns ? (
                                  <span style={{
                                    fontSize: '0.75rem',
                                    color: 'var(--info)',
                                    marginLeft: '8px',
                                    padding: '2px 6px',
                                    background: 'var(--info-light)',
                                    borderRadius: '4px',
                                    fontWeight: '600',
                                    animation: 'pulse 2s infinite'
                                  }} title={`Processing drill-downs: ${group.stats.running} running, ${group.stats.pending} queued`}>
                                    ⚙️ {group.stats.completed}/{group.stats.total}
                                  </span>
                                ) : (
                                  <span style={{
                                    fontSize: '0.75rem',
                                    color: 'var(--success)',
                                    marginLeft: '8px',
                                    padding: '2px 6px',
                                    background: 'var(--success-light)',
                                    borderRadius: '4px',
                                    fontWeight: '600'
                                  }} title={`Has drill-down analyses: ${group.stats.completed} completed${group.stats.failed > 0 ? `, ${group.stats.failed} failed` : ''}`}>
                                    📊 {group.stats.completed}{group.stats.failed > 0 ? `/${group.stats.total}` : ''}
                                  </span>
                                )}
                              </>
                            )}
                          </td>
                          <td>{analysis.zendesk_case || '-'}</td>
                          <td>{analysis.filename}</td>
                          <td>{analysis.parse_mode}</td>
                          <td>
                            <span style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: '500',
                              background: analysis.storage_type === 's3' ? 'var(--info-bg)' : 'var(--bg-hover)',
                              color: analysis.storage_type === 's3' ? 'var(--info)' : 'var(--text-primary)'
                            }}>
                              {analysis.storage_type === 's3' ? '☁️ S3' : '🗄️ Local'}
                            </span>
                          </td>
                          <td>{getStatusBadge(analysis.status)}</td>
                          <td>{formatDate(analysis.created_at)}</td>
                          <td>
                            {analysis.processing_time_seconds
                              ? `${analysis.processing_time_seconds}s`
                              : '-'}
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                onClick={() => viewAnalysis(analysis.id)}
                                className="btn btn-small"
                              >
                                View
                              </button>
                              <button
                                onClick={() => downloadLogFile(analysis.id, analysis.filename)}
                                className="btn btn-small btn-secondary"
                                title="Download log file"
                              >
                                📥
                              </button>
                            </div>
                          </td>
                        </tr>

                        {/* Child Rows (Drill-downs) */}
                        {hasChildren && !isCollapsed && group.children.map(child => (
                          <tr key={child.id} style={{
                            background: 'var(--bg-hover)',
                            borderLeft: '3px solid var(--primary)'
                          }}>
                            <td style={{ paddingLeft: '40px' }}>
                              <span style={{
                                fontSize: '0.85rem',
                                color: 'var(--primary)',
                                marginRight: '6px'
                              }} title="Drill-down analysis">
                                ↳ 🔍
                              </span>
                              {child.session_name}
                            </td>
                            <td>{child.zendesk_case || '-'}</td>
                            <td>{child.filename}</td>
                            <td>{child.parse_mode}</td>
                            <td>
                              <span style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                fontSize: '12px',
                                fontWeight: '500',
                                background: child.storage_type === 's3' ? 'var(--info-bg)' : 'var(--bg-hover)',
                                color: child.storage_type === 's3' ? 'var(--info)' : 'var(--text-primary)'
                              }}>
                                {child.storage_type === 's3' ? '☁️ S3' : '🗄️ Local'}
                              </span>
                            </td>
                            <td>{getStatusBadge(child.status)}</td>
                            <td>{formatDate(child.created_at)}</td>
                            <td>
                              {child.processing_time_seconds
                                ? `${child.processing_time_seconds}s`
                                : '-'}
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                  onClick={() => viewAnalysis(child.id)}
                                  className="btn btn-small"
                                >
                                  View
                                </button>
                                <button
                                  onClick={() => downloadLogFile(child.id, child.filename)}
                                  className="btn btn-small btn-secondary"
                                  title="Download log file"
                                >
                                  📥
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisHistory;
