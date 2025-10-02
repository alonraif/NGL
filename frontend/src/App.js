import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import FileUpload from './components/FileUpload';
import Results from './components/Results';
import ParserProgress from './components/ParserProgress';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

function App() {
  const [parseModes, setParseModes] = useState([]);
  const [selectedModes, setSelectedModes] = useState([]);
  const [timezone, setTimezone] = useState('US/Eastern');
  const [beginDate, setBeginDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [parserQueue, setParserQueue] = useState([]);
  const [currentParser, setCurrentParser] = useState(null);
  const [completedCount, setCompletedCount] = useState(0);

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

  const handleParserToggle = (modeValue) => {
    setSelectedModes(prev => {
      if (prev.includes(modeValue)) {
        return prev.filter(m => m !== modeValue);
      } else {
        return [...prev, modeValue];
      }
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    if (selectedModes.length === 0) {
      setError('Please select at least one parser');
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setCompletedCount(0);

    // Initialize parser queue
    const queue = selectedModes.map(mode => {
      const parserInfo = parseModes.find(p => p.value === mode);
      return {
        mode: mode,
        label: parserInfo?.label || mode,
        status: 'pending',
        time: 0,
        error: null
      };
    });
    setParserQueue(queue);

    // Process parsers sequentially
    const allResults = [];
    for (let i = 0; i < selectedModes.length; i++) {
      const mode = selectedModes[i];
      const parserInfo = parseModes.find(p => p.value === mode);

      // Update current parser
      setCurrentParser({
        mode: mode,
        label: parserInfo?.label || mode,
        startTime: Date.now()
      });

      // Update queue status to running
      setParserQueue(prev => prev.map((p, idx) =>
        idx === i ? { ...p, status: 'running' } : p
      ));

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('parse_mode', mode);
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
        });
        const processingTime = (Date.now() - startTime) / 1000;

        // Update queue status to completed
        setParserQueue(prev => prev.map((p, idx) =>
          idx === i ? { ...p, status: 'completed', time: processingTime } : p
        ));

        allResults.push(response.data);
        setResults(allResults);
        setCompletedCount(i + 1);

      } catch (err) {
        const processingTime = (Date.now() - Date.now()) / 1000;
        const errorMsg = err.response?.data?.error || 'An error occurred while processing';

        // Update queue status to failed
        setParserQueue(prev => prev.map((p, idx) =>
          idx === i ? { ...p, status: 'failed', time: processingTime, error: errorMsg } : p
        ));

        // Add error result
        allResults.push({
          parse_mode: mode,
          filename: file.name,
          error: errorMsg,
          success: false
        });
        setResults(allResults);
        setCompletedCount(i + 1);
      }
    }

    setCurrentParser(null);
    setLoading(false);
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
              <label htmlFor="parse-modes">Parse Modes (Select Multiple)</label>
              <div className="parser-checkboxes">
                {parseModes.map(mode => (
                  <label key={mode.value} className="parser-checkbox">
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

        {loading && parserQueue.length > 0 && (
          <ParserProgress
            parserQueue={parserQueue}
            currentParser={currentParser}
            completedCount={completedCount}
            totalCount={selectedModes.length}
          />
        )}

        {results.length > 0 && <Results results={results} />}
      </div>
    </div>
  );
}

export default App;
