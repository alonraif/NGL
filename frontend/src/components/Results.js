import React, { useState } from 'react';
import ModemStats from './ModemStats';
import BandwidthChart from './BandwidthChart';
import ModemBandwidthChart from './ModemBandwidthChart';
import SessionsTable from './SessionsTable';
import MemoryChart from './MemoryChart';
import ModemGradingChart from './ModemGradingChart';
import RawOutput from './RawOutput';

function Results({ data }) {
  const [activeTab, setActiveTab] = useState('visualization');

  const renderVisualization = () => {
    if (data.parse_mode === 'md' && data.parsed_data) {
      return <ModemStats modems={data.parsed_data} />;
    } else if (data.parse_mode === 'md-bw' && data.parsed_data) {
      return <ModemBandwidthChart data={data.parsed_data} />;
    } else if (['bw', 'md-db-bw'].includes(data.parse_mode) && data.parsed_data) {
      return <BandwidthChart data={data.parsed_data} mode={data.parse_mode} />;
    } else if (data.parse_mode === 'sessions' && data.parsed_data) {
      return <SessionsTable sessions={data.parsed_data} />;
    } else if (data.parse_mode === 'memory' && data.parsed_data) {
      return <MemoryChart data={data.parsed_data} />;
    } else if (data.parse_mode === 'grading' && data.parsed_data) {
      return <ModemGradingChart data={data.parsed_data} />;
    } else {
      return (
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <p>No visualization available for this parse mode.</p>
          <p>Check the "Raw Output" tab to see the results.</p>
        </div>
      );
    }
  };

  return (
    <div className="results-section">
      <div className="card">
        <h2>Analysis Results</h2>

        {data.filename && (
          <div className="file-info">
            <p><strong>File:</strong> {data.filename}</p>
            <p><strong>Parse Mode:</strong> {data.parse_mode}</p>
          </div>
        )}

        <div className="results-tabs">
          <button
            className={`tab ${activeTab === 'visualization' ? 'active' : ''}`}
            onClick={() => setActiveTab('visualization')}
          >
            📊 Visualization
          </button>
          <button
            className={`tab ${activeTab === 'raw' ? 'active' : ''}`}
            onClick={() => setActiveTab('raw')}
          >
            📝 Raw Output
          </button>
          {data.error && (
            <button
              className={`tab ${activeTab === 'errors' ? 'active' : ''}`}
              onClick={() => setActiveTab('errors')}
            >
              ⚠️ Errors
            </button>
          )}
        </div>

        <div className="tab-content">
          {activeTab === 'visualization' && renderVisualization()}
          {activeTab === 'raw' && <RawOutput output={data.output} />}
          {activeTab === 'errors' && data.error && (
            <div className="error">
              <pre>{data.error}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Results;
