import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useParsing } from '../context/ParsingContext';
import axios from 'axios';
import Results from '../components/Results';
import Header from '../components/Header';
import '../App.css';

const AnalysisHistory = () => {
  const navigate = useNavigate();
  const { getActiveJob, isParsingActive } = useParsing();
  const [activeTab, setActiveTab] = useState('my-analyses'); // 'my-analyses' or 'all-analyses'
  const [myAnalyses, setMyAnalyses] = useState([]);
  const [allAnalyses, setAllAnalyses] = useState([]);
  const [bookmarks, setBookmarks] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [viewingResult, setViewingResult] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState(new Set());

  // Filter state (replaces searchQuery)
  const [filters, setFilters] = useState({
    session_name: '',
    owner: '',
    zendesk_case: '',
    filename: '',
    analysis_id: '',
    status: '',
    parser_mode: '',
    date_from: '',
    date_to: ''
  });
  const [showFilters, setShowFilters] = useState(true); // Toggle filter panel
  const [parsers, setParsers] = useState([]); // Available parsers for dropdown

  // Pagination for "All Analyses" tab
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 50,
    total: 0,
    pages: 1
  });

  const activeJob = getActiveJob();

  // Collapse all groups by default when analyses are loaded
  useEffect(() => {
    const analyses = activeTab === 'my-analyses' ? myAnalyses : allAnalyses;
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
  }, [myAnalyses, allAnalyses, activeTab]);

  // Fetch parsers on mount
  useEffect(() => {
    fetchParsers();
  }, []);

  useEffect(() => {
    fetchData();
  }, [activeTab, pagination.page]); // Refetch when tab or page changes

  // Separate effect for polling when needed
  useEffect(() => {
    // Only poll if there's active parsing and we're on "My Analyses" tab
    if (!isParsingActive() || activeTab !== 'my-analyses') {
      return;
    }

    const pollInterval = setInterval(() => {
      fetchMyAnalyses();
    }, 5000); // Poll every 5 seconds only when parsing is active

    return () => clearInterval(pollInterval);
  }, [isParsingActive, activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'my-analyses') {
        await Promise.all([fetchMyAnalyses(), fetchBookmarks()]);
      } else {
        await Promise.all([fetchAllAnalyses(), fetchBookmarks()]);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchParsers = async () => {
    try {
      const response = await axios.get('/api/parse-modes');
      // Transform parse modes into options for dropdown
      const parserOptions = response.data.modes.map(mode => ({
        value: mode.mode,
        label: mode.label
      }));
      setParsers(parserOptions);
    } catch (error) {
      console.error('Failed to fetch parsers:', error);
    }
  };

  const buildFilterParams = () => {
    const params = {};
    Object.keys(filters).forEach(key => {
      if (filters[key]) {
        params[key] = filters[key];
      }
    });
    return params;
  };

  const fetchMyAnalyses = async () => {
    try {
      const params = buildFilterParams();
      const response = await axios.get('/api/analyses', { params });
      setMyAnalyses(response.data.analyses);
    } catch (error) {
      console.error('Failed to fetch my analyses:', error);
    }
  };

  const fetchAllAnalyses = async () => {
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        ...buildFilterParams()
      };

      console.log('[fetchAllAnalyses] Fetching with params:', params);
      const response = await axios.get('/api/analyses/all', { params });
      console.log('[fetchAllAnalyses] Received:', response.data.analyses.length, 'analyses');
      console.log('[fetchAllAnalyses] Pagination:', response.data.pagination);
      setAllAnalyses(response.data.analyses);
      setPagination(response.data.pagination);
    } catch (error) {
      console.error('Failed to fetch all analyses:', error);
      console.error('Error details:', error.response?.data);
    }
  };

  const fetchBookmarks = async () => {
    try {
      const response = await axios.get('/api/bookmarks');
      setBookmarks(new Set(response.data.bookmarks));
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const applyFilters = async () => {
    // Reset to page 1 when applying new filters
    setPagination({ ...pagination, page: 1 });
    await fetchData();
  };

  const resetFilters = () => {
    setFilters({
      session_name: '',
      owner: '',
      zendesk_case: '',
      filename: '',
      analysis_id: '',
      status: '',
      parser_mode: '',
      date_from: '',
      date_to: ''
    });
    setPagination({ ...pagination, page: 1 });
    fetchData();
  };

  const getActiveFilterCount = () => {
    return Object.values(filters).filter(v => v !== '').length;
  };

  const toggleBookmark = async (analysisId, isCurrentlyBookmarked) => {
    try {
      if (isCurrentlyBookmarked) {
        await axios.delete(`/api/bookmarks/${analysisId}`);
        setBookmarks(prev => {
          const newSet = new Set(prev);
          newSet.delete(analysisId);
          return newSet;
        });
      } else {
        await axios.post(`/api/bookmarks/${analysisId}`);
        setBookmarks(prev => new Set([...prev, analysisId]));
      }

      // Refresh data to update bookmark status
      if (activeTab === 'my-analyses') {
        await fetchMyAnalyses();
      } else {
        await fetchAllAnalyses();
      }
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
      alert('Failed to update bookmark');
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
  const groupedAnalyses = (analyses) => {
    const groups = [];
    const processedIds = new Set();

    analyses.forEach(analysis => {
      // Skip if already processed as a child
      if (processedIds.has(analysis.id)) return;

      // If it's a drill-down, check if parent is in current page
      if (analysis.is_drill_down) {
        const parentInPage = analyses.find(a => a.id === analysis.parent_analysis_id);
        if (parentInPage) {
          // Parent is in page, will be shown under parent
          processedIds.add(analysis.id);
          return;
        } else {
          // Parent not in page (pagination), show as standalone
          groups.push({
            parent: analysis,
            children: [],
            stats: {
              total: 0,
              completed: 0,
              failed: 0,
              running: 0,
              pending: 0,
              active: 0
            }
          });
          processedIds.add(analysis.id);
          return;
        }
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

  const renderAnalysisTable = (analyses, showOwner = false) => {
    if (analyses.length === 0) {
      const activeFilterCount = getActiveFilterCount();
      return (
        <p className="empty-message">
          {activeFilterCount > 0
            ? `No analyses found matching your filters`
            : activeTab === 'my-analyses'
            ? 'No analyses found. Upload a file to get started!'
            : 'No analyses available yet.'
          }
        </p>
      );
    }

    return (
      <div className="analysis-list">
        <table className="analysis-table">
          <thead>
            <tr>
              <th>Session Name</th>
              {showOwner && <th>Owner</th>}
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
            {groupedAnalyses(analyses).map(group => {
              const analysis = group.parent;
              const hasChildren = group.children.length > 0;
              const isCollapsed = collapsedGroups.has(analysis.id);
              const hasActiveDrillDowns = group.stats.active > 0;
              const isBookmarked = bookmarks.has(analysis.id);

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
                    {showOwner && (
                      <td style={{
                        color: analysis.is_own ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontStyle: analysis.is_own ? 'normal' : 'italic'
                      }}>
                        {analysis.owner_username}
                        {analysis.is_own && ' (you)'}
                      </td>
                    )}
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
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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
                        {/* Bookmark button */}
                        <button
                          onClick={() => toggleBookmark(analysis.id, isBookmarked)}
                          className="btn btn-small"
                          style={{
                            fontSize: '16px',
                            padding: '4px 8px',
                            background: isBookmarked ? 'var(--warning)' : 'transparent',
                            border: isBookmarked ? '1px solid var(--warning)' : '1px solid var(--border-color)',
                            color: isBookmarked ? '#000' : 'var(--text-primary)'
                          }}
                          title={isBookmarked ? 'Remove bookmark' : 'Bookmark this analysis'}
                        >
                          {isBookmarked ? '⭐' : '☆'}
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Child Rows (Drill-downs) */}
                  {hasChildren && !isCollapsed && group.children.map(child => {
                    const childIsBookmarked = bookmarks.has(child.id);
                    return (
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
                        {showOwner && (
                          <td style={{
                            color: child.is_own ? 'var(--text-primary)' : 'var(--text-secondary)',
                            fontStyle: child.is_own ? 'normal' : 'italic'
                          }}>
                            {child.owner_username}
                            {child.is_own && ' (you)'}
                          </td>
                        )}
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
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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
                            {/* Bookmark button for drill-downs */}
                            <button
                              onClick={() => toggleBookmark(child.id, childIsBookmarked)}
                              className="btn btn-small"
                              style={{
                                fontSize: '16px',
                                padding: '4px 8px',
                                background: childIsBookmarked ? 'var(--warning)' : 'transparent',
                                border: childIsBookmarked ? '1px solid var(--warning)' : '1px solid var(--border-color)',
                                color: childIsBookmarked ? '#000' : 'var(--text-primary)'
                              }}
                              title={childIsBookmarked ? 'Remove bookmark' : 'Bookmark this analysis'}
                            >
                              {childIsBookmarked ? '⭐' : '☆'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFilterPanel = () => {
    const activeCount = getActiveFilterCount();

    return (
      <div className={`filter-panel ${showFilters ? '' : 'collapsed'}`}>
        <div className="filter-panel-header">
          <div className="filter-panel-title">
            🔍 Filters
            {activeCount > 0 && <span className="filter-badge">{activeCount}</span>}
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            {activeCount > 0 && (
              <button onClick={resetFilters} className="btn btn-secondary btn-small">
                Reset All
              </button>
            )}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="btn btn-secondary btn-small"
            >
              {showFilters ? 'Collapse ▲' : 'Expand ▼'}
            </button>
          </div>
        </div>

        {showFilters && (
          <>
            <div className="filter-grid">
              {/* Row 1 */}
              <div className="filter-field">
                <label>Session Name</label>
                <input
                  type="text"
                  className={`filter-input ${filters.session_name ? 'has-value' : ''}`}
                  value={filters.session_name}
                  onChange={(e) => handleFilterChange('session_name', e.target.value)}
                  placeholder="Enter session name..."
                />
              </div>
              {activeTab === 'all-analyses' && (
                <div className="filter-field">
                  <label>Owner/Username</label>
                  <input
                    type="text"
                    className={`filter-input ${filters.owner ? 'has-value' : ''}`}
                    value={filters.owner}
                    onChange={(e) => handleFilterChange('owner', e.target.value)}
                    placeholder="Enter username..."
                  />
                </div>
              )}
              <div className="filter-field">
                <label>Zendesk Case</label>
                <input
                  type="text"
                  className={`filter-input ${filters.zendesk_case ? 'has-value' : ''}`}
                  value={filters.zendesk_case}
                  onChange={(e) => handleFilterChange('zendesk_case', e.target.value)}
                  placeholder="Enter case number..."
                />
              </div>
              <div className="filter-field">
                <label>Filename</label>
                <input
                  type="text"
                  className={`filter-input ${filters.filename ? 'has-value' : ''}`}
                  value={filters.filename}
                  onChange={(e) => handleFilterChange('filename', e.target.value)}
                  placeholder="Enter filename..."
                />
              </div>

              {/* Row 2 */}
              <div className="filter-field">
                <label>Analysis ID</label>
                <input
                  type="text"
                  className={`filter-input ${filters.analysis_id ? 'has-value' : ''}`}
                  value={filters.analysis_id}
                  onChange={(e) => handleFilterChange('analysis_id', e.target.value)}
                  placeholder="Enter ID..."
                />
              </div>
              <div className="filter-field">
                <label>Status</label>
                <select
                  className={`filter-select ${filters.status ? 'has-value' : ''}`}
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                >
                  <option value="">All</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="running">Running</option>
                  <option value="pending">Pending</option>
                </select>
              </div>

              {/* Row 3 */}
              <div className="filter-field">
                <label>Parser/Mode</label>
                <select
                  className={`filter-select ${filters.parser_mode ? 'has-value' : ''}`}
                  value={filters.parser_mode}
                  onChange={(e) => handleFilterChange('parser_mode', e.target.value)}
                >
                  <option value="">All</option>
                  {parsers.map(parser => (
                    <option key={parser.value} value={parser.value}>
                      {parser.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="filter-field">
                <label>From Date</label>
                <input
                  type="date"
                  className={`filter-input ${filters.date_from ? 'has-value' : ''}`}
                  value={filters.date_from}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                />
              </div>
              <div className="filter-field">
                <label>To Date</label>
                <input
                  type="date"
                  className={`filter-input ${filters.date_to ? 'has-value' : ''}`}
                  value={filters.date_to}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                />
              </div>
            </div>

            <div className="filter-actions">
              <button onClick={applyFilters} className="btn btn-primary">
                Apply Filters
              </button>
              {activeCount > 0 && (
                <button onClick={resetFilters} className="btn btn-secondary">
                  Reset All
                </button>
              )}
            </div>
          </>
        )}
      </div>
    );
  };

  const renderPagination = () => {
    if (pagination.pages <= 1) return null;

    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '12px',
        marginTop: '24px',
        padding: '16px'
      }}>
        <button
          onClick={() => setPagination({ ...pagination, page: pagination.page - 1 })}
          disabled={pagination.page === 1}
          className="btn btn-secondary btn-small"
        >
          Previous
        </button>
        <span style={{ color: 'var(--text-secondary)' }}>
          Page {pagination.page} of {pagination.pages} ({pagination.total} total)
        </span>
        <button
          onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })}
          disabled={pagination.page === pagination.pages}
          className="btn btn-secondary btn-small"
        >
          Next
        </button>
      </div>
    );
  };

  if (loading && !viewingResult) {
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
          <Header
            currentPage="results"
            showStorageInfo={false}
            showUserInfo={false}
            customActions={
              <>
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
              </>
            }
          />

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
        <Header currentPage="history" showStorageInfo={false} />

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
          {/* Tab Navigation */}
          <div className="tab-navigation">
            <button
              onClick={() => setActiveTab('my-analyses')}
              className={`tab-button ${activeTab === 'my-analyses' ? 'active' : ''}`}
            >
              My Analyses
              {bookmarks.size > 0 && <span className="tab-badge">{bookmarks.size}</span>}
            </button>
            <button
              onClick={() => setActiveTab('all-analyses')}
              className={`tab-button ${activeTab === 'all-analyses' ? 'active' : ''}`}
            >
              All Analyses
            </button>
          </div>

          {/* Filter Panel */}
          {renderFilterPanel()}

          {/* Tab Content */}
          {activeTab === 'my-analyses' ? (
            <>
              <div style={{ marginBottom: '24px' }}>
                <h2>Your Analyses & Bookmarks</h2>
                <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
                  View your own analyses and analyses you've bookmarked from other users
                </p>
              </div>
              {renderAnalysisTable(myAnalyses, true)}
            </>
          ) : (
            <>
              <div style={{ marginBottom: '24px' }}>
                <h2>All Analyses</h2>
                <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
                  Browse analyses from all users. Bookmark analyses to add them to your view.
                </p>
              </div>
              {renderAnalysisTable(allAnalyses, true)}
              {renderPagination()}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisHistory;
