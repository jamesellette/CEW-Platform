import React, { useState, useEffect, useCallback } from 'react';
import { recordingApi } from '../api';
import SessionPlayback from './SessionPlayback';

/**
 * RecordingsList component displays all recorded training sessions.
 * Allows instructors to browse, filter, and play back recordings for review.
 */
export default function RecordingsList({ user }) {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [filterUser, setFilterUser] = useState('');
  const [filterScenario, setFilterScenario] = useState('');

  const fetchRecordings = useCallback(async () => {
    try {
      setLoading(true);
      const response = await recordingApi.list();
      setRecordings(response.data.recordings || []);
      setError(null);
    } catch (err) {
      setError('Failed to load recordings');
      console.error('Recordings load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecordings();
  }, [fetchRecordings]);

  const handlePlayback = (recording) => {
    setSelectedRecording(recording);
  };

  const handleClosePlayback = () => {
    setSelectedRecording(null);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStateColor = (state) => {
    const colors = {
      completed: '#28a745',
      recording: '#ffc107',
      paused: '#17a2b8',
      stopped: '#6c757d',
    };
    return colors[state] || '#6c757d';
  };

  // Filter recordings
  const filteredRecordings = recordings.filter(recording => {
    const matchesUser = !filterUser || 
      (recording.username && recording.username.toLowerCase().includes(filterUser.toLowerCase()));
    const matchesScenario = !filterScenario || 
      (recording.scenario_name && recording.scenario_name.toLowerCase().includes(filterScenario.toLowerCase()));
    return matchesUser && matchesScenario;
  });

  // Show playback view if a recording is selected
  if (selectedRecording) {
    return (
      <SessionPlayback
        sessionId={selectedRecording.session_id}
        onClose={handleClosePlayback}
      />
    );
  }

  if (loading) {
    return <div style={containerStyle}>Loading recordings...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={fetchRecordings} style={buttonStyle}>Retry</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>📼 Session Recordings</h2>
        <button onClick={fetchRecordings} style={refreshButtonStyle}>
          ⟳ Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={filtersStyle}>
        <div style={filterGroupStyle}>
          <label style={filterLabelStyle}>Filter by User:</label>
          <input
            type="text"
            placeholder="Username..."
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
            style={filterInputStyle}
          />
        </div>
        <div style={filterGroupStyle}>
          <label style={filterLabelStyle}>Filter by Scenario:</label>
          <input
            type="text"
            placeholder="Scenario name..."
            value={filterScenario}
            onChange={(e) => setFilterScenario(e.target.value)}
            style={filterInputStyle}
          />
        </div>
        {(filterUser || filterScenario) && (
          <button
            onClick={() => { setFilterUser(''); setFilterScenario(''); }}
            style={clearFilterStyle}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Summary */}
      <div style={summaryStyle}>
        Showing {filteredRecordings.length} of {recordings.length} recordings
      </div>

      {/* Recordings List */}
      {filteredRecordings.length === 0 ? (
        <div style={emptyStateStyle}>
          <p>📭 No recordings found</p>
          <p style={emptySubTextStyle}>
            {recordings.length === 0 
              ? 'Training sessions will appear here once recorded.'
              : 'Try adjusting your filters.'}
          </p>
        </div>
      ) : (
        <div style={listStyle}>
          {filteredRecordings.map((recording) => (
            <div key={recording.session_id} style={recordingCardStyle}>
              <div style={cardHeaderStyle}>
                <div style={scenarioNameStyle}>
                  {recording.scenario_name || 'Unnamed Session'}
                </div>
                <span style={{ 
                  ...stateBadgeStyle, 
                  backgroundColor: getStateColor(recording.state) 
                }}>
                  {recording.state || 'unknown'}
                </span>
              </div>

              <div style={cardBodyStyle}>
                <div style={metaRowStyle}>
                  <span style={metaLabelStyle}>👤 User:</span>
                  <span style={metaValueStyle}>{recording.username || 'Unknown User'}</span>
                </div>
                <div style={metaRowStyle}>
                  <span style={metaLabelStyle}>⏱️ Duration:</span>
                  <span style={metaValueStyle}>{formatDuration(recording.duration_seconds)}</span>
                </div>
                <div style={metaRowStyle}>
                  <span style={metaLabelStyle}>📅 Started:</span>
                  <span style={metaValueStyle}>{formatDate(recording.started_at)}</span>
                </div>
                <div style={metaRowStyle}>
                  <span style={metaLabelStyle}>📝 Events:</span>
                  <span style={metaValueStyle}>{recording.event_count || 0}</span>
                </div>
              </div>

              <div style={cardFooterStyle}>
                <button
                  onClick={() => handlePlayback(recording)}
                  style={playButtonStyle}
                  disabled={!['completed', 'stopped'].includes(recording.state)}
                >
                  ▶️ Play Recording
                </button>
              </div>
            </div>
          ))}
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

const refreshButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const filtersStyle = {
  display: 'flex',
  gap: '16px',
  marginBottom: '16px',
  flexWrap: 'wrap',
  alignItems: 'flex-end',
};

const filterGroupStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

const filterLabelStyle = {
  fontSize: '12px',
  color: '#666',
  fontWeight: '500',
};

const filterInputStyle = {
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
  width: '200px',
};

const clearFilterStyle = {
  padding: '8px 12px',
  backgroundColor: '#e9ecef',
  color: '#495057',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

const summaryStyle = {
  fontSize: '13px',
  color: '#666',
  marginBottom: '16px',
};

const emptyStateStyle = {
  textAlign: 'center',
  padding: '40px',
  backgroundColor: 'white',
  borderRadius: '8px',
  color: '#666',
};

const emptySubTextStyle = {
  fontSize: '14px',
  color: '#999',
  marginTop: '8px',
};

const listStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
  gap: '16px',
};

const recordingCardStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  overflow: 'hidden',
};

const cardHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#f8f9fa',
  borderBottom: '1px solid #e9ecef',
};

const scenarioNameStyle = {
  fontWeight: '600',
  fontSize: '14px',
  color: '#333',
};

const stateBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
  textTransform: 'uppercase',
};

const cardBodyStyle = {
  padding: '16px',
};

const metaRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: '8px',
  fontSize: '13px',
};

const metaLabelStyle = {
  color: '#666',
};

const metaValueStyle = {
  color: '#333',
  fontWeight: '500',
};

const cardFooterStyle = {
  padding: '12px 16px',
  borderTop: '1px solid #e9ecef',
  display: 'flex',
  justifyContent: 'flex-end',
};

const playButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
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
