import React, { useState, useEffect, useCallback, useRef } from 'react';
import { labApi, authApi } from '../api';

/**
 * ContainerLogs component displays logs from a specific container.
 * Supports both fetching historical logs and real-time streaming via WebSocket.
 */
export default function ContainerLogs({ labId, hostname, onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  // Scroll to bottom when new logs arrive (if autoScroll enabled)
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Fetch initial logs
  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await labApi.getLogs(labId, hostname, 200, true);
      setLogs(response.data.logs || []);
      setError(null);
    } catch (err) {
      setError('Failed to fetch logs: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [labId, hostname]);

  // Connect to WebSocket for streaming
  const startStreaming = useCallback(() => {
    const token = authApi.getToken();
    if (!token) {
      setError('Authentication required');
      return;
    }

    const wsUrl = labApi.getLogStreamUrl(labId, hostname, token);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStreaming(true);
        setError(null);
        console.log('Log streaming connected');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'log') {
            setLogs(prev => [...prev, message.line]);
          } else if (message.type === 'error') {
            setError(message.message);
          }
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
        setStreaming(false);
      };

      ws.onclose = (event) => {
        setStreaming(false);
        console.log('WebSocket closed:', event.code, event.reason);
      };
    } catch (err) {
      setError('Failed to connect to log stream');
      console.error('WebSocket connection error:', err);
    }
  }, [labId, hostname]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User stopped streaming');
      wsRef.current = null;
    }
    setStreaming(false);
  }, []);

  // Initial load
  useEffect(() => {
    fetchLogs();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [fetchLogs]);

  // Clear logs
  const clearLogs = () => {
    setLogs([]);
  };

  // Download logs as file
  const downloadLogs = () => {
    const content = logs.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${hostname}-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Filter logs
  const filteredLogs = filter
    ? logs.filter(log => log.toLowerCase().includes(filter.toLowerCase()))
    : logs;

  if (loading) {
    return <div style={containerStyle}>Loading logs for {hostname}...</div>;
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h3 style={titleStyle}>📜 Logs: {hostname}</h3>
        <div style={controlsStyle}>
          <input
            type="text"
            placeholder="Filter logs..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={filterInputStyle}
          />
          <label style={checkboxLabelStyle}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
        </div>
      </div>

      {error && (
        <div style={errorStyle}>
          ⚠️ {error}
        </div>
      )}

      <div style={statusBarStyle}>
        <span style={statusBadgeStyle(streaming)}>
          {streaming ? '🔴 Live Streaming' : '📋 Static View'}
        </span>
        <span style={countStyle}>
          {filteredLogs.length} {filter ? 'matching ' : ''}lines
        </span>
      </div>

      <div style={logsContainerStyle}>
        {filteredLogs.length === 0 ? (
          <div style={emptyLogsStyle}>No logs available</div>
        ) : (
          filteredLogs.map((line, index) => (
            <div key={index} style={logLineStyle(line)}>
              <span style={lineNumberStyle}>{index + 1}</span>
              <span style={logTextStyle}>{line}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      <div style={actionsStyle}>
        {!streaming ? (
          <button onClick={startStreaming} style={primaryButtonStyle}>
            ▶️ Start Streaming
          </button>
        ) : (
          <button onClick={stopStreaming} style={dangerButtonStyle}>
            ⏹️ Stop Streaming
          </button>
        )}
        <button onClick={fetchLogs} style={secondaryButtonStyle}>
          ⟳ Refresh
        </button>
        <button onClick={clearLogs} style={secondaryButtonStyle}>
          🗑️ Clear
        </button>
        <button onClick={downloadLogs} style={secondaryButtonStyle}>
          ⬇️ Download
        </button>
        {onClose && (
          <button onClick={onClose} style={closeButtonStyle}>
            ✕ Close
          </button>
        )}
      </div>
    </div>
  );
}

// Styles
const containerStyle = {
  padding: '16px',
  backgroundColor: '#1e1e1e',
  borderRadius: '8px',
  marginTop: '16px',
  color: '#d4d4d4',
};

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
  flexWrap: 'wrap',
  gap: '10px',
};

const titleStyle = {
  margin: 0,
  color: '#ffffff',
  fontSize: '16px',
};

const controlsStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
};

const filterInputStyle = {
  padding: '6px 12px',
  borderRadius: '4px',
  border: '1px solid #444',
  backgroundColor: '#2d2d2d',
  color: '#d4d4d4',
  fontSize: '13px',
  width: '200px',
};

const checkboxLabelStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
  fontSize: '13px',
  color: '#888',
};

const errorStyle = {
  padding: '8px 12px',
  backgroundColor: '#5c2020',
  borderRadius: '4px',
  marginBottom: '12px',
  color: '#ff8080',
};

const statusBarStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px',
  fontSize: '12px',
};

const statusBadgeStyle = (isStreaming) => ({
  padding: '4px 8px',
  borderRadius: '4px',
  backgroundColor: isStreaming ? '#2d4a2d' : '#2d2d2d',
  color: isStreaming ? '#90ee90' : '#888',
});

const countStyle = {
  color: '#888',
};

const logsContainerStyle = {
  maxHeight: '400px',
  overflowY: 'auto',
  backgroundColor: '#0d0d0d',
  borderRadius: '4px',
  padding: '8px',
  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
  fontSize: '12px',
  lineHeight: '1.5',
};

const emptyLogsStyle = {
  color: '#666',
  fontStyle: 'italic',
  textAlign: 'center',
  padding: '20px',
};

const logLineStyle = (line) => {
  let backgroundColor = 'transparent';
  if (line.toLowerCase().includes('error')) {
    backgroundColor = 'rgba(255, 80, 80, 0.1)';
  } else if (line.toLowerCase().includes('warn')) {
    backgroundColor = 'rgba(255, 200, 0, 0.1)';
  }
  return {
    display: 'flex',
    gap: '8px',
    padding: '2px 4px',
    backgroundColor,
    borderRadius: '2px',
  };
};

const lineNumberStyle = {
  color: '#555',
  minWidth: '35px',
  textAlign: 'right',
  userSelect: 'none',
};

const logTextStyle = {
  flex: 1,
  wordBreak: 'break-all',
  whiteSpace: 'pre-wrap',
};

const actionsStyle = {
  display: 'flex',
  gap: '8px',
  marginTop: '12px',
  flexWrap: 'wrap',
};

const primaryButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const secondaryButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#4a4a4a',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const dangerButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const closeButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
  marginLeft: 'auto',
};
