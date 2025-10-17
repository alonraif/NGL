import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useParsing } from '../context/ParsingContext';
import '../App.css';
import FileUpload from '../components/FileUpload';
import Results from '../components/Results';
import ParserProgress from '../components/ParserProgress';
import ThemeToggle from '../components/ThemeToggle';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

function UploadPage() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const {
    startParsing,
    updateParserStatus,
    addParserResult,
    completeJob,
    cancelJob,
    clearJob,
    getActiveJob
  } = useParsing();

  const [parseModes, setParseModes] = useState([]);
  const [selectedModes, setSelectedModes] = useState([]);
  const [sessionName, setSessionName] = useState('');
  const [zendeskCase, setZendeskCase] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [beginDate, setBeginDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [abortController, setAbortController] = useState(null);
  const cancelledRef = useRef(false);
  const [downloadProgress, setDownloadProgress] = useState(null);

  // Get active job from context
  const activeJob = getActiveJob();
  const loading = activeJob?.status === 'running';
  const isCompleted = activeJob?.status === 'completed';
  const results = activeJob?.results || [];
  const parserQueue = activeJob?.parserQueue || [];
  const currentParserIndex = activeJob?.currentParserIndex;
  const currentParser = currentParserIndex !== undefined && parserQueue[currentParserIndex]
    ? {
        ...parserQueue[currentParserIndex],
        startTime: parserQueue[currentParserIndex].startTime || Date.now() // Fallback for restored state
      }
    : null;
  const completedCount = activeJob?.completedCount || 0;

  // Poll for completed analyses when we have a running job after page refresh
  useEffect(() => {
    if (!activeJob || activeJob.status !== 'running') return;

    // If we have a running job but no results yet (likely after refresh), poll for updates
    const shouldPoll = activeJob.results.length === 0 && activeJob.completedCount === 0;

    if (!shouldPoll) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get('/api/analyses');
        const analyses = response.data.analyses;

        // Check if any recent analyses match our job's session
        const recentAnalyses = analyses.filter(a =>
          a.session_name === activeJob.sessionName &&
          a.status === 'completed' &&
          new Date(a.created_at).getTime() > activeJob.startTime
        );

        if (recentAnalyses.length > 0) {
          console.log('[UploadPage] Found completed analyses, job likely finished on backend');
          // Job completed on backend, mark as completed
          completeJob(activeJob.id);
        }
      } catch (error) {
        console.error('[UploadPage] Error polling for analyses:', error);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [activeJob, completeJob]);

  useEffect(() => {
    // Fetch available parse modes
    axios.get('/api/parse-modes')
      .then(response => {
        setParseModes(response.data);
      })
      .catch(err => {
        console.error('Failed to fetch parse modes:', err);
      });
  }, []);

  // Poll for download progress when downloading from URL
  useEffect(() => {
    if (!loading || !file || file.type !== 'url') {
      setDownloadProgress(null);
      return;
    }

    const pollProgress = async () => {
      try {
        const response = await axios.get('/api/download-progress');
        if (response.data.downloading) {
          setDownloadProgress(response.data);
        } else {
          setDownloadProgress(null);
        }
      } catch (error) {
        console.error('Error polling download progress:', error);
      }
    };

    // Poll every 500ms
    const interval = setInterval(pollProgress, 500);
    return () => clearInterval(interval);
  }, [loading, file]);

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setError(null);
  };

  const handleParserToggle = (modeValue) => {
    setSelectedModes(prev => {
      if (prev.includes(modeValue)) {
        return prev.filter(m => m !== modeValue);
      } else {
        return [...prev, modeValue];
      }
    });
  };

  const handleCancel = async () => {
    console.log('[UploadPage] handleCancel called, activeJob:', activeJob);
    if (activeJob && activeJob.status === 'running') {
      console.log('[UploadPage] Cancelling job:', activeJob.id);
      // Set cancellation flag
      cancelledRef.current = true;
      console.log('[UploadPage] cancelledRef set to:', cancelledRef.current);

      // Abort ongoing HTTP request
      if (abortController) {
        console.log('[UploadPage] Aborting controller');
        abortController.abort();
      } else {
        console.log('[UploadPage] No abortController found');
      }

      // Call backend cancel endpoint to kill the running process
      try {
        console.log('[UploadPage] Calling backend cancel endpoint');
        await axios.post('/api/cancel');
        console.log('[UploadPage] Backend cancel successful');
      } catch (err) {
        console.error('[UploadPage] Backend cancel failed:', err);
      }

      // Mark job as cancelled
      cancelJob(activeJob.id);
      console.log('[UploadPage] Job marked as cancelled');
    } else {
      console.log('[UploadPage] Clearing completed/cancelled job');
      // Just clear completed/cancelled jobs
      clearJob(activeJob.id);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    if (!sessionName.trim()) {
      setError('Please enter a session name');
      return;
    }

    if (selectedModes.length === 0) {
      setError('Please select at least one parser');
      return;
    }

    setError(null);

    // Reset cancellation flag
    cancelledRef.current = false;

    // Create unique job ID
    const jobId = `job_${Date.now()}`;

    // Create AbortController for this job
    const controller = new AbortController();
    setAbortController(controller);

    // Initialize parsing job in context
    const parsers = selectedModes.map(mode => {
      const parserInfo = parseModes.find(p => p.value === mode);
      return {
        mode: mode,
        label: parserInfo?.label || mode
      };
    });

    startParsing(jobId, {
      sessionName,
      zendeskCase,
      filename: file.name,
      parsers
    });

    // Process parsers sequentially
    for (let i = 0; i < selectedModes.length; i++) {
      const mode = selectedModes[i];

      // Check if job was cancelled using ref
      if (cancelledRef.current) {
        console.log('[UploadPage] Job cancelled via ref, stopping parser loop');
        break;
      }

      // Update parser status to running
      updateParserStatus(jobId, i, 'running');

      try {
        const formData = new FormData();

        // Check if this is a URL upload or file upload
        if (file.type === 'url') {
          // URL-based upload
          formData.append('file_url', file.url);
        } else {
          // Traditional file upload
          formData.append('file', file);
        }

        formData.append('parse_mode', mode);
        formData.append('session_name', sessionName);
        if (zendeskCase.trim()) {
          formData.append('zendesk_case', zendeskCase);
        }
        formData.append('timezone', timezone);

        if (beginDate) {
          formData.append('begin_date', formatDateTime(beginDate));
        }
        if (endDate) {
          formData.append('end_date', formatDateTime(endDate));
        }

        const startTime = Date.now();
        const response = await axios.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          signal: controller.signal,
          timeout: 1800000  // 30 minutes timeout for large file processing
        });
        const processingTime = (Date.now() - startTime) / 1000;

        // Update parser status to completed
        updateParserStatus(jobId, i, 'completed', { time: processingTime });

        // Add result with additional metadata
        addParserResult(jobId, {
          ...response.data,
          session_name: sessionName,
          zendesk_case: zendeskCase,
          timezone: timezone
        });

      } catch (err) {
        // Check if request was aborted
        if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
          console.log('[UploadPage] Request cancelled by user');
          updateParserStatus(jobId, i, 'cancelled', {
            time: 0,
            error: 'Cancelled by user'
          });
          break; // Stop processing remaining parsers
        }

        const processingTime = 0;
        let errorMsg = err.response?.data?.error || 'An error occurred while processing';

        // Handle rate limiting specifically
        if (err.response?.status === 429) {
          errorMsg = 'Rate limit exceeded. Please wait before uploading more files.';
        }

        // Update parser status to failed
        updateParserStatus(jobId, i, 'failed', {
          time: processingTime,
          error: errorMsg
        });

        // Add error result
        addParserResult(jobId, {
          parse_mode: mode,
          filename: file.name,
          error: errorMsg,
          success: false
        });
      }
    }

    // Check final job status using ref
    if (!cancelledRef.current) {
      // Complete the job only if it wasn't cancelled
      completeJob(jobId);
    }

    // Clean up abort controller
    setAbortController(null);
  };

  // Helper function to format date to 'YYYY-MM-DD HH:MM:SS'
  const formatDateTime = (date) => {
    if (!date) return '';
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  const timezones = [
    'US/Eastern',
    'US/Central',
    'US/Mountain',
    'US/Pacific',
    'UTC',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
  ];

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <div className="header-content">
            <img
              src="https://cdn-liveutv.pressidium.com/wp-content/uploads/2024/01/Live-and-Ulimted-Light-Background-V2.png"
              alt="LiveU Logo"
              className="header-logo"
            />
            <div className="header-text">
              <h1>NGL - Next Gen LULA</h1>
              <p>Next Generation LiveU Log Analyzer</p>
            </div>
          </div>
          <div className="header-actions">
            <div className="user-info">
              <span className="username">{user?.username}</span>
              {isAdmin() && <span className="admin-badge">Admin</span>}
              <span className="storage-info">
                {user?.storage_used_mb?.toFixed(1) || 0} / {user?.storage_quota_mb || 0} MB
              </span>
            </div>
            <ThemeToggle />
            <button onClick={() => navigate('/history')} className="btn btn-secondary">
              History
            </button>
            {isAdmin() && (
              <button onClick={() => navigate('/admin')} className="btn btn-secondary">
                Admin
              </button>
            )}
            <button onClick={() => navigate('/change-password')} className="btn btn-secondary">
              Change Password
            </button>
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </header>

        {(loading || isCompleted) && activeJob && (
          <div className="card" style={{
            marginBottom: '24px',
            background: isCompleted ? 'var(--success-light)' : 'var(--info-light)',
            border: isCompleted ? '1px solid var(--success)' : '1px solid var(--brand-primary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ marginTop: 0, color: isCompleted ? 'var(--success)' : 'var(--info)' }}>
                  {isCompleted ? '✅ Parsing Complete' : '📊 Parsing Job'}
                </h3>
                <p style={{ color: isCompleted ? 'var(--success)' : 'var(--info)', margin: '8px 0' }}>
                  <strong>Session:</strong> {activeJob.sessionName}
                  {activeJob.zendeskCase && <> | <strong>Case:</strong> {activeJob.zendeskCase}</>}
                </p>
                <p style={{ color: isCompleted ? 'var(--success)' : 'var(--info)', margin: '4px 0' }}>
                  <strong>File:</strong> {activeJob.filename}
                </p>
              </div>
              <button
                onClick={handleCancel}
                className="btn btn-secondary"
                style={{ marginLeft: '20px' }}
              >
                {isCompleted ? 'Clear' : 'Cancel'}
              </button>
            </div>
          </div>
        )}

        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="upload-section">
              <h2>Upload Log File</h2>
              <FileUpload onFileSelect={handleFileSelect} />
              {file && (
                <div className="file-info">
                  {file.type === 'url' ? (
                    <>
                      <p><strong>Source:</strong> URL</p>
                      <p><strong>File:</strong> {file.name}</p>
                      <p style={{ fontSize: '0.85rem', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>
                        {file.url}
                      </p>
                    </>
                  ) : (
                    <>
                      <p><strong>Selected file:</strong> {file.name}</p>
                      <p><strong>Size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="session-name">
                Session Name <span className="required">*</span>
              </label>
              <input
                type="text"
                id="session-name"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="e.g., Lakers game - main camera"
                required
                maxLength={255}
              />
              <small>Enter a descriptive name to identify this analysis session</small>
            </div>

            <div className="form-group">
              <label htmlFor="zendesk-case">Zendesk Case (Optional)</label>
              <input
                type="text"
                id="zendesk-case"
                value={zendeskCase}
                onChange={(e) => setZendeskCase(e.target.value)}
                placeholder="e.g., #12345"
                maxLength={100}
              />
              <small>Optional ticket reference for tracking</small>
            </div>

            <div className="form-group">
              <label htmlFor="parse-modes">Parse Modes (Select Multiple)</label>
              <div className="parser-checkboxes">
                {parseModes.map(mode => (
                  <label key={mode.value} className={`parser-checkbox${mode.recommended ? ' recommended' : ''}`}>
                    <input
                      type="checkbox"
                      checked={selectedModes.includes(mode.value)}
                      onChange={() => handleParserToggle(mode.value)}
                    />
                    <div className="checkbox-content">
                      <span className="checkbox-label">{mode.label}</span>
                      <span className="checkbox-description">{mode.description}</span>
                    </div>
                  </label>
                ))}
              </div>
              <small>
                {selectedModes.length} parser{selectedModes.length !== 1 ? 's' : ''} selected
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="timezone">Timezone</label>
              <select
                id="timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
              >
                {timezones.map(tz => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="begin-date">Begin Date (Optional)</label>
                <DatePicker
                  selected={beginDate}
                  onChange={(date) => setBeginDate(date)}
                  showTimeSelect
                  timeFormat="HH:mm"
                  timeIntervals={15}
                  dateFormat="yyyy-MM-dd HH:mm:ss"
                  placeholderText="Select start date and time"
                  isClearable
                  className="date-picker-input"
                />
                <small>Select date and time for filtering</small>
              </div>

              <div className="form-group">
                <label htmlFor="end-date">End Date (Optional)</label>
                <DatePicker
                  selected={endDate}
                  onChange={(date) => setEndDate(date)}
                  showTimeSelect
                  timeFormat="HH:mm"
                  timeIntervals={15}
                  dateFormat="yyyy-MM-dd HH:mm:ss"
                  placeholderText="Select end date and time"
                  isClearable
                  minDate={beginDate}
                  className="date-picker-input"
                />
                <small>Select date and time for filtering</small>
              </div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading || !file || selectedModes.length === 0}>
              {loading ? 'Processing...' : 'Analyze Log'}
            </button>
          </form>

          {error && (
            <div className="error" style={{ marginTop: '20px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {downloadProgress && (
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginTop: 0, color: 'var(--info)' }}>Downloading File from URL...</h3>
            <div style={{ marginBottom: '12px' }}>
              <div style={{
                width: '100%',
                height: '12px',
                background: 'var(--border-color)',
                borderRadius: '6px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${downloadProgress.percent}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, var(--brand-gradient-start) 0%, var(--brand-gradient-end) 100%)',
                  transition: 'width 0.3s ease',
                  borderRadius: '6px'
                }}></div>
              </div>
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              {downloadProgress.total ? (
                <>
                  {(downloadProgress.downloaded / (1024 * 1024)).toFixed(2)} MB / {(downloadProgress.total / (1024 * 1024)).toFixed(2)} MB
                  ({downloadProgress.percent.toFixed(1)}%)
                </>
              ) : (
                <>
                  {(downloadProgress.downloaded / (1024 * 1024)).toFixed(2)} MB downloaded...
                </>
              )}
            </div>
          </div>
        )}

        {loading && parserQueue.length > 0 && currentParser && (
          <ParserProgress
            parserQueue={parserQueue}
            currentParser={currentParser}
            completedCount={completedCount}
            totalCount={activeJob.parsers.length}
          />
        )}

        {results.length > 0 && <Results results={results} />}
      </div>
    </div>
  );
}

export default UploadPage;
