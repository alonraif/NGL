import React, { useState, useRef } from 'react';
import ModemStats from './ModemStats';
import BandwidthChart from './BandwidthChart';
import ModemBandwidthChart from './ModemBandwidthChart';
import SessionsTable from './SessionsTable';
import MemoryChart from './MemoryChart';
import ModemGradingChart from './ModemGradingChart';
import CpuChart from './CpuChart';
import RawOutput from './RawOutput';
import CopyChartButton from './CopyChartButton';

const MODES_WITH_VISUALIZATION = new Set([
  'md',
  'md-bw',
  'md-db-bw',
  'bw',
  'sessions',
  'memory',
  'grading',
  'cpu'
]);

const sanitizeForFile = (value) => {
  if (!value) return 'visualization';
  return value.toString().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'visualization';
};

function Results({ results }) {
  const [activeParser, setActiveParser] = useState(0); // Index of selected parser
  // Initialize activeTab based on whether first parser has visualization
  const initialTab = results && results.length > 0 && MODES_WITH_VISUALIZATION.has(results[0].parse_mode)
    ? 'visualization'
    : 'raw';
  const [activeTab, setActiveTab] = useState(initialTab);
  const visualizationRef = useRef(null);

  if (!results || results.length === 0) {
    return null;
  }

  const currentResult = results[activeParser];
  const hasVisualization = MODES_WITH_VISUALIZATION.has(currentResult.parse_mode);

  const getParserLabel = (parseMode) => {
    const labels = {
      'known': 'Known Errors',
      'error': 'All Errors',
      'v': 'Verbose',
      'all': 'All Lines',
      'bw': 'Bandwidth',
      'md-bw': 'Modem Bandwidth',
      'md-db-bw': 'Data Bridge BW',
      'md': 'Modem Stats',
      'sessions': 'Sessions',
      'id': 'Device IDs',
      'memory': 'Memory Usage',
      'grading': 'Modem Grading',
      'cpu': 'CPU Usage'
    };
    return labels[parseMode] || parseMode;
  };

  const renderVisualization = () => {
    if (currentResult.parse_mode === 'md' && currentResult.parsed_data) {
      return <ModemStats modems={currentResult.parsed_data} />;
    } else if (currentResult.parse_mode === 'md-bw' && currentResult.parsed_data) {
      return <ModemBandwidthChart data={currentResult.parsed_data} />;
    } else if (['bw', 'md-db-bw'].includes(currentResult.parse_mode) && currentResult.parsed_data) {
      return <BandwidthChart data={currentResult.parsed_data} mode={currentResult.parse_mode} />;
    } else if (currentResult.parse_mode === 'sessions' && currentResult.parsed_data) {
      return <SessionsTable sessions={currentResult.parsed_data} />;
    } else if (currentResult.parse_mode === 'memory' && currentResult.parsed_data) {
      return <MemoryChart data={currentResult.parsed_data} />;
    } else if (currentResult.parse_mode === 'grading' && currentResult.parsed_data) {
      return <ModemGradingChart data={currentResult.parsed_data} />;
    } else if (currentResult.parse_mode === 'cpu' && currentResult.parsed_data) {
      return <CpuChart data={currentResult.parsed_data} />;
    } else {
      return (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          <p>No visualization available for this parse mode.</p>
          <p>Check the "Raw Output" tab to see the results.</p>
        </div>
      );
    }
  };

  const visualizationContent = activeTab === 'visualization' ? renderVisualization() : null;

  const parserPart = sanitizeForFile(currentResult.parse_mode);
  const filePart = currentResult.filename ? sanitizeForFile(currentResult.filename) : null;
  const copyAllFileName = filePart
    ? `${filePart}-${parserPart}-visualization.png`
    : `${parserPart}-visualization.png`;

  const showCopyAllButton =
    activeTab === 'visualization' &&
    MODES_WITH_VISUALIZATION.has(currentResult.parse_mode) &&
    !!currentResult.parsed_data;

  return (
    <div className="results-section">
      <div className="card">
        <h2>Analysis Results</h2>

        {currentResult.filename && (
          <div className="file-info">
            <p><strong>File:</strong> {currentResult.filename}</p>
            <p><strong>Total Parsers:</strong> {results.length}</p>
          </div>
        )}

        {/* Parser Selection Tabs */}
        {results.length > 1 && (
          <div className="parser-tabs-outer">
            {results.map((result, index) => (
              <button
                key={index}
                className={`parser-tab ${activeParser === index ? 'active' : ''}`}
                onClick={() => {
                  setActiveParser(index);
                  // Auto-select appropriate tab based on parser type
                  const newParserHasViz = MODES_WITH_VISUALIZATION.has(result.parse_mode);
                  setActiveTab(newParserHasViz ? 'visualization' : 'raw');
                }}
              >
                <span className="parser-tab-label">{getParserLabel(result.parse_mode)}</span>
                {result.processing_time && (
                  <span className="parser-tab-time">{result.processing_time}s</span>
                )}
                <span className={`parser-tab-status ${result.error ? 'error' : 'success'}`}>
                  {result.error ? '✗' : '✓'}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Content Tabs */}
        <div className="results-tabs">
          {hasVisualization && (
            <button
              className={`tab ${activeTab === 'visualization' ? 'active' : ''}`}
              onClick={() => setActiveTab('visualization')}
            >
              Visualization
            </button>
          )}
          <button
            className={`tab ${activeTab === 'raw' ? 'active' : ''}`}
            onClick={() => setActiveTab('raw')}
          >
            Raw Output
          </button>
          {currentResult.error && (
            <button
              className={`tab ${activeTab === 'errors' ? 'active' : ''}`}
              onClick={() => setActiveTab('errors')}
            >
              Errors
            </button>
          )}
        </div>

        <div className="tab-content">
          {activeTab === 'visualization' && (
            <>
              {showCopyAllButton && (
                <div className="visualization-toolbar">
                  <CopyChartButton
                    targetRef={visualizationRef}
                    idleLabel="Copy All"
                    fileName={copyAllFileName}
                  />
                </div>
              )}
              <div ref={visualizationRef} className="visualization-content">
                {visualizationContent}
              </div>
            </>
          )}
          {activeTab === 'raw' && <RawOutput output={currentResult.output} />}
          {activeTab === 'errors' && currentResult.error && (
            <div className="error">
              <pre>{currentResult.error}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Results;
