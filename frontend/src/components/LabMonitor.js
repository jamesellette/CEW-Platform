import React, { useState, useEffect, useCallback, useRef } from 'react';
import { labApi, wsApi, authApi } from '../api';
import ContainerLogs from './ContainerLogs';

/**
 * LabMonitor component provides real-time monitoring of active lab environments.
 * Uses WebSocket for live updates of container health and resource usage.
 */
export default function LabMonitor({ labId, onClose }) {
  const [labData, setLabData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [selectedContainerLogs, setSelectedContainerLogs] = useState(null);
  const wsRef = useRef(null);

  // Fetch initial lab data
  const fetchLabData = useCallback(async () => {
    try {
      const [labResponse, healthResponse, resourcesResponse] = await Promise.all([
        labApi.get(labId),
        labApi.getHealth(labId),
        labApi.getResources(labId),
      ]);
      
      setLabData({
        ...labResponse.data,
        health: healthResponse.data.containers,
        resources: resourcesResponse.data.containers,
      });
      setError(null);
    } catch (err) {
      setError('Failed to load lab data');
      console.error('Lab data error:', err);
    } finally {
      setLoading(false);
    }
  }, [labId]);

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    const token = authApi.getToken();
    if (!token) {
      setError('Authentication required');
      return;
    }

    const wsUrl = wsApi.getLabMonitorUrl(labId, token);
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastUpdate(new Date().toLocaleTimeString());
          
          if (message.type === 'initial_state' || message.type === 'lab_update') {
            setLabData(prev => ({
              ...prev,
              ...message,
              containers: message.containers || prev?.containers,
            }));
          }
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        setConnected(false);
        console.log('WebSocket closed:', event.code, event.reason);
        
        // Attempt to reconnect after 5 seconds
        if (event.code !== 1000) {
          setTimeout(connectWebSocket, 5000);
        }
      };
    } catch (err) {
      setError('Failed to connect to WebSocket');
      console.error('WebSocket connection error:', err);
    }
  }, [labId]);

  // Initial load and WebSocket connection
  useEffect(() => {
    fetchLabData();
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [fetchLabData, connectWebSocket]);

  // Send periodic ping to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);

    return () => clearInterval(pingInterval);
  }, []);

  const handleRecover = async () => {
    try {
      const response = await labApi.recover(labId);
      alert(`Recovery initiated: ${response.data.count} containers restarted`);
      fetchLabData(); // Refresh data
    } catch (err) {
      alert('Recovery failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return <div style={containerStyle}>Loading lab data...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={fetchLabData} style={buttonStyle}>Retry</button>
        {onClose && <button onClick={onClose} style={secondaryButtonStyle}>Close</button>}
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>🖥️ Lab Monitor: {labData?.scenario_name}</h2>
        <div style={statusBarStyle}>
          <span style={connectionBadgeStyle(connected)}>
            {connected ? '🟢 Live' : '🔴 Disconnected'}
          </span>
          {lastUpdate && <span style={lastUpdateStyle}>Last update: {lastUpdate}</span>}
          <span style={modeBadgeStyle}>
            {labData?.docker_mode ? '🐳 Docker' : '🔄 Simulation'}
          </span>
        </div>
      </div>

      <div style={gridStyle}>
        {/* Lab Status Card */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Lab Status</h3>
          <div style={statusStyle(labData?.status)}>
            <span style={statusDotStyle(labData?.status)}></span>
            {labData?.status?.toUpperCase() || 'UNKNOWN'}
          </div>
          <p style={infoTextStyle}>Lab ID: {labId.slice(0, 8)}...</p>
          <p style={infoTextStyle}>Started: {labData?.started_at || 'N/A'}</p>
        </div>

        {/* Networks Card */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Networks</h3>
          {labData?.networks?.length > 0 ? (
            labData.networks.map((network) => (
              <div key={network.network_id} style={networkItemStyle}>
                <span style={networkNameStyle}>{network.name}</span>
                <span style={subnetStyle}>{network.subnet}</span>
                {network.isolated && <span style={isolatedBadgeStyle}>Isolated</span>}
              </div>
            ))
          ) : (
            <p style={emptyTextStyle}>No networks</p>
          )}
        </div>
      </div>

      {/* Containers Section */}
      <h3 style={sectionTitleStyle}>Containers ({labData?.containers?.length || 0})</h3>
      <div style={containerGridStyle}>
        {labData?.containers?.map((container) => (
          <div key={container.hostname || container.container_id} style={containerCardStyle}>
            <div style={containerHeaderStyle}>
              <h4 style={containerNameStyle}>{container.hostname}</h4>
              <span style={containerStatusBadge(container.status || container.health?.status)}>
                {container.status || container.health?.status || 'unknown'}
              </span>
            </div>
            
            <div style={containerDetailsStyle}>
              <p style={detailRowStyle}>
                <span style={detailLabelStyle}>Image:</span>
                <span style={detailValueStyle}>{container.image}</span>
              </p>
              {container.ip_address && (
                <p style={detailRowStyle}>
                  <span style={detailLabelStyle}>IP:</span>
                  <span style={detailValueStyle}>{container.ip_address}</span>
                </p>
              )}
              
              {/* Health Status */}
              {container.health && (
                <div style={healthSectionStyle}>
                  <span style={detailLabelStyle}>Health:</span>
                  <span style={healthBadge(container.health.health)}>
                    {container.health.health || 'unknown'}
                  </span>
                </div>
              )}
              
              {/* Resource Usage */}
              {container.resources && container.resources.mode !== 'error' && (
                <div style={resourceSectionStyle}>
                  <div style={resourceBarContainer}>
                    <span style={detailLabelStyle}>CPU:</span>
                    <div style={progressBarBackground}>
                      <div style={progressBarFill(container.resources.cpu_percent || 0)}></div>
                    </div>
                    <span style={resourceValueStyle}>
                      {(container.resources.cpu_percent || 0).toFixed(1)}%
                    </span>
                  </div>
                  <div style={resourceBarContainer}>
                    <span style={detailLabelStyle}>Memory:</span>
                    <div style={progressBarBackground}>
                      <div style={progressBarFill(
                        ((container.resources.memory_usage_mb || 0) / 
                         (container.resources.memory_limit_mb || 512)) * 100
                      )}></div>
                    </div>
                    <span style={resourceValueStyle}>
                      {(container.resources.memory_usage_mb || 0).toFixed(0)}MB
                    </span>
                  </div>
                </div>
              )}
              
              {/* View Logs Button */}
              <button
                onClick={() => setSelectedContainerLogs(container.hostname)}
                style={viewLogsButtonStyle}
              >
                📜 View Logs
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Container Logs Panel */}
      {selectedContainerLogs && (
        <ContainerLogs
          labId={labId}
          hostname={selectedContainerLogs}
          onClose={() => setSelectedContainerLogs(null)}
        />
      )}

      {/* Actions */}
      <div style={actionsStyle}>
        <button onClick={handleRecover} style={buttonStyle}>
          🔄 Recover Unhealthy
        </button>
        <button onClick={fetchLabData} style={secondaryButtonStyle}>
          ⟳ Refresh
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
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '20px',
  flexWrap: 'wrap',
  gap: '10px',
};

const statusBarStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
};

const connectionBadgeStyle = (connected) => ({
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  fontWeight: 'bold',
  backgroundColor: connected ? '#d4edda' : '#f8d7da',
  color: connected ? '#155724' : '#721c24',
});

const lastUpdateStyle = {
  fontSize: '12px',
  color: '#666',
};

const modeBadgeStyle = {
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  backgroundColor: '#e9ecef',
  color: '#495057',
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
  gap: '16px',
  marginBottom: '20px',
};

const cardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const cardTitleStyle = {
  margin: '0 0 12px 0',
  fontSize: '14px',
  fontWeight: '600',
  color: '#666',
  textTransform: 'uppercase',
};

const statusStyle = (status) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '18px',
  fontWeight: 'bold',
  color: status === 'running' ? '#28a745' : status === 'stopped' ? '#6c757d' : '#ffc107',
});

const statusDotStyle = (status) => ({
  width: '12px',
  height: '12px',
  borderRadius: '50%',
  backgroundColor: status === 'running' ? '#28a745' : status === 'stopped' ? '#6c757d' : '#ffc107',
});

const infoTextStyle = {
  margin: '4px 0',
  fontSize: '12px',
  color: '#666',
};

const networkItemStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px 0',
  borderBottom: '1px solid #eee',
};

const networkNameStyle = {
  fontWeight: 'bold',
  color: '#333',
};

const subnetStyle = {
  fontSize: '12px',
  color: '#666',
  fontFamily: 'monospace',
};

const isolatedBadgeStyle = {
  padding: '2px 6px',
  borderRadius: '4px',
  fontSize: '10px',
  backgroundColor: '#d4edda',
  color: '#155724',
};

const emptyTextStyle = {
  color: '#999',
  fontStyle: 'italic',
};

const sectionTitleStyle = {
  margin: '20px 0 12px 0',
  fontSize: '16px',
  fontWeight: '600',
  color: '#333',
};

const containerGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: '16px',
};

const containerCardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  border: '1px solid #e9ecef',
};

const containerHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const containerNameStyle = {
  margin: 0,
  fontSize: '16px',
  fontWeight: 'bold',
  color: '#333',
};

const containerStatusBadge = (status) => ({
  padding: '2px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  textTransform: 'uppercase',
  backgroundColor: status === 'running' ? '#d4edda' : 
                   status === 'simulated' ? '#fff3cd' : '#f8d7da',
  color: status === 'running' ? '#155724' : 
         status === 'simulated' ? '#856404' : '#721c24',
});

const containerDetailsStyle = {
  fontSize: '13px',
};

const detailRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  margin: '4px 0',
};

const detailLabelStyle = {
  color: '#666',
  minWidth: '60px',
};

const detailValueStyle = {
  color: '#333',
  fontFamily: 'monospace',
  fontSize: '12px',
};

const healthSectionStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginTop: '8px',
  paddingTop: '8px',
  borderTop: '1px solid #eee',
};

const healthBadge = (health) => ({
  padding: '2px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  backgroundColor: health === 'healthy' ? '#d4edda' : 
                   health === 'starting' ? '#fff3cd' : '#f8d7da',
  color: health === 'healthy' ? '#155724' : 
         health === 'starting' ? '#856404' : '#721c24',
});

const resourceSectionStyle = {
  marginTop: '12px',
  paddingTop: '8px',
  borderTop: '1px solid #eee',
};

const resourceBarContainer = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '6px',
};

const progressBarBackground = {
  flex: 1,
  height: '8px',
  backgroundColor: '#e9ecef',
  borderRadius: '4px',
  overflow: 'hidden',
};

const progressBarFill = (percent) => ({
  width: `${Math.min(100, percent)}%`,
  height: '100%',
  backgroundColor: percent > 80 ? '#dc3545' : percent > 60 ? '#ffc107' : '#28a745',
  borderRadius: '4px',
  transition: 'width 0.3s ease',
});

const resourceValueStyle = {
  fontSize: '11px',
  color: '#666',
  minWidth: '50px',
  textAlign: 'right',
};

const viewLogsButtonStyle = {
  marginTop: '10px',
  padding: '6px 12px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
  width: '100%',
};

const actionsStyle = {
  display: 'flex',
  gap: '10px',
  marginTop: '20px',
  paddingTop: '16px',
  borderTop: '1px solid #dee2e6',
};

const buttonStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const secondaryButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const closeButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
  marginLeft: 'auto',
};
