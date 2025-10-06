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

  const activeJob = getActiveJob();

  useEffect(() => {
    fetchAnalyses();

    // Poll for updates if there's an active parsing job
    const pollInterval = setInterval(() => {
      if (isParsingActive()) {
        fetchAnalyses();
      }
    }, 5000); // Poll every 5 seconds

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
      const response = await axios.get(`/api/analyses/${analysisId}/download`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
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

          {selectedAnalysis.result && selectedAnalysis.analysis.status === 'completed' && (
            <Results results={[{
              parse_mode: selectedAnalysis.analysis.parse_mode,
              filename: selectedAnalysis.analysis.filename,
              output: selectedAnalysis.result.raw_output,
              parsed_data: selectedAnalysis.result.parsed_data,
              success: true
            }]} />
          )}
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
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px'
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
                  {analyses.map(analysis => (
                    <tr key={analysis.id}>
                      <td><strong>{analysis.session_name}</strong></td>
                      <td>{analysis.zendesk_case || '-'}</td>
                      <td>{analysis.filename}</td>
                      <td>{analysis.parse_mode}</td>
                      <td>
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '500',
                          background: analysis.storage_type === 's3' ? '#dbeafe' : '#e5e7eb',
                          color: analysis.storage_type === 's3' ? '#1e40af' : '#374151'
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
                  ))}
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
