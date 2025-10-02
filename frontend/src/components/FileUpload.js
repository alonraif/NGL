import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

function FileUpload({ onFileSelect }) {
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
  });

  return (
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
  );
}

export default FileUpload;
