import React, { createContext, useState, useContext, useCallback, useEffect } from 'react';

const ParsingContext = createContext(null);

export const useParsing = () => {
  const context = useContext(ParsingContext);
  if (!context) {
    throw new Error('useParsing must be used within ParsingProvider');
  }
  return context;
};

// Load state from localStorage
const loadFromStorage = () => {
  try {
    const saved = localStorage.getItem('ngl_parsing_state');
    console.log('[ParsingContext] Loading from localStorage:', saved);
    if (saved) {
      const parsed = JSON.parse(saved);
      console.log('[ParsingContext] Parsed state:', parsed);
      return {
        parsingJobs: parsed.parsingJobs || {},
        activeJobId: parsed.activeJobId || null
      };
    }
  } catch (error) {
    console.error('Failed to load parsing state from localStorage:', error);
  }
  console.log('[ParsingContext] No saved state found, returning empty');
  return { parsingJobs: {}, activeJobId: null };
};

// Save state to localStorage
const saveToStorage = (parsingJobs, activeJobId) => {
  try {
    const data = {
      parsingJobs,
      activeJobId
    };
    console.log('[ParsingContext] Saving to localStorage:', data);
    localStorage.setItem('ngl_parsing_state', JSON.stringify(data));
  } catch (error) {
    console.error('Failed to save parsing state to localStorage:', error);
  }
};

export const ParsingProvider = ({ children }) => {
  const initialState = loadFromStorage();
  const [parsingJobs, setParsingJobs] = useState(initialState.parsingJobs);
  const [activeJobId, setActiveJobId] = useState(initialState.activeJobId);

  // Persist to localStorage whenever state changes
  useEffect(() => {
    saveToStorage(parsingJobs, activeJobId);
  }, [parsingJobs, activeJobId]);

  // On mount, clean up old completed jobs (older than 5 minutes)
  useEffect(() => {
    const cleanupOldJobs = () => {
      const now = Date.now();
      const fiveMinutes = 5 * 60 * 1000;
      const updatedJobs = { ...parsingJobs };
      let hasChanges = false;

      Object.keys(updatedJobs).forEach(jobId => {
        const job = updatedJobs[jobId];
        // Remove completed jobs older than 5 minutes
        if (job.status === 'completed' && job.endTime && (now - job.endTime > fiveMinutes)) {
          delete updatedJobs[jobId];
          hasChanges = true;
        }
      });

      if (hasChanges) {
        setParsingJobs(updatedJobs);
      }
    };

    cleanupOldJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  const startParsing = useCallback((jobId, jobData) => {
    setParsingJobs(prev => ({
      ...prev,
      [jobId]: {
        id: jobId,
        ...jobData,
        status: 'running',
        startTime: Date.now(),
        parserQueue: jobData.parsers.map(parser => ({
          ...parser,
          status: 'pending',
          time: 0,
          error: null
        })),
        currentParserIndex: 0,
        completedCount: 0,
        results: []
      }
    }));
    setActiveJobId(jobId);
  }, []);

  const updateParserStatus = useCallback((jobId, parserIndex, status, data = {}) => {
    setParsingJobs(prev => {
      const job = prev[jobId];
      if (!job) return prev;

      const updatedQueue = [...job.parserQueue];
      updatedQueue[parserIndex] = {
        ...updatedQueue[parserIndex],
        status,
        ...data
      };

      return {
        ...prev,
        [jobId]: {
          ...job,
          parserQueue: updatedQueue,
          currentParserIndex: status === 'running' ? parserIndex : job.currentParserIndex
        }
      };
    });
  }, []);

  const addParserResult = useCallback((jobId, result) => {
    setParsingJobs(prev => {
      const job = prev[jobId];
      if (!job) return prev;

      return {
        ...prev,
        [jobId]: {
          ...job,
          results: [...job.results, result],
          completedCount: job.completedCount + 1
        }
      };
    });
  }, []);

  const completeJob = useCallback((jobId) => {
    setParsingJobs(prev => {
      const job = prev[jobId];
      if (!job) return prev;

      return {
        ...prev,
        [jobId]: {
          ...job,
          status: 'completed',
          endTime: Date.now()
        }
      };
    });

    // Don't clear activeJobId - keep the job active so results remain visible
    // User can manually clear it with the Cancel/Clear button

    // Auto-clear completed job from storage after 5 minutes
    setTimeout(() => {
      clearJob(jobId);
    }, 5 * 60 * 1000);
  }, []);

  const cancelJob = useCallback((jobId) => {
    setParsingJobs(prev => {
      const job = prev[jobId];
      if (!job) return prev;

      return {
        ...prev,
        [jobId]: {
          ...job,
          status: 'cancelled',
          endTime: Date.now()
        }
      };
    });
  }, []);

  const setCurrentAnalysisId = useCallback((jobId, analysisId) => {
    setParsingJobs(prev => {
      const job = prev[jobId];
      if (!job) return prev;

      return {
        ...prev,
        [jobId]: {
          ...job,
          currentAnalysisId: analysisId
        }
      };
    });
  }, []);

  const clearJob = useCallback((jobId) => {
    setParsingJobs(prev => {
      const newJobs = { ...prev };
      delete newJobs[jobId];
      return newJobs;
    });

    setActiveJobId(current => current === jobId ? null : current);
  }, []);

  const getActiveJob = useCallback(() => {
    return activeJobId ? parsingJobs[activeJobId] : null;
  }, [activeJobId, parsingJobs]);

  const isParsingActive = useCallback(() => {
    return activeJobId !== null && parsingJobs[activeJobId]?.status === 'running';
  }, [activeJobId, parsingJobs]);

  const value = {
    parsingJobs,
    activeJobId,
    startParsing,
    updateParserStatus,
    addParserResult,
    completeJob,
    cancelJob,
    setCurrentAnalysisId,
    clearJob,
    getActiveJob,
    isParsingActive
  };

  return (
    <ParsingContext.Provider value={value}>
      {children}
    </ParsingContext.Provider>
  );
};
