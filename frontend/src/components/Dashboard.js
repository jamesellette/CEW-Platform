import React, { useState, useEffect } from 'react';
import api from '../api';

export default function Dashboard({ user }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const response = await api.get('/system/status');
      setStatus(response.data);
      setError(null);
    } catch (err) {
      if (err.response?.status !== 403) {
        setError('Failed to load system status');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={containerStyle}>Loading system status...</div>;
  }

  if (error) {
    return <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>{error}</div>;
  }

  if (!status) {
    return null;
  }

  return (
    <div style={containerStyle}>
      <h2>System Dashboard</h2>

      <div style={gridStyle}>
        {/* System Status */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>System Status</h3>
          <div style={statusIndicatorStyle(status.status === 'operational')}>
            <span style={statusDotStyle(status.status === 'operational')}></span>
            {status.status === 'operational' ? 'Operational' : 'Degraded'}
          </div>
        </div>

        {/* Docker Status */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Container Engine</h3>
          <div style={statusIndicatorStyle(status.docker?.available)}>
            <span style={statusDotStyle(status.docker?.available)}></span>
            {status.docker?.available ? '🐳 Docker Active' : '🔄 Simulation Mode'}
          </div>
          <div style={modeInfoStyle}>
            Mode: <strong>{status.docker?.mode || 'simulation'}</strong>
          </div>
        </div>

        {/* Scenarios */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Scenarios</h3>
          <div style={metricStyle}>
            <span style={metricValueStyle}>{status.scenarios.total}</span>
            <span style={metricLabelStyle}>Total</span>
          </div>
          <div style={metricStyle}>
            <span style={{ ...metricValueStyle, color: '#28a745' }}>{status.scenarios.active}</span>
            <span style={metricLabelStyle}>Active</span>
          </div>
        </div>

        {/* Labs */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Lab Environments</h3>
          <div style={metricStyle}>
            <span style={metricValueStyle}>{status.labs.total}</span>
            <span style={metricLabelStyle}>Total Sessions</span>
          </div>
          <div style={metricStyle}>
            <span style={{ ...metricValueStyle, color: '#28a745' }}>{status.labs.active}</span>
            <span style={metricLabelStyle}>Running</span>
          </div>
        </div>

        {/* Resources */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Active Resources</h3>
          <div style={metricStyle}>
            <span style={metricValueStyle}>{status.labs.total_containers}</span>
            <span style={metricLabelStyle}>Containers</span>
          </div>
          <div style={metricStyle}>
            <span style={metricValueStyle}>{status.labs.total_networks}</span>
            <span style={metricLabelStyle}>Networks</span>
          </div>
        </div>
      </div>

      {/* Safety Status */}
      <div style={safetyCardStyle}>
        <h3 style={cardTitleStyle}>🛡️ Safety Status</h3>
        <div style={safetyGridStyle}>
          <div style={safetyItemStyle}>
            <span style={safetyStatusStyle(status.safety.air_gap_enforced)}>
              {status.safety.air_gap_enforced ? '✅' : '⚠️'}
            </span>
            <span>Air-Gap Enforced</span>
          </div>
          <div style={safetyItemStyle}>
            <span style={safetyStatusStyle(status.safety.external_network_blocked)}>
              {status.safety.external_network_blocked ? '✅' : '⚠️'}
            </span>
            <span>External Network Blocked</span>
          </div>
          <div style={safetyItemStyle}>
            <span style={safetyStatusStyle(status.safety.real_rf_blocked)}>
              {status.safety.real_rf_blocked ? '✅' : '⚠️'}
            </span>
            <span>Real RF Blocked</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const containerStyle = {
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
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

const statusIndicatorStyle = (isOperational) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '18px',
  fontWeight: 'bold',
  color: isOperational ? '#28a745' : '#dc3545',
});

const statusDotStyle = (isOperational) => ({
  width: '12px',
  height: '12px',
  borderRadius: '50%',
  backgroundColor: isOperational ? '#28a745' : '#dc3545',
  display: 'inline-block',
});

const modeInfoStyle = {
  marginTop: '8px',
  fontSize: '12px',
  color: '#666',
};

const metricStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 0',
  borderBottom: '1px solid #eee',
};

const metricValueStyle = {
  fontSize: '24px',
  fontWeight: 'bold',
  color: '#333',
};

const metricLabelStyle = {
  fontSize: '14px',
  color: '#666',
};

const safetyCardStyle = {
  backgroundColor: '#d4edda',
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #c3e6cb',
};

const safetyGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: '12px',
};

const safetyItemStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '14px',
};

const safetyStatusStyle = (isSecure) => ({
  fontSize: '18px',
});
