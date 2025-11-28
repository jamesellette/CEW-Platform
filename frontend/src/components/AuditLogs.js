import React, { useState, useEffect } from 'react';
import { auditApi } from '../api';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({ username: '', action: '' });

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter.username) params.username = filter.username;
      if (filter.action) params.action = filter.action;
      params.limit = 100;

      const response = await auditApi.logs(params);
      setLogs(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load audit logs');
      console.error('Error loading audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = (e) => {
    e.preventDefault();
    loadLogs();
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getActionColor = (action) => {
    if (action.includes('login') || action.includes('LOGIN')) return '#28a745';
    if (action.includes('failed') || action.includes('FAILED')) return '#dc3545';
    if (action.includes('kill') || action.includes('KILL')) return '#dc3545';
    if (action.includes('activate') || action.includes('ACTIVATE')) return '#17a2b8';
    if (action.includes('deactivate') || action.includes('DEACTIVATE')) return '#ffc107';
    return '#6c757d';
  };

  return (
    <div style={containerStyle}>
      <h2>📋 Audit Logs</h2>
      <p style={{ color: '#666' }}>
        View system activity and security events.
      </p>

      {/* Filter Form */}
      <form onSubmit={handleFilter} style={filterFormStyle}>
        <input
          type="text"
          placeholder="Filter by username"
          value={filter.username}
          onChange={(e) => setFilter({ ...filter, username: e.target.value })}
          style={inputStyle}
        />
        <select
          value={filter.action}
          onChange={(e) => setFilter({ ...filter, action: e.target.value })}
          style={inputStyle}
        >
          <option value="">All Actions</option>
          <option value="login">Login</option>
          <option value="failed_login">Failed Login</option>
          <option value="activate_scenario">Activate Scenario</option>
          <option value="deactivate_scenario">Deactivate Scenario</option>
          <option value="kill_switch">Kill Switch</option>
          <option value="create_user">Create User</option>
        </select>
        <button type="submit" style={btnStyle}>
          🔍 Filter
        </button>
        <button
          type="button"
          onClick={() => {
            setFilter({ username: '', action: '' });
            loadLogs();
          }}
          style={{ ...btnStyle, backgroundColor: '#6c757d' }}
        >
          ↻ Reset
        </button>
      </form>

      {error && <div style={errorStyle}>{error}</div>}

      {loading ? (
        <p>Loading audit logs...</p>
      ) : logs.length === 0 ? (
        <p style={{ color: '#666' }}>No audit logs found.</p>
      ) : (
        <div style={tableContainerStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Timestamp</th>
                <th style={thStyle}>User</th>
                <th style={thStyle}>Action</th>
                <th style={thStyle}>Resource</th>
                <th style={thStyle}>Details</th>
                <th style={thStyle}>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td style={tdStyle}>{formatTimestamp(log.timestamp)}</td>
                  <td style={tdStyle}>{log.username || '-'}</td>
                  <td style={tdStyle}>
                    <span style={{ ...actionBadgeStyle, backgroundColor: getActionColor(log.action) }}>
                      {log.action}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    {log.resource_type && (
                      <span>
                        {log.resource_type}
                        {log.resource_id && typeof log.resource_id === 'string' && `: ${log.resource_id.substring(0, 8)}...`}
                      </span>
                    )}
                  </td>
                  <td style={{ ...tdStyle, maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {log.details || '-'}
                  </td>
                  <td style={tdStyle}>
                    {log.success ? (
                      <span style={{ color: '#28a745' }}>✓ Success</span>
                    ) : (
                      <span style={{ color: '#dc3545' }}>✗ Failed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const containerStyle = {
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const filterFormStyle = {
  display: 'flex',
  gap: '10px',
  marginBottom: '20px',
  flexWrap: 'wrap',
};

const inputStyle = {
  padding: '8px 12px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  fontSize: '14px',
};

const btnStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const tableContainerStyle = {
  overflowX: 'auto',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  backgroundColor: 'white',
  fontSize: '14px',
};

const thStyle = {
  border: '1px solid #ddd',
  padding: '10px',
  backgroundColor: '#f4f4f4',
  textAlign: 'left',
  fontWeight: '600',
};

const tdStyle = {
  border: '1px solid #ddd',
  padding: '10px',
  verticalAlign: 'top',
};

const actionBadgeStyle = {
  padding: '2px 8px',
  borderRadius: '12px',
  color: 'white',
  fontSize: '12px',
  fontWeight: '500',
};

const errorStyle = {
  backgroundColor: '#f8d7da',
  color: '#721c24',
  padding: '12px',
  borderRadius: '4px',
  marginBottom: '16px',
};
