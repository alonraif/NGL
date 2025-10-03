import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import Results from '../components/Results';
import '../App.css';

const AnalysisHistory = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [viewingResult, setViewingResult] = useState(false);

  useEffect(() => {
    fetchAnalyses();
  }, []);

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

        <div className="card">
          <h2>Your Analyses</h2>
          {analyses.length === 0 ? (
            <p className="empty-message">No analyses found. Upload a file to get started!</p>
          ) : (
            <div className="analysis-list">
              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Parser</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Time</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.map(analysis => (
                    <tr key={analysis.id}>
                      <td>{analysis.filename}</td>
                      <td>{analysis.parse_mode}</td>
                      <td>{getStatusBadge(analysis.status)}</td>
                      <td>{formatDate(analysis.created_at)}</td>
                      <td>
                        {analysis.processing_time_seconds
                          ? `${analysis.processing_time_seconds}s`
                          : '-'}
                      </td>
                      <td>
                        <button
                          onClick={() => viewAnalysis(analysis.id)}
                          className="btn btn-small"
                        >
                          View
                        </button>
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
