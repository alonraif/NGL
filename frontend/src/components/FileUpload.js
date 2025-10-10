import React, { useState, useRef } from 'react';

function FileUpload({ onFileSelect }) {
  const [uploadMode, setUploadMode] = useState('file'); // 'file' or 'url'
  const [url, setUrl] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      // Pass URL as a special object to distinguish from File objects
      onFileSelect({
        type: 'url',
        url: url.trim(),
        name: url.trim().split('/').pop().split('?')[0] || 'remote-file'
      });
    }
  };

  const handleUrlChange = (e) => {
    setUrl(e.target.value);
  };

  return (
    <div className="file-upload-container">
      {/* Upload Mode Toggle */}
      <div className="upload-mode-toggle">
        <button
          type="button"
          onClick={() => setUploadMode('file')}
          className={`mode-button ${uploadMode === 'file' ? 'active' : ''}`}
        >
          <span className="mode-icon">📁</span>
          <span className="mode-label">Select File</span>
        </button>
        <button
          type="button"
          onClick={() => setUploadMode('url')}
          className={`mode-button ${uploadMode === 'url' ? 'active' : ''}`}
        >
          <span className="mode-icon">🔗</span>
          <span className="mode-label">From URL</span>
        </button>
      </div>

      {/* File Upload Mode */}
      {uploadMode === 'file' && (
        <div className="upload-content">
          <input
            ref={fileInputRef}
            type="file"
            accept=".tar.bz2,.bz2,.tar.gz,.gz"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <div className="upload-area">
            <div className="upload-icon-large">📦</div>
            <h3 className="upload-title">Select Log File</h3>
            <p className="upload-subtitle">
              Choose a compressed log file from your computer
            </p>
            <button
              type="button"
              onClick={handleBrowseClick}
              className="browse-button"
            >
              Browse Files
            </button>
            <p className="upload-formats">
              Supported formats: .tar.bz2, .bz2, .tar.gz, .gz
            </p>
          </div>
        </div>
      )}

      {/* URL Upload Mode */}
      {uploadMode === 'url' && (
        <div className="upload-content">
          <div className="upload-area">
            <div className="upload-icon-large">🔗</div>
            <h3 className="upload-title">Enter Log File URL</h3>
            <p className="upload-subtitle">
              Provide a direct link to a compressed log file
            </p>
            <form onSubmit={handleUrlSubmit} className="url-form">
              <input
                type="url"
                value={url}
                onChange={handleUrlChange}
                placeholder="https://example.com/logfile.tar.bz2"
                required
                className="url-input"
              />
              <button type="submit" className="url-submit-button">
                Load from URL
              </button>
            </form>
            <p className="upload-formats">
              Supported formats: .tar.bz2, .bz2, .tar.gz, .gz
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
