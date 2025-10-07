import React, { useState, useEffect, useCallback } from 'react';
import { toBlob } from 'html-to-image';

const STATUS_RESET_DELAY = 2000;

const CopyChartButton = ({
  targetRef,
  fileName = 'chart.png',
  className = '',
  idleLabel = 'Copy Chart'
}) => {
  const [status, setStatus] = useState('idle');

  useEffect(() => {
    if (status === 'success' || status === 'downloaded' || status === 'error') {
      const timeout = setTimeout(() => setStatus('idle'), STATUS_RESET_DELAY);
      return () => clearTimeout(timeout);
    }
    return undefined;
  }, [status]);

  const copyChart = useCallback(async () => {
    if (!targetRef?.current) {
      setStatus('error');
      return;
    }

    try {
      setStatus('copying');
      const blob = await toBlob(targetRef.current, {
        backgroundColor: '#ffffff',
        pixelRatio: Math.max(window.devicePixelRatio || 1, 2)
      });

      if (!blob) {
        throw new Error('Unable to generate chart image');
      }

      const clipboardItemCtor =
        typeof window !== 'undefined' ? window.ClipboardItem : undefined;
      const canWriteToClipboard =
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        typeof navigator.clipboard.write === 'function' &&
        typeof clipboardItemCtor === 'function';

      if (canWriteToClipboard) {
        const clipboardItem = new clipboardItemCtor({ 'image/png': blob });
        await navigator.clipboard.write([clipboardItem]);
        setStatus('success');
      } else {
        // Fallback to download when clipboard API is unavailable.
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        setStatus('downloaded');
      }
    } catch (error) {
      console.error('Failed to copy chart to clipboard:', error);
      setStatus('error');
    }
  }, [targetRef, fileName]);

  const getLabel = () => {
    switch (status) {
      case 'copying':
        return 'Copying...';
      case 'success':
        return 'Copied!';
      case 'downloaded':
        return 'Saved Image';
      case 'error':
        return 'Copy Failed';
      default:
        return idleLabel;
    }
  };

  return (
    <button
      type="button"
      className={`btn btn-secondary copy-chart-btn ${className}`.trim()}
      onClick={copyChart}
      disabled={status === 'copying'}
    >
      📋 {getLabel()}
    </button>
  );
};

export default CopyChartButton;
