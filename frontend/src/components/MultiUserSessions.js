import React, { useState, useEffect, useCallback } from 'react';
import { sessionApi, labApi, scenarioApi } from '../api';

/**
 * MultiUserSessions component for managing collaborative training sessions.
 * Supports Red Team vs Blue Team scenarios and shared lab environments.
 */
export default function MultiUserSessions({ user }) {
  const [activeTab, setActiveTab] = useState('active');
  const [sessions, setSessions] = useState([]);
  const [mySessions, setMySessions] = useState([]);
  const [labs, setLabs] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    labId: '',
    scenarioId: '',
    sessionType: 'collaborative',
    maxParticipants: 10,
  });

  // Fetch active sessions
  const fetchSessions = useCallback(async () => {
    try {
      const response = await sessionApi.listSessions(null, true);
      setSessions(response.data.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  // Fetch my sessions
  const fetchMySessions = useCallback(async () => {
    try {
      const response = await sessionApi.getMySessions();
      setMySessions(response.data.sessions || []);
    } catch (err) {
      console.error('Failed to load my sessions:', err);
    }
  }, []);

  // Fetch labs and scenarios for dropdowns
  const fetchResources = useCallback(async () => {
    try {
      const [labsRes, scenariosRes] = await Promise.all([
        labApi.listActive(),
        scenarioApi.list()
      ]);
      setLabs(labsRes.data || []);
      setScenarios(scenariosRes.data || []);
    } catch (err) {
      console.error('Failed to load resources:', err);
    }
  }, []);

  // Load all data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchSessions(),
        fetchMySessions(),
        fetchResources()
      ]);
    } catch (err) {
      console.error('Failed to load session data:', err);
      setError('Failed to load session data');
    } finally {
      setLoading(false);
    }
  }, [fetchSessions, fetchMySessions, fetchResources]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Handle session creation
  const handleCreateSession = async (e) => {
    e.preventDefault();
    
    try {
      await sessionApi.createSession(
        formData.name,
        formData.description,
        formData.labId,
        formData.scenarioId,
        formData.sessionType,
        formData.maxParticipants
      );
      
      setShowCreateForm(false);
      resetForm();
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to create session:', err);
      setActionError('Failed to create session: ' + (err.response?.data?.detail || err.message));
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      labId: '',
      scenarioId: '',
      sessionType: 'collaborative',
      maxParticipants: 10,
    });
    setActionError(null);
  };

  // Join a session
  const handleJoinSession = async (sessionId) => {
    try {
      await sessionApi.joinSession(sessionId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to join session:', err);
      setActionError('Failed to join session. It may be full or already started.');
    }
  };

  // Leave a session
  const handleLeaveSession = async (sessionId) => {
    try {
      await sessionApi.leaveSession(sessionId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to leave session:', err);
      setActionError('Failed to leave session.');
    }
  };

  // Start a session (instructor only)
  const handleStartSession = async (sessionId) => {
    try {
      await sessionApi.startSession(sessionId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to start session:', err);
      setActionError('Failed to start session.');
    }
  };

  // End a session (instructor only)
  const handleEndSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to end this session?')) return;
    
    try {
      await sessionApi.endSession(sessionId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to end session:', err);
      setActionError('Failed to end session.');
    }
  };

  const getSessionTypeIcon = (type) => {
    const icons = {
      red_vs_blue: '⚔️',
      collaborative: '🤝',
      competitive: '🏆',
      ctf: '🚩',
    };
    return icons[type] || '👥';
  };

  const getSessionTypeLabel = (type) => {
    const labels = {
      red_vs_blue: 'Red vs Blue',
      collaborative: 'Collaborative',
      competitive: 'Competitive',
      ctf: 'Capture the Flag',
    };
    return labels[type] || type;
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#ffc107',
      active: '#28a745',
      in_progress: '#007bff',
      completed: '#6c757d',
      ended: '#6c757d',
    };
    return colors[status] || '#6c757d';
  };

  const isUserInSession = (session) => {
    return session.participants?.some(p => p.username === user?.username);
  };

  // Fetch session details
  const handleViewSession = async (sessionId) => {
    try {
      const response = await sessionApi.getSession(sessionId);
      setSelectedSession(response.data);
    } catch (err) {
      console.error('Failed to load session details:', err);
      setActionError('Failed to load session details.');
    }
  };

  if (loading) {
    return <div style={containerStyle}>Loading sessions...</div>;
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
        <h2>👥 Multi-User Sessions</h2>
        {isInstructor && (
          <button onClick={() => setShowCreateForm(true)} style={primaryButtonStyle}>
            + New Session
          </button>
        )}
      </div>

      {/* Action Error Message */}
      {actionError && (
        <div style={actionErrorStyle}>
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} style={dismissErrorStyle}>✕</button>
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('active')}
          style={activeTab === 'active' ? tabActiveStyle : tabStyle}
        >
          🟢 Active Sessions
        </button>
        <button
          onClick={() => setActiveTab('mySessions')}
          style={activeTab === 'mySessions' ? tabActiveStyle : tabStyle}
        >
          👤 My Sessions
        </button>
        <button
          onClick={() => setActiveTab('browse')}
          style={activeTab === 'browse' ? tabActiveStyle : tabStyle}
        >
          🔍 Browse All
        </button>
      </div>

      {/* Active Sessions Tab */}
      {activeTab === 'active' && (
        <div style={contentStyle}>
          <h3>Active Training Sessions</h3>
          {sessions.filter(s => s.status === 'active' || s.status === 'in_progress').length === 0 ? (
            <p style={emptyTextStyle}>No active sessions at the moment.</p>
          ) : (
            <div style={sessionListStyle}>
              {sessions.filter(s => s.status === 'active' || s.status === 'in_progress').map((session) => (
                <div key={session.session_id} style={sessionCardStyle}>
                  <div style={cardHeaderStyle}>
                    <div style={sessionTitleRowStyle}>
                      <span style={sessionTypeIconStyle}>{getSessionTypeIcon(session.session_type)}</span>
                      <span style={sessionTitleStyle}>{session.name}</span>
                    </div>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(session.status) 
                    }}>
                      {session.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={sessionMetaStyle}>
                      <span>🎯 {getSessionTypeLabel(session.session_type)}</span>
                    </div>
                    <div style={sessionMetaStyle}>
                      <span>👥 {session.participants?.length || 0} / {session.max_participants} participants</span>
                    </div>
                    <div style={sessionMetaStyle}>
                      <span>👤 Host: {session.host_username}</span>
                    </div>
                    {session.description && (
                      <p style={descriptionStyle}>{session.description}</p>
                    )}
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewSession(session.session_id)}
                      style={viewButtonStyle}
                    >
                      View Details
                    </button>
                    {!isUserInSession(session) && session.status === 'pending' && (
                      <button
                        onClick={() => handleJoinSession(session.session_id)}
                        style={joinButtonStyle}
                      >
                        Join Session
                      </button>
                    )}
                    {isUserInSession(session) && session.status === 'pending' && (
                      <button
                        onClick={() => handleLeaveSession(session.session_id)}
                        style={leaveButtonStyle}
                      >
                        Leave
                      </button>
                    )}
                    {isInstructor && session.status === 'pending' && (
                      <button
                        onClick={() => handleStartSession(session.session_id)}
                        style={startButtonStyle}
                      >
                        ▶️ Start
                      </button>
                    )}
                    {isInstructor && (session.status === 'active' || session.status === 'in_progress') && (
                      <button
                        onClick={() => handleEndSession(session.session_id)}
                        style={endButtonStyle}
                      >
                        End Session
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Sessions Tab */}
      {activeTab === 'mySessions' && (
        <div style={contentStyle}>
          <h3>Sessions I'm Participating In</h3>
          {mySessions.length === 0 ? (
            <p style={emptyTextStyle}>You haven't joined any sessions yet. Browse available sessions to join!</p>
          ) : (
            <div style={sessionListStyle}>
              {mySessions.map((session) => (
                <div key={session.session_id} style={sessionCardStyle}>
                  <div style={cardHeaderStyle}>
                    <div style={sessionTitleRowStyle}>
                      <span style={sessionTypeIconStyle}>{getSessionTypeIcon(session.session_type)}</span>
                      <span style={sessionTitleStyle}>{session.name}</span>
                    </div>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(session.status) 
                    }}>
                      {session.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={sessionMetaStyle}>
                      <span>🎯 {getSessionTypeLabel(session.session_type)}</span>
                    </div>
                    <div style={sessionMetaStyle}>
                      <span>👤 Host: {session.host_username}</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewSession(session.session_id)}
                      style={viewButtonStyle}
                    >
                      View Details
                    </button>
                    {session.status === 'pending' && (
                      <button
                        onClick={() => handleLeaveSession(session.session_id)}
                        style={leaveButtonStyle}
                      >
                        Leave Session
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Browse All Tab */}
      {activeTab === 'browse' && (
        <div style={contentStyle}>
          <h3>All Sessions</h3>
          {sessions.length === 0 ? (
            <p style={emptyTextStyle}>No sessions available.</p>
          ) : (
            <div style={sessionListStyle}>
              {sessions.map((session) => (
                <div key={session.session_id} style={sessionCardStyle}>
                  <div style={cardHeaderStyle}>
                    <div style={sessionTitleRowStyle}>
                      <span style={sessionTypeIconStyle}>{getSessionTypeIcon(session.session_type)}</span>
                      <span style={sessionTitleStyle}>{session.name}</span>
                    </div>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(session.status) 
                    }}>
                      {session.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={sessionMetaStyle}>
                      <span>🎯 {getSessionTypeLabel(session.session_type)}</span>
                    </div>
                    <div style={sessionMetaStyle}>
                      <span>👥 {session.participants?.length || 0} / {session.max_participants}</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewSession(session.session_id)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Session Modal */}
      {showCreateForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>👥 Create Multi-User Session</h3>
              <button onClick={() => setShowCreateForm(false)} style={closeButtonStyle}>✕</button>
            </div>
            <form onSubmit={handleCreateSession} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Session Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Red Team Training #1"
                  required
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Session Type *</label>
                <select
                  value={formData.sessionType}
                  onChange={(e) => setFormData(prev => ({ ...prev, sessionType: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="collaborative">🤝 Collaborative - Work together</option>
                  <option value="red_vs_blue">⚔️ Red vs Blue - Attack/Defense</option>
                  <option value="competitive">🏆 Competitive - Individual scoring</option>
                  <option value="ctf">🚩 Capture the Flag</option>
                </select>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Lab Environment</label>
                <select
                  value={formData.labId}
                  onChange={(e) => setFormData(prev => ({ ...prev, labId: e.target.value }))}
                  style={inputStyle}
                >
                  <option value="">Select a lab (optional)...</option>
                  {labs.map(lab => (
                    <option key={lab.lab_id} value={lab.lab_id}>{lab.scenario_name}</option>
                  ))}
                </select>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Scenario</label>
                <select
                  value={formData.scenarioId}
                  onChange={(e) => setFormData(prev => ({ ...prev, scenarioId: e.target.value }))}
                  style={inputStyle}
                >
                  <option value="">Select a scenario (optional)...</option>
                  {scenarios.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Max Participants</label>
                <input
                  type="number"
                  value={formData.maxParticipants}
                  onChange={(e) => setFormData(prev => ({ ...prev, maxParticipants: parseInt(e.target.value) || 10 }))}
                  style={inputStyle}
                  min="2"
                  max="50"
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="Describe the session objectives..."
                />
              </div>
              
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowCreateForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Session Detail Modal */}
      {selectedSession && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>{getSessionTypeIcon(selectedSession.session_type)} {selectedSession.name}</h3>
              <button onClick={() => setSelectedSession(null)} style={closeButtonStyle}>✕</button>
            </div>
            <div style={detailBodyStyle}>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Type:</span>
                <span>{getSessionTypeLabel(selectedSession.session_type)}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Status:</span>
                <span style={{ 
                  ...statusBadgeStyle, 
                  backgroundColor: getStatusColor(selectedSession.status) 
                }}>
                  {selectedSession.status}
                </span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Host:</span>
                <span>{selectedSession.host_username}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Capacity:</span>
                <span>{selectedSession.participants?.length || 0} / {selectedSession.max_participants}</span>
              </div>
              {selectedSession.description && (
                <div style={detailRowStyle}>
                  <span style={detailLabelStyle}>Description:</span>
                  <span>{selectedSession.description}</span>
                </div>
              )}
              
              {/* Participants List */}
              <h4 style={sectionTitleStyle}>Participants</h4>
              {selectedSession.participants?.length === 0 ? (
                <p style={emptyTextStyle}>No participants yet.</p>
              ) : (
                <div style={participantListStyle}>
                  {selectedSession.participants?.map((p, idx) => (
                    <div key={idx} style={participantItemStyle}>
                      <span style={participantNameStyle}>👤 {p.display_name || p.username}</span>
                      {p.team_role && <span style={teamRoleBadgeStyle}>{p.team_role}</span>}
                    </div>
                  ))}
                </div>
              )}

              {/* Teams (if applicable) */}
              {selectedSession.teams?.length > 0 && (
                <>
                  <h4 style={sectionTitleStyle}>Teams</h4>
                  <div style={teamListStyle}>
                    {selectedSession.teams.map((team, idx) => (
                      <div key={idx} style={{ ...teamCardStyle, borderColor: team.color }}>
                        <span style={teamNameStyle}>{team.name}</span>
                        <span style={teamScoreStyle}>Score: {team.score || 0}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
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

const actionErrorStyle = {
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

const dismissErrorStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  color: '#721c24',
  cursor: 'pointer',
  fontSize: '16px',
  padding: '0 4px',
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

const contentStyle = {
  marginTop: '20px',
};

const sessionListStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: '16px',
};

const sessionCardStyle = {
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

const sessionTitleRowStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
};

const sessionTypeIconStyle = {
  fontSize: '18px',
};

const sessionTitleStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const statusBadgeStyle = {
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

const sessionMetaStyle = {
  fontSize: '13px',
  color: '#666',
  marginBottom: '8px',
};

const descriptionStyle = {
  fontSize: '13px',
  color: '#333',
  marginTop: '8px',
  borderTop: '1px solid #eee',
  paddingTop: '8px',
};

const cardFooterStyle = {
  padding: '12px 16px',
  borderTop: '1px solid #e9ecef',
  display: 'flex',
  gap: '8px',
  flexWrap: 'wrap',
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

const viewButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const joinButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const leaveButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#ffc107',
  color: '#333',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const startButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const endButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
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
  maxWidth: '600px',
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

const detailBodyStyle = {
  padding: '16px',
};

const detailRowStyle = {
  display: 'flex',
  marginBottom: '12px',
  fontSize: '14px',
};

const detailLabelStyle = {
  fontWeight: '500',
  color: '#666',
  minWidth: '100px',
  marginRight: '8px',
};

const sectionTitleStyle = {
  fontSize: '14px',
  fontWeight: '600',
  color: '#333',
  marginTop: '20px',
  marginBottom: '12px',
  borderTop: '1px solid #eee',
  paddingTop: '16px',
};

const participantListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const participantItemStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '8px 12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
};

const participantNameStyle = {
  fontSize: '13px',
};

const teamRoleBadgeStyle = {
  padding: '2px 8px',
  borderRadius: '12px',
  fontSize: '11px',
  backgroundColor: '#e9ecef',
  color: '#495057',
};

const teamListStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, 1fr)',
  gap: '8px',
};

const teamCardStyle = {
  padding: '12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  borderLeft: '4px solid',
};

const teamNameStyle = {
  fontWeight: '600',
  display: 'block',
  marginBottom: '4px',
};

const teamScoreStyle = {
  fontSize: '12px',
  color: '#666',
};
