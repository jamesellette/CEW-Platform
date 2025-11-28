import React, { useState, useEffect } from 'react';
import { scenarioApi, killSwitchApi } from '../api';

export default function InstructorControls({ user }) {
  const [activeScenarios, setActiveScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadActiveScenarios();
    // Poll for updates every 10 seconds
    const interval = setInterval(loadActiveScenarios, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadActiveScenarios = async () => {
    try {
      const response = await scenarioApi.listActive();
      setActiveScenarios(response.data);
      setError(null);
    } catch (err) {
      if (err.response?.status !== 403) {
        setError('Failed to load active scenarios');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivate = async (scenarioId) => {
    if (!window.confirm('Are you sure you want to deactivate this scenario?')) {
      return;
    }

    try {
      await scenarioApi.deactivate(scenarioId);
      setMessage('Scenario deactivated successfully');
      loadActiveScenarios();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to deactivate scenario');
    }
  };

  const handleKillSwitch = async () => {
    if (!window.confirm('⚠️ EMERGENCY KILL SWITCH ⚠️\n\nThis will immediately deactivate ALL active scenarios.\n\nAre you sure?')) {
      return;
    }

    try {
      const response = await killSwitchApi.activate();
      setMessage(`Kill switch activated. ${response.data.deactivated_count} scenarios deactivated.`);
      loadActiveScenarios();
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
          disabled={activeScenarios.length === 0}
        >
          🛑 EMERGENCY KILL SWITCH
        </button>
        <small style={{ color: '#666', display: 'block', marginTop: '8px' }}>
          Immediately stops ALL active training scenarios
        </small>
      </div>

      {/* Active Scenarios */}
      <h3>Active Scenarios ({activeScenarios.length})</h3>
      {loading ? (
        <p>Loading...</p>
      ) : activeScenarios.length === 0 ? (
        <p style={{ color: '#666' }}>No active scenarios</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Scenario</th>
              <th style={thStyle}>Activated By</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {activeScenarios.map((scenario) => (
              <tr key={scenario.scenario_id}>
                <td style={tdStyle}>{scenario.scenario_name}</td>
                <td style={tdStyle}>{scenario.activated_by}</td>
                <td style={tdStyle}>
                  <span style={statusBadgeStyle}>● Active</span>
                </td>
                <td style={tdStyle}>
                  <button
                    onClick={() => handleDeactivate(scenario.scenario_id)}
                    style={deactivateButtonStyle}
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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

const deactivateButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#ffc107',
  color: '#333',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};

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
