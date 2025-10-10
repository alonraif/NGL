import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

function FileUpload({ onFileSelect }) {
  const [uploadMode, setUploadMode] = useState('file'); // 'file' or 'url'
  const [url, setUrl] = useState('');

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/x-bzip2': ['.bz2'],
      'application/x-tar': ['.tar'],
    },
    multiple: false,
    noClick: uploadMode === 'url', // Disable click when in URL mode
    noDrag: uploadMode === 'url',  // Disable drag when in URL mode
  });

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      // Pass URL as a special object to distinguish from File objects
      onFileSelect({
        type: 'url',
        url: url.trim(),
        name: url.trim().split('/').pop() || 'remote-file'
      });
    }
  };

  const handleUrlChange = (e) => {
    setUrl(e.target.value);
  };

  return (
    <div>
      {/* Upload Mode Toggle */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '16px',
        borderBottom: '2px solid #e5e7eb',
        paddingBottom: '8px'
      }}>
        <button
          type="button"
          onClick={() => setUploadMode('file')}
          style={{
            padding: '8px 16px',
            background: uploadMode === 'file' ? '#3b82f6' : 'transparent',
            color: uploadMode === 'file' ? 'white' : '#6b7280',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: uploadMode === 'file' ? '600' : '400',
            transition: 'all 0.2s'
          }}
        >
          📁 Upload File
        </button>
        <button
          type="button"
          onClick={() => setUploadMode('url')}
          style={{
            padding: '8px 16px',
            background: uploadMode === 'url' ? '#3b82f6' : 'transparent',
            color: uploadMode === 'url' ? 'white' : '#6b7280',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: uploadMode === 'url' ? '600' : '400',
            transition: 'all 0.2s'
          }}
        >
          🔗 From URL
        </button>
      </div>

      {/* File Upload Mode */}
      {uploadMode === 'file' && (
        <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
          <input {...getInputProps()} />
          <div className="dropzone-content">
            <div className="upload-icon">📦</div>
            {isDragActive ? (
              <p>Drop the file here...</p>
            ) : (
              <>
                <p><strong>Drag & drop a log file here, or click to select</strong></p>
                <p style={{ fontSize: '0.9rem', color: '#666' }}>
                  Supported formats: .tar.bz2, .bz2
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* URL Upload Mode */}
      {uploadMode === 'url' && (
        <div style={{
          padding: '32px',
          border: '2px solid #d1d5db',
          borderRadius: '8px',
          background: '#f9fafb'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>🔗</div>
            <p style={{ fontWeight: '600', marginBottom: '8px' }}>
              Enter Log File URL
            </p>
            <p style={{ fontSize: '0.9rem', color: '#666' }}>
              Provide a direct link to a .tar.bz2 or .bz2 file
            </p>
          </div>

          <form onSubmit={handleUrlSubmit} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="url"
              value={url}
              onChange={handleUrlChange}
              placeholder="https://example.com/logfile.tar.bz2"
              required
              style={{
                flex: 1,
                padding: '10px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />
            <button
              type="submit"
              style={{
                padding: '10px 20px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                whiteSpace: 'nowrap'
              }}
            >
              Load URL
            </button>
          </form>

          <p style={{
            fontSize: '0.85rem',
            color: '#9ca3af',
            marginTop: '12px',
            textAlign: 'center'
          }}>
            The file will be downloaded and processed from the provided URL
          </p>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
