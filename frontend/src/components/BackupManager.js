import React, { useState, useEffect, useCallback } from 'react';
import { backupApi } from '../api';

/**
 * Backup Management Dashboard component.
 * Provides UI for backup creation, restore, scheduling, and disaster recovery.
 */
export default function BackupManager({ user }) {
  const [backups, setBackups] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('backups');
  const [showCreateBackupForm, setShowCreateBackupForm] = useState(false);
  const [showCreateScheduleForm, setShowCreateScheduleForm] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState(null);

  const isAdmin = user?.role === 'admin';

  // Form states
  const [backupForm, setBackupForm] = useState({
    backup_type: 'full',
    description: '',
    tags: '',
    retention_days: 30,
  });

  const [scheduleForm, setScheduleForm] = useState({
    backup_type: 'full',
    frequency: 'daily',
    time_of_day: '02:00',
    day_of_week: 0,
    day_of_month: 1,
    retention_days: 30,
    max_backups: 10,
  });

  // Fetch backups
  const fetchBackups = useCallback(async () => {
    try {
      const response = await backupApi.listBackups();
      setBackups(response.data || []);
    } catch (err) {
      console.error('Failed to load backups:', err);
    }
  }, []);

  // Fetch schedules
  const fetchSchedules = useCallback(async () => {
    try {
      const response = await backupApi.listSchedules();
      setSchedules(response.data || []);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    }
  }, []);

  // Fetch snapshots
  const fetchSnapshots = useCallback(async () => {
    try {
      const response = await backupApi.listSnapshots();
      setSnapshots(response.data || []);
    } catch (err) {
      console.error('Failed to load snapshots:', err);
    }
  }, []);

  // Fetch statistics
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await backupApi.getStatistics();
      setStatistics(response.data);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  }, []);

  // Load all data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchBackups(),
        fetchSchedules(),
        fetchSnapshots(),
        fetchStatistics(),
      ]);
    } catch (err) {
      setError('Failed to load backup data');
    } finally {
      setLoading(false);
    }
  }, [fetchBackups, fetchSchedules, fetchSnapshots, fetchStatistics]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Create backup
  const handleCreateBackup = async (e) => {
    e.preventDefault();
    try {
      const tags = backupForm.tags ? backupForm.tags.split(',').map(t => t.trim()) : [];
      await backupApi.createBackup(
        backupForm.backup_type,
        backupForm.description,
        tags,
        parseInt(backupForm.retention_days)
      );
      setShowCreateBackupForm(false);
      setBackupForm({
        backup_type: 'full',
        description: '',
        tags: '',
        retention_days: 30,
      });
      setSuccessMessage('Backup created successfully');
      fetchBackups();
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create backup: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Verify backup
  const handleVerifyBackup = async (backupId) => {
    try {
      const response = await backupApi.verifyBackup(backupId);
      if (response.data.valid) {
        setSuccessMessage('Backup verified successfully');
      } else {
        setActionError('Backup verification failed: ' + (response.data.error || 'Unknown error'));
      }
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to verify backup');
    }
  };

  // Restore backup
  const handleRestoreBackup = async (backupId) => {
    if (!window.confirm('Are you sure you want to restore from this backup?\n\n⚠️ WARNING: This action cannot be undone. Current data will be overwritten and active lab sessions may be affected.')) {
      return;
    }
    try {
      await backupApi.restoreBackup(backupId);
      setSuccessMessage('Restore completed successfully');
      loadAllData();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to restore backup: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Delete backup
  const handleDeleteBackup = async (backupId) => {
    if (!window.confirm('Are you sure you want to delete this backup?')) return;
    try {
      await backupApi.deleteBackup(backupId);
      setSuccessMessage('Backup deleted');
      fetchBackups();
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete backup');
    }
  };

  // Export backup
  const handleExportBackup = async (backupId, format = 'json') => {
    try {
      const response = await backupApi.exportBackup(backupId, format);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `backup_${backupId}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setActionError('Failed to export backup');
    }
  };

  // Create schedule
  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    try {
      await backupApi.createSchedule(
        scheduleForm.backup_type,
        scheduleForm.frequency,
        scheduleForm.time_of_day,
        scheduleForm.frequency === 'weekly' ? parseInt(scheduleForm.day_of_week) : null,
        scheduleForm.frequency === 'monthly' ? parseInt(scheduleForm.day_of_month) : null,
        parseInt(scheduleForm.retention_days),
        parseInt(scheduleForm.max_backups)
      );
      setShowCreateScheduleForm(false);
      setScheduleForm({
        backup_type: 'full',
        frequency: 'daily',
        time_of_day: '02:00',
        day_of_week: 0,
        day_of_month: 1,
        retention_days: 30,
        max_backups: 10,
      });
      setSuccessMessage('Schedule created successfully');
      fetchSchedules();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create schedule: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Delete schedule
  const handleDeleteSchedule = async (scheduleId) => {
    if (!window.confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await backupApi.deleteSchedule(scheduleId);
      setSuccessMessage('Schedule deleted');
      fetchSchedules();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete schedule');
    }
  };

  // Cleanup expired backups
  const handleCleanupExpired = async () => {
    try {
      const response = await backupApi.cleanupExpired();
      setSuccessMessage(`Cleaned up ${response.data.removed_count} expired backups`);
      fetchBackups();
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to cleanup expired backups');
    }
  };

  // Delete snapshot
  const handleDeleteSnapshot = async (snapshotId) => {
    if (!window.confirm('Are you sure you want to delete this snapshot?')) return;
    try {
      await backupApi.deleteSnapshot(snapshotId);
      setSuccessMessage('Snapshot deleted');
      fetchSnapshots();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete snapshot');
    }
  };

  // Restore snapshot
  const handleRestoreSnapshot = async (snapshotId) => {
    if (!window.confirm('Are you sure you want to restore from this snapshot?')) return;
    try {
      await backupApi.restoreSnapshot(snapshotId);
      setSuccessMessage('Snapshot restored');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to restore snapshot');
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  // Format size
  const formatSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Get status color
  const getStatusColor = (status) => {
    const colors = {
      completed: '#28a745',
      pending: '#ffc107',
      failed: '#dc3545',
      verified: '#17a2b8',
    };
    return colors[status] || '#6c757d';
  };

  // Get backup type color
  const getTypeColor = (type) => {
    const colors = {
      full: '#007bff',
      scenarios: '#28a745',
      config: '#ffc107',
      users: '#17a2b8',
    };
    return colors[type] || '#6c757d';
  };

  if (loading) {
    return <div style={containerStyle}>Loading backup manager...</div>;
  }

  if (!isAdmin) {
    return (
      <div style={containerStyle}>
        <div style={accessDeniedStyle}>
          <span style={accessDeniedIconStyle}>🔒</span>
          <p>Backup management requires administrator privileges.</p>
        </div>
      </div>
    );
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
        <h2>💾 Backup & Disaster Recovery</h2>
        <div style={headerActionsStyle}>
          <button onClick={handleCleanupExpired} style={secondaryButtonStyle}>
            🧹 Cleanup Expired
          </button>
          <button onClick={() => setShowCreateBackupForm(true)} style={primaryButtonStyle}>
            + Create Backup
          </button>
        </div>
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

      {/* Statistics */}
      {statistics && (
        <div style={statsGridStyle}>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_backups || 0}</span>
            <span style={statLabelStyle}>Total Backups</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{formatSize(statistics.total_size_bytes)}</span>
            <span style={statLabelStyle}>Total Size</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.completed_backups || 0}</span>
            <span style={statLabelStyle}>Completed</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.active_schedules || 0}</span>
            <span style={statLabelStyle}>Active Schedules</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('backups')}
          style={activeTab === 'backups' ? tabActiveStyle : tabStyle}
        >
          💾 Backups ({backups.length})
        </button>
        <button
          onClick={() => setActiveTab('schedules')}
          style={activeTab === 'schedules' ? tabActiveStyle : tabStyle}
        >
          📅 Schedules ({schedules.length})
        </button>
        <button
          onClick={() => setActiveTab('snapshots')}
          style={activeTab === 'snapshots' ? tabActiveStyle : tabStyle}
        >
          📸 Lab Snapshots ({snapshots.length})
        </button>
      </div>

      {/* Backups Tab */}
      {activeTab === 'backups' && (
        <div style={tabContentStyle}>
          {backups.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>💾</span>
              <p>No backups found. Create your first backup to protect your data.</p>
            </div>
          ) : (
            <div style={tableContainerStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Type</th>
                    <th style={thStyle}>Description</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>Size</th>
                    <th style={thStyle}>Created</th>
                    <th style={thStyle}>Expires</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {backups.map((backup) => (
                    <tr key={backup.backup_id} style={trStyle}>
                      <td style={tdStyle}>
                        <span style={{ ...typeBadgeStyle, backgroundColor: getTypeColor(backup.backup_type) }}>
                          {backup.backup_type}
                        </span>
                      </td>
                      <td style={tdStyle}>{backup.description || '-'}</td>
                      <td style={tdStyle}>
                        <span style={{ ...statusBadgeStyle, backgroundColor: getStatusColor(backup.status) }}>
                          {backup.status}
                        </span>
                      </td>
                      <td style={tdStyle}>{formatSize(backup.size_bytes)}</td>
                      <td style={tdStyle}>{formatDate(backup.created_at)}</td>
                      <td style={tdStyle}>{formatDate(backup.expires_at)}</td>
                      <td style={tdStyle}>
                        <div style={actionButtonsStyle}>
                          <button
                            onClick={() => handleVerifyBackup(backup.backup_id)}
                            style={actionBtnStyle}
                            title="Verify"
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => handleRestoreBackup(backup.backup_id)}
                            style={{ ...actionBtnStyle, backgroundColor: '#28a745' }}
                            title="Restore"
                          >
                            ↻
                          </button>
                          <button
                            onClick={() => handleExportBackup(backup.backup_id)}
                            style={{ ...actionBtnStyle, backgroundColor: '#17a2b8' }}
                            title="Export"
                          >
                            ↓
                          </button>
                          <button
                            onClick={() => handleDeleteBackup(backup.backup_id)}
                            style={{ ...actionBtnStyle, backgroundColor: '#dc3545' }}
                            title="Delete"
                          >
                            ×
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

      {/* Schedules Tab */}
      {activeTab === 'schedules' && (
        <div style={tabContentStyle}>
          <div style={tabHeaderStyle}>
            <h4>Backup Schedules</h4>
            <button onClick={() => setShowCreateScheduleForm(true)} style={addButtonStyle}>
              + Add Schedule
            </button>
          </div>
          
          {schedules.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>📅</span>
              <p>No backup schedules configured. Set up automated backups.</p>
            </div>
          ) : (
            <div style={scheduleGridStyle}>
              {schedules.map((schedule) => (
                <div key={schedule.schedule_id} style={scheduleCardStyle}>
                  <div style={scheduleHeaderStyle}>
                    <span style={{ ...typeBadgeStyle, backgroundColor: getTypeColor(schedule.backup_type) }}>
                      {schedule.backup_type}
                    </span>
                    <span style={schedule.enabled ? enabledBadgeStyle : disabledBadgeStyle}>
                      {schedule.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div style={scheduleBodyStyle}>
                    <div style={scheduleDetailStyle}>
                      <span>Frequency:</span>
                      <strong>{schedule.frequency}</strong>
                    </div>
                    <div style={scheduleDetailStyle}>
                      <span>Time:</span>
                      <strong>{schedule.time_of_day}</strong>
                    </div>
                    <div style={scheduleDetailStyle}>
                      <span>Retention:</span>
                      <strong>{schedule.retention_days} days</strong>
                    </div>
                    <div style={scheduleDetailStyle}>
                      <span>Max Backups:</span>
                      <strong>{schedule.max_backups}</strong>
                    </div>
                    {schedule.last_run_at && (
                      <div style={scheduleDetailStyle}>
                        <span>Last Run:</span>
                        <strong>{formatDate(schedule.last_run_at)}</strong>
                      </div>
                    )}
                    {schedule.next_run_at && (
                      <div style={scheduleDetailStyle}>
                        <span>Next Run:</span>
                        <strong>{formatDate(schedule.next_run_at)}</strong>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteSchedule(schedule.schedule_id)}
                    style={deleteScheduleButtonStyle}
                  >
                    Delete Schedule
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Snapshots Tab */}
      {activeTab === 'snapshots' && (
        <div style={tabContentStyle}>
          {snapshots.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>📸</span>
              <p>No lab snapshots found. Snapshots are created during lab operations.</p>
            </div>
          ) : (
            <div style={snapshotGridStyle}>
              {snapshots.map((snapshot) => (
                <div key={snapshot.snapshot_id} style={snapshotCardStyle}>
                  <div style={snapshotHeaderStyle}>
                    <span style={snapshotLabIdStyle}>Lab: {snapshot.lab_id?.substring(0, 8)}...</span>
                    <span style={snapshotStatusBadgeStyle}>{snapshot.status}</span>
                  </div>
                  <div style={snapshotBodyStyle}>
                    <div style={snapshotDetailStyle}>
                      <span>Scenario:</span>
                      <strong>{snapshot.scenario_id?.substring(0, 8)}...</strong>
                    </div>
                    <div style={snapshotDetailStyle}>
                      <span>Containers:</span>
                      <strong>{snapshot.containers?.length || 0}</strong>
                    </div>
                    <div style={snapshotDetailStyle}>
                      <span>Networks:</span>
                      <strong>{snapshot.networks?.length || 0}</strong>
                    </div>
                    <div style={snapshotDetailStyle}>
                      <span>Created:</span>
                      <strong>{formatDate(snapshot.created_at)}</strong>
                    </div>
                    {snapshot.notes && (
                      <p style={snapshotNotesStyle}>{snapshot.notes}</p>
                    )}
                  </div>
                  <div style={snapshotActionsStyle}>
                    <button
                      onClick={() => handleRestoreSnapshot(snapshot.snapshot_id)}
                      style={restoreSnapshotButtonStyle}
                    >
                      Restore
                    </button>
                    <button
                      onClick={() => handleDeleteSnapshot(snapshot.snapshot_id)}
                      style={deleteSnapshotButtonStyle}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Backup Modal */}
      {showCreateBackupForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Create New Backup</h3>
              <button onClick={() => setShowCreateBackupForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateBackup} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Backup Type *</label>
                <select
                  value={backupForm.backup_type}
                  onChange={(e) => setBackupForm((prev) => ({ ...prev, backup_type: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="full">Full Backup</option>
                  <option value="scenarios">Scenarios Only</option>
                  <option value="config">Configuration Only</option>
                  <option value="users">Users Only</option>
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description</label>
                <textarea
                  value={backupForm.description}
                  onChange={(e) => setBackupForm((prev) => ({ ...prev, description: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="Optional description for this backup..."
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={backupForm.tags}
                  onChange={(e) => setBackupForm((prev) => ({ ...prev, tags: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., production, pre-update, weekly"
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Retention (days) *</label>
                <input
                  type="number"
                  value={backupForm.retention_days}
                  onChange={(e) => setBackupForm((prev) => ({ ...prev, retention_days: e.target.value }))}
                  style={inputStyle}
                  min="1"
                  max="365"
                  required
                />
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowCreateBackupForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Backup
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Schedule Modal */}
      {showCreateScheduleForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Create Backup Schedule</h3>
              <button onClick={() => setShowCreateScheduleForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateSchedule} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Backup Type *</label>
                <select
                  value={scheduleForm.backup_type}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, backup_type: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="full">Full Backup</option>
                  <option value="scenarios">Scenarios Only</option>
                  <option value="config">Configuration Only</option>
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Frequency *</label>
                <select
                  value={scheduleForm.frequency}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, frequency: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Time of Day *</label>
                <input
                  type="time"
                  value={scheduleForm.time_of_day}
                  onChange={(e) => setScheduleForm((prev) => ({ ...prev, time_of_day: e.target.value }))}
                  style={inputStyle}
                  required
                />
              </div>
              {scheduleForm.frequency === 'weekly' && (
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Day of Week *</label>
                  <select
                    value={scheduleForm.day_of_week}
                    onChange={(e) => setScheduleForm((prev) => ({ ...prev, day_of_week: e.target.value }))}
                    style={inputStyle}
                  >
                    <option value="0">Sunday</option>
                    <option value="1">Monday</option>
                    <option value="2">Tuesday</option>
                    <option value="3">Wednesday</option>
                    <option value="4">Thursday</option>
                    <option value="5">Friday</option>
                    <option value="6">Saturday</option>
                  </select>
                </div>
              )}
              {scheduleForm.frequency === 'monthly' && (
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Day of Month *</label>
                  <input
                    type="number"
                    value={scheduleForm.day_of_month}
                    onChange={(e) => setScheduleForm((prev) => ({ ...prev, day_of_month: e.target.value }))}
                    style={inputStyle}
                    min="1"
                    max="28"
                  />
                </div>
              )}
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Retention (days) *</label>
                  <input
                    type="number"
                    value={scheduleForm.retention_days}
                    onChange={(e) => setScheduleForm((prev) => ({ ...prev, retention_days: e.target.value }))}
                    style={inputStyle}
                    min="1"
                    max="365"
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Max Backups *</label>
                  <input
                    type="number"
                    value={scheduleForm.max_backups}
                    onChange={(e) => setScheduleForm((prev) => ({ ...prev, max_backups: e.target.value }))}
                    style={inputStyle}
                    min="1"
                    max="100"
                    required
                  />
                </div>
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowCreateScheduleForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Schedule
                </button>
              </div>
            </form>
          </div>
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

const headerActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const accessDeniedStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '60px',
  color: '#666',
};

const accessDeniedIconStyle = {
  fontSize: '64px',
  marginBottom: '16px',
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

const tabHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px',
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

const typeBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
  textTransform: 'uppercase',
};

const statusBadgeStyle = {
  ...typeBadgeStyle,
};

const actionButtonsStyle = {
  display: 'flex',
  gap: '4px',
};

const actionBtnStyle = {
  width: '28px',
  height: '28px',
  border: 'none',
  borderRadius: '4px',
  backgroundColor: '#007bff',
  color: 'white',
  cursor: 'pointer',
  fontSize: '14px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const scheduleGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '16px',
};

const scheduleCardStyle = {
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  padding: '16px',
  border: '1px solid #e9ecef',
};

const scheduleHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const scheduleBodyStyle = {
  marginBottom: '12px',
};

const scheduleDetailStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  marginBottom: '4px',
  color: '#666',
};

const enabledBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#28a745',
  color: 'white',
};

const disabledBadgeStyle = {
  ...enabledBadgeStyle,
  backgroundColor: '#6c757d',
};

const deleteScheduleButtonStyle = {
  width: '100%',
  padding: '8px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const snapshotGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '16px',
};

const snapshotCardStyle = {
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  padding: '16px',
  border: '1px solid #e9ecef',
};

const snapshotHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const snapshotLabIdStyle = {
  fontWeight: '500',
  fontSize: '13px',
};

const snapshotStatusBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#17a2b8',
  color: 'white',
};

const snapshotBodyStyle = {
  marginBottom: '12px',
};

const snapshotDetailStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  marginBottom: '4px',
  color: '#666',
};

const snapshotNotesStyle = {
  fontSize: '12px',
  color: '#666',
  fontStyle: 'italic',
  marginTop: '8px',
  marginBottom: 0,
};

const snapshotActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const restoreSnapshotButtonStyle = {
  flex: 1,
  padding: '8px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const deleteSnapshotButtonStyle = {
  flex: 1,
  padding: '8px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
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

const primaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
};

const secondaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#6c757d',
};

const addButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#17a2b8',
  padding: '6px 12px',
  fontSize: '13px',
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
  maxWidth: '500px',
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

const formStyle = {
  padding: '16px',
};

const formGroupStyle = {
  marginBottom: '16px',
  flex: 1,
};

const formRowStyle = {
  display: 'flex',
  gap: '16px',
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

const formActionsStyle = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '8px',
  marginTop: '16px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
};
