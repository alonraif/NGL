import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import FileUpload from './components/FileUpload';
import Results from './components/Results';

function App() {
  const [parseModes, setParseModes] = useState([]);
  const [selectedMode, setSelectedMode] = useState('known');
  const [timezone, setTimezone] = useState('US/Eastern');
  const [beginDate, setBeginDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

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

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('parse_mode', selectedMode);
    formData.append('timezone', timezone);
    if (beginDate) formData.append('begin_date', beginDate);
    if (endDate) formData.append('end_date', endDate);

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while processing the file');
    } finally {
      setLoading(false);
    }
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
          <h1>🎥 NGL - Next Gen LULA</h1>
          <p>Next Generation LiveU Log Analyzer with beautiful visualizations</p>
        </header>

        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="upload-section">
              <h2>Upload Log File</h2>
              <FileUpload onFileSelect={handleFileSelect} />
              {file && (
                <div className="file-info">
                  <p><strong>Selected file:</strong> {file.name}</p>
                  <p><strong>Size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="parse-mode">Parse Mode</label>
              <select
                id="parse-mode"
                value={selectedMode}
                onChange={(e) => setSelectedMode(e.target.value)}
              >
                {parseModes.map(mode => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
              <small>
                {parseModes.find(m => m.value === selectedMode)?.description}
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
                <input
                  type="text"
                  id="begin-date"
                  placeholder="e.g., 2024-01-01 12:00:00"
                  value={beginDate}
                  onChange={(e) => setBeginDate(e.target.value)}
                />
                <small>Format: YYYY-MM-DD HH:MM:SS</small>
              </div>

              <div className="form-group">
                <label htmlFor="end-date">End Date (Optional)</label>
                <input
                  type="text"
                  id="end-date"
                  placeholder="e.g., 2024-01-01 18:00:00"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
                <small>Format: YYYY-MM-DD HH:MM:SS</small>
              </div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading || !file}>
              {loading ? 'Processing...' : 'Analyze Log'}
            </button>
          </form>

          {error && (
            <div className="error" style={{ marginTop: '20px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {loading && (
          <div className="card">
            <div className="loading">
              <div className="spinner"></div>
              <p>Processing your log file... This may take a few minutes.</p>
            </div>
          </div>
        )}

        {results && <Results data={results} />}
      </div>
    </div>
  );
}

export default App;
