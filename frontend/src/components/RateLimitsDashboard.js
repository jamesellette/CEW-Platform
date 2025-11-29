import React, { useState, useEffect, useCallback } from 'react';
import { rateLimitApi } from '../api';

/**
 * Rate Limits Dashboard component.
 * Provides admin UI for managing API rate limiting, viewing statistics, and handling violations.
 */
export default function RateLimitsDashboard({ user }) {
  const [status, setStatus] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [violations, setViolations] = useState([]);
  const [topUsers, setTopUsers] = useState([]);
  const [topEndpoints, setTopEndpoints] = useState([]);
  const [myStatus, setMyStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showBlockUserForm, setShowBlockUserForm] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  const isAdmin = user?.role === 'admin';

  // Form states
  const [blockForm, setBlockForm] = useState({
    userId: '',
    duration: 60,
  });

  // Fetch rate limit status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await rateLimitApi.getStatus();
      setStatus(response.data);
    } catch (err) {
      console.error('Failed to load status:', err);
    }
  }, []);

  // Fetch statistics
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await rateLimitApi.getStatistics();
      setStatistics(response.data);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  }, []);

  // Fetch violations
  const fetchViolations = useCallback(async () => {
    try {
      const response = await rateLimitApi.getViolations();
      setViolations(response.data || []);
    } catch (err) {
      console.error('Failed to load violations:', err);
    }
  }, []);

  // Fetch top users
  const fetchTopUsers = useCallback(async () => {
    try {
      const response = await rateLimitApi.getTopUsers(10);
      setTopUsers(response.data || []);
    } catch (err) {
      console.error('Failed to load top users:', err);
    }
  }, []);

  // Fetch top endpoints
  const fetchTopEndpoints = useCallback(async () => {
    try {
      const response = await rateLimitApi.getTopEndpoints(10);
      setTopEndpoints(response.data || []);
    } catch (err) {
      console.error('Failed to load top endpoints:', err);
    }
  }, []);

  // Fetch my status
  const fetchMyStatus = useCallback(async () => {
    try {
      const response = await rateLimitApi.getMyStatus();
      setMyStatus(response.data);
    } catch (err) {
      console.error('Failed to load my status:', err);
    }
  }, []);

  // Load all data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const promises = [fetchMyStatus()];
      if (isAdmin) {
        promises.push(
          fetchStatus(),
          fetchStatistics(),
          fetchViolations(),
          fetchTopUsers(),
          fetchTopEndpoints()
        );
      }
      await Promise.all(promises);
    } catch (err) {
      setError('Failed to load rate limit data');
    } finally {
      setLoading(false);
    }
  }, [isAdmin, fetchStatus, fetchStatistics, fetchViolations, fetchTopUsers, fetchTopEndpoints, fetchMyStatus]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Toggle rate limiting
  const handleToggleEnabled = async () => {
    try {
      await rateLimitApi.setEnabled(!status?.enabled);
      setSuccessMessage(`Rate limiting ${status?.enabled ? 'disabled' : 'enabled'}`);
      fetchStatus();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to toggle rate limiting');
    }
  };

  // Block user
  const handleBlockUser = async (e) => {
    e.preventDefault();
    const duration = parseInt(blockForm.duration, 10);
    if (isNaN(duration) || duration <= 0) {
      setActionError('Please enter a valid positive duration in minutes');
      return;
    }
    try {
      await rateLimitApi.blockUser(blockForm.userId, duration);
      setShowBlockUserForm(false);
      setBlockForm({ userId: '', duration: 60 });
      setSuccessMessage(`User ${blockForm.userId} blocked for ${duration} minutes`);
      fetchViolations();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to block user: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Unblock user
  const handleUnblockUser = async (userId) => {
    try {
      await rateLimitApi.unblockUser(userId);
      setSuccessMessage(`User ${userId} unblocked`);
      fetchViolations();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to unblock user');
    }
  };

  // Reset user state
  const handleResetUserState = async (userId) => {
    try {
      await rateLimitApi.resetUserState(userId);
      setSuccessMessage(`Rate limit state reset for ${userId}`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to reset user state');
    }
  };

  // Reset statistics
  const handleResetStatistics = async () => {
    if (!window.confirm('Are you sure you want to reset all rate limiting statistics?')) return;
    try {
      await rateLimitApi.resetStatistics();
      setSuccessMessage('Statistics reset successfully');
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to reset statistics');
    }
  };

  // View user details
  const handleViewUserDetails = async (userId) => {
    try {
      const response = await rateLimitApi.getUserState(userId);
      setSelectedUser({ userId, ...response.data });
    } catch (err) {
      setActionError('Failed to load user details');
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return <div style={containerStyle}>Loading rate limits dashboard...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={loadAllData} style={buttonStyle}>Retry</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>🚦 API Rate Limiting</h2>
        {isAdmin && status && (
          <button
            onClick={handleToggleEnabled}
            style={status.enabled ? disableButtonStyle : enableButtonStyle}
          >
            {status.enabled ? '⏸ Disable Rate Limiting' : '▶ Enable Rate Limiting'}
          </button>
        )}
      </div>

      {successMessage && (
        <div style={successMessageStyle}>
          <span>✓ {successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} style={dismissButtonStyle}>✕</button>
        </div>
      )}

      {actionError && (
        <div style={errorMessageStyle}>
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} style={dismissButtonStyle}>✕</button>
        </div>
      )}

      {/* My Rate Limit Status (visible to all users) */}
      {myStatus && (
        <div style={myStatusCardStyle}>
          <h4>Your Rate Limit Status</h4>
          <div style={myStatusGridStyle}>
            <div style={myStatusItemStyle}>
              <span style={myStatusLabelStyle}>Tier:</span>
              <span style={tierBadgeStyle}>{myStatus.tier}</span>
            </div>
            {myStatus.limits && (
              <>
                <div style={myStatusItemStyle}>
                  <span style={myStatusLabelStyle}>Per Minute:</span>
                  <span>{myStatus.limits.requests_per_minute || 'Unlimited'}</span>
                </div>
                <div style={myStatusItemStyle}>
                  <span style={myStatusLabelStyle}>Per Hour:</span>
                  <span>{myStatus.limits.requests_per_hour || 'Unlimited'}</span>
                </div>
              </>
            )}
            {myStatus.current_state && (
              <>
                <div style={myStatusItemStyle}>
                  <span style={myStatusLabelStyle}>Requests (minute):</span>
                  <span>{myStatus.current_state.requests_in_minute || 0}</span>
                </div>
                <div style={myStatusItemStyle}>
                  <span style={myStatusLabelStyle}>Requests (hour):</span>
                  <span>{myStatus.current_state.requests_in_hour || 0}</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Admin-only sections */}
      {isAdmin && (
        <>
          {/* Statistics */}
          {statistics && (
            <div style={statsGridStyle}>
              <div style={statCardStyle}>
                <span style={statValueStyle}>{statistics.total_requests || 0}</span>
                <span style={statLabelStyle}>Total Requests</span>
              </div>
              <div style={statCardStyle}>
                <span style={statValueStyle}>{statistics.blocked_requests || 0}</span>
                <span style={statLabelStyle}>Blocked</span>
              </div>
              <div style={statCardStyle}>
                <span style={statValueStyle}>{statistics.unique_users || 0}</span>
                <span style={statLabelStyle}>Unique Users</span>
              </div>
              <div style={statCardStyle}>
                <span style={statValueStyle}>{statistics.blocked_ips || 0}</span>
                <span style={statLabelStyle}>Blocked IPs</span>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div style={tabsStyle}>
            <button
              onClick={() => setActiveTab('overview')}
              style={activeTab === 'overview' ? tabActiveStyle : tabStyle}
            >
              📊 Overview
            </button>
            <button
              onClick={() => setActiveTab('violations')}
              style={activeTab === 'violations' ? tabActiveStyle : tabStyle}
            >
              ⚠️ Violations ({violations.length})
            </button>
            <button
              onClick={() => setActiveTab('users')}
              style={activeTab === 'users' ? tabActiveStyle : tabStyle}
            >
              👥 Top Users
            </button>
            <button
              onClick={() => setActiveTab('endpoints')}
              style={activeTab === 'endpoints' ? tabActiveStyle : tabStyle}
            >
              🔗 Top Endpoints
            </button>
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div style={tabContentStyle}>
              <div style={overviewGridStyle}>
                {/* Status Card */}
                <div style={overviewCardStyle}>
                  <h4>Status</h4>
                  <div style={statusDisplayStyle}>
                    <span style={status?.enabled ? statusEnabledStyle : statusDisabledStyle}>
                      {status?.enabled ? '✓ Enabled' : '✗ Disabled'}
                    </span>
                  </div>
                  {status?.mode && (
                    <p style={modeTextStyle}>Mode: {status.mode}</p>
                  )}
                </div>

                {/* Tier Limits Card */}
                <div style={overviewCardStyle}>
                  <h4>Tier Limits</h4>
                  <div style={tierListStyle}>
                    <div style={tierItemStyle}>
                      <span style={tierNameStyle}>Admin</span>
                      <span style={tierLimitStyle}>Unlimited</span>
                    </div>
                    <div style={tierItemStyle}>
                      <span style={tierNameStyle}>Instructor</span>
                      <span style={tierLimitStyle}>1000/min, 10000/hour</span>
                    </div>
                    <div style={tierItemStyle}>
                      <span style={tierNameStyle}>Trainee</span>
                      <span style={tierLimitStyle}>100/min, 1000/hour</span>
                    </div>
                    <div style={tierItemStyle}>
                      <span style={tierNameStyle}>Anonymous</span>
                      <span style={tierLimitStyle}>10/min, 100/hour</span>
                    </div>
                  </div>
                </div>

                {/* Quick Actions Card */}
                <div style={overviewCardStyle}>
                  <h4>Quick Actions</h4>
                  <div style={quickActionsStyle}>
                    <button onClick={() => setShowBlockUserForm(true)} style={actionButtonStyle}>
                      🚫 Block User
                    </button>
                    <button onClick={handleResetStatistics} style={actionButtonSecondaryStyle}>
                      🔄 Reset Statistics
                    </button>
                    <button onClick={loadAllData} style={actionButtonSecondaryStyle}>
                      ↻ Refresh Data
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Violations Tab */}
          {activeTab === 'violations' && (
            <div style={tabContentStyle}>
              {violations.length === 0 ? (
                <div style={emptyStateStyle}>
                  <span style={emptyIconStyle}>✓</span>
                  <p>No rate limit violations recorded.</p>
                </div>
              ) : (
                <div style={tableContainerStyle}>
                  <table style={tableStyle}>
                    <thead>
                      <tr>
                        <th style={thStyle}>User/IP</th>
                        <th style={thStyle}>Endpoint</th>
                        <th style={thStyle}>Violation Type</th>
                        <th style={thStyle}>Count</th>
                        <th style={thStyle}>Last Violation</th>
                        <th style={thStyle}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {violations.map((violation, idx) => (
                        <tr key={idx} style={trStyle}>
                          <td style={tdStyle}>{violation.user_id || violation.ip_address}</td>
                          <td style={tdStyle}>{violation.endpoint || 'All'}</td>
                          <td style={tdStyle}>
                            <span style={violationTypeBadgeStyle}>
                              {violation.violation_type || 'rate_exceeded'}
                            </span>
                          </td>
                          <td style={tdStyle}>{violation.count || 1}</td>
                          <td style={tdStyle}>{formatDate(violation.last_violation_at)}</td>
                          <td style={tdStyle}>
                            <div style={actionButtonsStyle}>
                              <button
                                onClick={() => handleViewUserDetails(violation.user_id)}
                                style={smallButtonStyle}
                              >
                                View
                              </button>
                              <button
                                onClick={() => handleUnblockUser(violation.user_id)}
                                style={{ ...smallButtonStyle, backgroundColor: '#28a745' }}
                              >
                                Unblock
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Top Users Tab */}
          {activeTab === 'users' && (
            <div style={tabContentStyle}>
              {topUsers.length === 0 ? (
                <div style={emptyStateStyle}>
                  <span style={emptyIconStyle}>👥</span>
                  <p>No user activity recorded yet.</p>
                </div>
              ) : (
                <div style={leaderboardStyle}>
                  {topUsers.map((user, idx) => (
                    <div key={idx} style={leaderboardItemStyle}>
                      <div style={leaderboardRankStyle}>
                        {idx + 1}
                      </div>
                      <div style={leaderboardInfoStyle}>
                        <span style={leaderboardNameStyle}>{user.user_id}</span>
                        <span style={leaderboardMetaStyle}>{user.tier || 'Unknown tier'}</span>
                      </div>
                      <div style={leaderboardStatsStyle}>
                        <span style={leaderboardRequestsStyle}>{user.total_requests || 0}</span>
                        <span style={leaderboardLabelStyle}>requests</span>
                      </div>
                      <div style={leaderboardActionsStyle}>
                        <button
                          onClick={() => handleViewUserDetails(user.user_id)}
                          style={viewDetailsButtonStyle}
                        >
                          Details
                        </button>
                        <button
                          onClick={() => handleResetUserState(user.user_id)}
                          style={resetButtonStyle}
                        >
                          Reset
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Top Endpoints Tab */}
          {activeTab === 'endpoints' && (
            <div style={tabContentStyle}>
              {topEndpoints.length === 0 ? (
                <div style={emptyStateStyle}>
                  <span style={emptyIconStyle}>🔗</span>
                  <p>No endpoint activity recorded yet.</p>
                </div>
              ) : (
                <div style={endpointListStyle}>
                  {topEndpoints.map((endpoint, idx) => (
                    <div key={idx} style={endpointItemStyle}>
                      <div style={endpointRankStyle}>{idx + 1}</div>
                      <div style={endpointInfoStyle}>
                        <span style={endpointPathStyle}>{endpoint.endpoint}</span>
                        <span style={endpointMethodStyle}>{endpoint.method || 'ALL'}</span>
                      </div>
                      <div style={endpointStatsStyle}>
                        <div style={endpointStatStyle}>
                          <span style={endpointStatValueStyle}>{endpoint.total_requests || 0}</span>
                          <span style={endpointStatLabelStyle}>Requests</span>
                        </div>
                        <div style={endpointStatStyle}>
                          <span style={endpointStatValueStyle}>{endpoint.blocked_count || 0}</span>
                          <span style={endpointStatLabelStyle}>Blocked</span>
                        </div>
                        <div style={endpointStatStyle}>
                          <span style={endpointStatValueStyle}>{endpoint.avg_latency_ms || 0}ms</span>
                          <span style={endpointStatLabelStyle}>Avg Latency</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* User Details Modal */}
          {selectedUser && (
            <div style={modalOverlayStyle}>
              <div style={modalStyle}>
                <div style={modalHeaderStyle}>
                  <h3>User Details: {selectedUser.userId}</h3>
                  <button onClick={() => setSelectedUser(null)} style={closeButtonStyle}>
                    ✕
                  </button>
                </div>
                <div style={modalBodyStyle}>
                  <div style={userDetailRowStyle}>
                    <span>Tier:</span>
                    <span style={tierBadgeStyle}>{selectedUser.tier || 'Unknown'}</span>
                  </div>
                  <div style={userDetailRowStyle}>
                    <span>Requests (minute):</span>
                    <span>{selectedUser.requests_in_minute || 0}</span>
                  </div>
                  <div style={userDetailRowStyle}>
                    <span>Requests (hour):</span>
                    <span>{selectedUser.requests_in_hour || 0}</span>
                  </div>
                  <div style={userDetailRowStyle}>
                    <span>Requests (day):</span>
                    <span>{selectedUser.requests_in_day || 0}</span>
                  </div>
                  <div style={userDetailRowStyle}>
                    <span>Is Blocked:</span>
                    <span style={selectedUser.is_blocked ? blockedBadgeStyle : unblockedBadgeStyle}>
                      {selectedUser.is_blocked ? 'Yes' : 'No'}
                    </span>
                  </div>
                  {selectedUser.blocked_until && (
                    <div style={userDetailRowStyle}>
                      <span>Blocked Until:</span>
                      <span>{formatDate(selectedUser.blocked_until)}</span>
                    </div>
                  )}
                  <div style={userDetailRowStyle}>
                    <span>Last Request:</span>
                    <span>{formatDate(selectedUser.last_request_at)}</span>
                  </div>
                </div>
                <div style={modalActionsStyle}>
                  {selectedUser.is_blocked ? (
                    <button
                      onClick={() => {
                        handleUnblockUser(selectedUser.userId);
                        setSelectedUser(null);
                      }}
                      style={unblockButtonStyle}
                    >
                      Unblock User
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setBlockForm({ userId: selectedUser.userId, duration: 60 });
                        setSelectedUser(null);
                        setShowBlockUserForm(true);
                      }}
                      style={blockButtonStyle}
                    >
                      Block User
                    </button>
                  )}
                  <button
                    onClick={() => {
                      handleResetUserState(selectedUser.userId);
                      setSelectedUser(null);
                    }}
                    style={resetUserButtonStyle}
                  >
                    Reset Rate Limit
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Block User Modal */}
          {showBlockUserForm && (
            <div style={modalOverlayStyle}>
              <div style={modalStyle}>
                <div style={modalHeaderStyle}>
                  <h3>Block User</h3>
                  <button onClick={() => setShowBlockUserForm(false)} style={closeButtonStyle}>
                    ✕
                  </button>
                </div>
                <form onSubmit={handleBlockUser} style={formStyle}>
                  <div style={formGroupStyle}>
                    <label style={labelStyle}>User ID *</label>
                    <input
                      type="text"
                      value={blockForm.userId}
                      onChange={(e) => setBlockForm((prev) => ({ ...prev, userId: e.target.value }))}
                      style={inputStyle}
                      placeholder="Username or IP address"
                      required
                    />
                  </div>
                  <div style={formGroupStyle}>
                    <label style={labelStyle}>Duration (minutes) *</label>
                    <input
                      type="number"
                      value={blockForm.duration}
                      onChange={(e) => setBlockForm((prev) => ({ ...prev, duration: e.target.value }))}
                      style={inputStyle}
                      min="1"
                      max="10080"
                      required
                    />
                    <small style={helpTextStyle}>Max: 10080 minutes (7 days)</small>
                  </div>
                  <div style={formActionsStyle}>
                    <button type="button" onClick={() => setShowBlockUserForm(false)} style={secondaryButtonStyle}>
                      Cancel
                    </button>
                    <button type="submit" style={dangerButtonStyle}>
                      Block User
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </>
      )}

      {/* Non-admin message */}
      {!isAdmin && (
        <div style={nonAdminInfoStyle}>
          <p>Advanced rate limit management requires administrator privileges.</p>
          <p>Your current rate limits are shown above.</p>
        </div>
      )}
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
};

const myStatusCardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  marginBottom: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const myStatusGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: '16px',
  marginTop: '12px',
};

const myStatusItemStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

const myStatusLabelStyle = {
  fontSize: '12px',
  color: '#666',
};

const tierBadgeStyle = {
  display: 'inline-block',
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '12px',
  fontWeight: 'bold',
  backgroundColor: '#007bff',
  color: 'white',
  textTransform: 'uppercase',
};

const statsGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(4, 1fr)',
  gap: '16px',
  marginBottom: '20px',
};

const statCardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  textAlign: 'center',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const statValueStyle = {
  display: 'block',
  fontSize: '24px',
  fontWeight: 'bold',
  color: '#007bff',
};

const statLabelStyle = {
  display: 'block',
  fontSize: '12px',
  color: '#666',
  marginTop: '4px',
};

const tabsStyle = {
  display: 'flex',
  gap: '8px',
  marginBottom: '20px',
};

const tabStyle = {
  padding: '8px 16px',
  backgroundColor: '#e9ecef',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const tabActiveStyle = {
  ...tabStyle,
  backgroundColor: '#007bff',
  color: 'white',
};

const tabContentStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  padding: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const overviewGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '20px',
};

const overviewCardStyle = {
  backgroundColor: '#f8f9fa',
  padding: '16px',
  borderRadius: '8px',
};

const statusDisplayStyle = {
  textAlign: 'center',
  padding: '20px',
};

const statusEnabledStyle = {
  fontSize: '18px',
  fontWeight: 'bold',
  color: '#28a745',
};

const statusDisabledStyle = {
  fontSize: '18px',
  fontWeight: 'bold',
  color: '#dc3545',
};

const modeTextStyle = {
  textAlign: 'center',
  color: '#666',
  fontSize: '13px',
  marginTop: '8px',
};

const tierListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  marginTop: '12px',
};

const tierItemStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '8px',
  backgroundColor: 'white',
  borderRadius: '4px',
  fontSize: '13px',
};

const tierNameStyle = {
  fontWeight: '500',
};

const tierLimitStyle = {
  color: '#666',
};

const quickActionsStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  marginTop: '12px',
};

const actionButtonStyle = {
  padding: '10px 16px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const actionButtonSecondaryStyle = {
  ...actionButtonStyle,
  backgroundColor: '#6c757d',
};

const emptyStateStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '60px',
  color: '#666',
};

const emptyIconStyle = {
  fontSize: '64px',
  marginBottom: '16px',
};

const tableContainerStyle = {
  overflowX: 'auto',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const thStyle = {
  textAlign: 'left',
  padding: '12px',
  borderBottom: '2px solid #e9ecef',
  fontSize: '13px',
  fontWeight: '600',
  color: '#333',
};

const trStyle = {
  borderBottom: '1px solid #e9ecef',
};

const tdStyle = {
  padding: '12px',
  fontSize: '13px',
};

const violationTypeBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  backgroundColor: '#dc3545',
  color: 'white',
};

const actionButtonsStyle = {
  display: 'flex',
  gap: '4px',
};

const smallButtonStyle = {
  padding: '4px 8px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '11px',
};

const leaderboardStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const leaderboardItemStyle = {
  display: 'flex',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  gap: '16px',
};

const leaderboardRankStyle = {
  width: '32px',
  height: '32px',
  borderRadius: '50%',
  backgroundColor: '#007bff',
  color: 'white',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 'bold',
};

const leaderboardInfoStyle = {
  flex: 1,
};

const leaderboardNameStyle = {
  display: 'block',
  fontWeight: '500',
  fontSize: '14px',
};

const leaderboardMetaStyle = {
  display: 'block',
  fontSize: '12px',
  color: '#666',
};

const leaderboardStatsStyle = {
  textAlign: 'right',
};

const leaderboardRequestsStyle = {
  display: 'block',
  fontSize: '18px',
  fontWeight: 'bold',
  color: '#007bff',
};

const leaderboardLabelStyle = {
  display: 'block',
  fontSize: '11px',
  color: '#666',
};

const leaderboardActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const viewDetailsButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const resetButtonStyle = {
  ...viewDetailsButtonStyle,
  backgroundColor: '#6c757d',
};

const endpointListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const endpointItemStyle = {
  display: 'flex',
  alignItems: 'center',
  padding: '16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  gap: '16px',
};

const endpointRankStyle = {
  width: '28px',
  height: '28px',
  borderRadius: '50%',
  backgroundColor: '#28a745',
  color: 'white',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 'bold',
  fontSize: '12px',
};

const endpointInfoStyle = {
  flex: 1,
};

const endpointPathStyle = {
  display: 'block',
  fontWeight: '500',
  fontSize: '14px',
  fontFamily: 'monospace',
};

const endpointMethodStyle = {
  display: 'inline-block',
  padding: '2px 6px',
  backgroundColor: '#007bff',
  color: 'white',
  borderRadius: '4px',
  fontSize: '10px',
  fontWeight: 'bold',
  marginTop: '4px',
};

const endpointStatsStyle = {
  display: 'flex',
  gap: '24px',
};

const endpointStatStyle = {
  textAlign: 'center',
};

const endpointStatValueStyle = {
  display: 'block',
  fontSize: '16px',
  fontWeight: 'bold',
};

const endpointStatLabelStyle = {
  display: 'block',
  fontSize: '10px',
  color: '#666',
};

const nonAdminInfoStyle = {
  textAlign: 'center',
  padding: '40px',
  color: '#666',
};

const successMessageStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#d4edda',
  color: '#155724',
  borderRadius: '4px',
  marginBottom: '16px',
  fontSize: '14px',
};

const errorMessageStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#f8d7da',
  color: '#721c24',
  borderRadius: '4px',
  marginBottom: '16px',
  fontSize: '14px',
};

const dismissButtonStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  cursor: 'pointer',
  fontSize: '16px',
  padding: '0 4px',
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

const enableButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
};

const disableButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#ffc107',
  color: '#333',
};

const secondaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#6c757d',
};

const dangerButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#dc3545',
};

// Modal styles
const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modalStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  width: '90%',
  maxWidth: '450px',
  maxHeight: '90vh',
  overflow: 'auto',
};

const modalHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px',
  borderBottom: '1px solid #eee',
};

const closeButtonStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  color: '#666',
};

const modalBodyStyle = {
  padding: '16px',
};

const userDetailRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '8px 0',
  borderBottom: '1px solid #eee',
  fontSize: '14px',
};

const blockedBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#dc3545',
  color: 'white',
};

const unblockedBadgeStyle = {
  ...blockedBadgeStyle,
  backgroundColor: '#28a745',
};

const modalActionsStyle = {
  display: 'flex',
  gap: '8px',
  padding: '16px',
  borderTop: '1px solid #eee',
  justifyContent: 'flex-end',
};

const unblockButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const blockButtonStyle = {
  ...unblockButtonStyle,
  backgroundColor: '#dc3545',
};

const resetUserButtonStyle = {
  ...unblockButtonStyle,
  backgroundColor: '#6c757d',
};

const formStyle = {
  padding: '16px',
};

const formGroupStyle = {
  marginBottom: '16px',
};

const labelStyle = {
  display: 'block',
  marginBottom: '4px',
  fontWeight: '500',
  fontSize: '13px',
  color: '#333',
};

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
  boxSizing: 'border-box',
};

const helpTextStyle = {
  display: 'block',
  marginTop: '4px',
  fontSize: '11px',
  color: '#666',
};

const formActionsStyle = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '8px',
  marginTop: '16px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
};
