import React, { useState, useEffect } from 'react';
import { scenarioApi, killSwitchApi, labApi } from '../api';

export default function InstructorControls({ user }) {
  const [activeScenarios, setActiveScenarios] = useState([]);
  const [activeLabs, setActiveLabs] = useState([]);
  const [selectedLab, setSelectedLab] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadActiveData();
    // Poll for updates every 10 seconds
    const interval = setInterval(loadActiveData, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadActiveData = async () => {
    try {
      const [scenariosResponse, labsResponse] = await Promise.all([
        scenarioApi.listActive(),
        labApi.listActive()
      ]);
      setActiveScenarios(scenariosResponse.data);
      setActiveLabs(labsResponse.data);
      setError(null);
    } catch (err) {
      if (err.response?.status !== 403) {
        setError('Failed to load active data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleViewLab = async (labId) => {
    try {
      const response = await labApi.get(labId);
      setSelectedLab(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load lab details');
    }
  };

  const handleDeactivate = async (scenarioId) => {
    if (!window.confirm('Are you sure you want to deactivate this scenario?')) {
      return;
    }

    try {
      await scenarioApi.deactivate(scenarioId);
      setMessage('Scenario deactivated successfully');
      setSelectedLab(null);
      loadActiveData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to deactivate scenario');
    }
  };

  const handleStopLab = async (labId) => {
    if (!window.confirm('Are you sure you want to stop this lab environment?')) {
      return;
    }

    try {
      await labApi.stop(labId);
      setMessage('Lab stopped successfully');
      setSelectedLab(null);
      loadActiveData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to stop lab');
    }
  };

  const handleKillSwitch = async () => {
    if (!window.confirm('⚠️ EMERGENCY KILL SWITCH ⚠️\n\nThis will immediately deactivate ALL active scenarios and stop ALL lab environments.\n\nAre you sure?')) {
      return;
    }

    try {
      const response = await killSwitchApi.activate();
      setMessage(`Kill switch activated. ${response.data.deactivated_count} scenarios deactivated, ${response.data.stopped_labs?.length || 0} labs stopped.`);
      setSelectedLab(null);
      loadActiveData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to activate kill switch');
    }
  };

  // Only show for instructors and admins
  if (!user || !['admin', 'instructor'].includes(user.role)) {
    return null;
  }

  return (
    <div style={containerStyle}>
      <h2>Instructor Controls</h2>

      {error && <div style={errorStyle}>{error}</div>}
      {message && <div style={successStyle}>{message}</div>}

      {/* Kill Switch */}
      <div style={killSwitchContainerStyle}>
        <button
          onClick={handleKillSwitch}
          style={killSwitchButtonStyle}
          disabled={activeScenarios.length === 0 && activeLabs.length === 0}
        >
          🛑 EMERGENCY KILL SWITCH
        </button>
        <small style={{ color: '#666', display: 'block', marginTop: '8px' }}>
          Immediately stops ALL active training scenarios and lab environments
        </small>
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Active Scenarios / Labs */}
        <div style={{ flex: 1 }}>
          <h3>Active Labs ({activeLabs.length})</h3>
          {loading ? (
            <p>Loading...</p>
          ) : activeLabs.length === 0 ? (
            <p style={{ color: '#666' }}>No active labs</p>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Scenario</th>
                  <th style={thStyle}>Activated By</th>
                  <th style={thStyle}>Containers</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeLabs.map((lab) => (
                  <tr key={lab.lab_id}>
                    <td style={tdStyle}>{lab.scenario_name}</td>
                    <td style={tdStyle}>{lab.activated_by}</td>
                    <td style={tdStyle}>
                      <span style={countBadgeStyle}>
                        {lab.container_count} containers
                      </span>
                      <span style={countBadgeStyle}>
                        {lab.network_count} networks
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => handleViewLab(lab.lab_id)}
                        style={viewButtonStyle}
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleStopLab(lab.lab_id)}
                        style={deactivateButtonStyle}
                      >
                        Stop
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Lab Details Panel */}
        {selectedLab && (
          <div style={detailsPanelStyle}>
            <h3>Lab Details</h3>
            <button
              onClick={() => setSelectedLab(null)}
              style={closeButtonStyle}
            >
              ×
            </button>
            <p><strong>Lab ID:</strong> {selectedLab.lab_id}</p>
            <p><strong>Scenario:</strong> {selectedLab.scenario_name}</p>
            <p><strong>Status:</strong> <span style={statusBadgeStyle}>● {selectedLab.status}</span></p>
            <p><strong>Started:</strong> {selectedLab.started_at ? new Date(selectedLab.started_at).toLocaleString() : 'N/A'}</p>

            <h4>Networks ({selectedLab.networks?.length || 0})</h4>
            <ul style={{ fontSize: '14px' }}>
              {selectedLab.networks?.map((net) => (
                <li key={net.network_id}>
                  <strong>{net.name}</strong>: {net.subnet}
                  {net.isolated && <span style={isolatedBadgeStyle}>isolated</span>}
                </li>
              ))}
            </ul>

            <h4>Containers ({selectedLab.containers?.length || 0})</h4>
            <ul style={{ fontSize: '14px' }}>
              {selectedLab.containers?.map((container) => (
                <li key={container.container_id}>
                  <strong>{container.hostname}</strong> ({container.image})
                  {container.ip_address && <span> - {container.ip_address}</span>}
                  <span style={containerStatusStyle(container.status)}>{container.status}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

const containerStyle = {
  padding: '20px',
  backgroundColor: '#fff3cd',
  borderRadius: '8px',
  marginBottom: '20px',
  border: '1px solid #ffc107',
};

const killSwitchContainerStyle = {
  textAlign: 'center',
  padding: '20px',
  marginBottom: '20px',
};

const killSwitchButtonStyle = {
  padding: '15px 30px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  fontSize: '18px',
  fontWeight: 'bold',
  cursor: 'pointer',
  boxShadow: '0 4px 6px rgba(0,0,0,0.2)',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  backgroundColor: 'white',
};

const thStyle = {
  border: '1px solid #ddd',
  padding: '10px',
  backgroundColor: '#f4f4f4',
  textAlign: 'left',
};

const tdStyle = {
  border: '1px solid #ddd',
  padding: '10px',
};

const statusBadgeStyle = {
  color: '#28a745',
  fontWeight: 'bold',
};

const countBadgeStyle = {
  backgroundColor: '#e9ecef',
  padding: '2px 6px',
  borderRadius: '4px',
  fontSize: '12px',
  marginRight: '4px',
};

const viewButtonStyle = {
  padding: '4px 8px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  marginRight: '4px',
};

const deactivateButtonStyle = {
  padding: '4px 8px',
  backgroundColor: '#ffc107',
  color: '#333',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};

const detailsPanelStyle = {
  flex: 1,
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #ddd',
  position: 'relative',
};

const closeButtonStyle = {
  position: 'absolute',
  top: '8px',
  right: '8px',
  background: 'none',
  border: 'none',
  fontSize: '24px',
  cursor: 'pointer',
  color: '#666',
};

const isolatedBadgeStyle = {
  backgroundColor: '#28a745',
  color: 'white',
  padding: '1px 6px',
  borderRadius: '10px',
  fontSize: '10px',
  marginLeft: '8px',
};

const containerStatusStyle = (status) => ({
  backgroundColor: status === 'running' || status === 'simulated' ? '#28a745' : '#6c757d',
  color: 'white',
  padding: '1px 6px',
  borderRadius: '10px',
  fontSize: '10px',
  marginLeft: '8px',
});

const errorStyle = {
  backgroundColor: '#f8d7da',
  color: '#721c24',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};

const successStyle = {
  backgroundColor: '#d4edda',
  color: '#155724',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};
