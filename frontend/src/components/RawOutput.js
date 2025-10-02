import React, { useState } from 'react';

function RawOutput({ output }) {
  const [searchTerm, setSearchTerm] = useState('');

  if (!output) {
    return <div>No output available</div>;
  }

  const lines = output.split('\n');
  const filteredLines = searchTerm
    ? lines.filter(line => line.toLowerCase().includes(searchTerm.toLowerCase()))
    : lines;

  return (
    <div>
      <div style={{ marginBottom: '15px' }}>
        <input
          type="text"
          placeholder="Search in output..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            border: '2px solid #e0e0e0',
            borderRadius: '6px',
            fontSize: '1rem',
          }}
        />
        {searchTerm && (
          <p style={{ marginTop: '8px', color: '#666', fontSize: '0.9rem' }}>
            Found {filteredLines.length} of {lines.length} lines
          </p>
        )}
      </div>

      <div className="raw-output">
        <pre>{filteredLines.join('\n')}</pre>
      </div>

      <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
        <button
          onClick={() => {
            const blob = new Blob([output], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'lula-output.txt';
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="btn btn-primary"
          style={{ width: 'auto' }}
        >
          💾 Download Output
        </button>
        <button
          onClick={() => {
            navigator.clipboard.writeText(output);
            alert('Output copied to clipboard!');
          }}
          className="btn btn-primary"
          style={{ width: 'auto', background: '#82ca9d' }}
        >
          📋 Copy to Clipboard
        </button>
      </div>
    </div>
  );
}

export default RawOutput;
