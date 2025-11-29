import React, { useState, useEffect } from 'react';
import ScenarioList from './components/ScenarioList';
import ScenarioEditor from './components/ScenarioEditor';
import TopologySelector from './components/TopologySelector';
import Login from './components/Login';
import InstructorControls from './components/InstructorControls';
import Dashboard from './components/Dashboard';
import AuditLogs from './components/AuditLogs';
import UserManagement from './components/UserManagement';
import RecordingsList from './components/RecordingsList';
import ProgressDashboard from './components/ProgressDashboard';
import ScheduleManager from './components/ScheduleManager';
import MultiUserSessions from './components/MultiUserSessions';
import Marketplace from './components/Marketplace';
import TopologyEditor from './components/TopologyEditor';
import RFSimulation from './components/RFSimulation';
import BackupManager from './components/BackupManager';
import RateLimitsDashboard from './components/RateLimitsDashboard';
import IntegrationsManager from './components/IntegrationsManager';
import { authApi } from './api';

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('dashboard'); // 'dashboard', 'list', 'editor', 'topologies', 'audit', 'users', 'recordings', 'progress', 'schedule', 'sessions', 'marketplace', 'topology-editor', 'rf-simulation', 'backups', 'rate-limits', 'integrations'
  const [editingScenario, setEditingScenario] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    // Check for existing session
    const savedUser = authApi.getUser();
    if (savedUser && authApi.getToken()) {
      setUser(savedUser);
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    authApi.logout();
    setUser(null);
  };

  const handleCreateNew = () => {
    setEditingScenario(null);
    setView('editor');
  };

  const handleCreateFromTemplate = () => {
    setView('topologies');
  };

  const handleTemplateSelect = (template) => {
    // Create a new scenario pre-populated with template data
    setEditingScenario({
      name: template.name + ' Scenario',
      description: template.description,
      topology: {
        nodes: template.nodes,
        networks: template.networks,
        rf_environment: template.rf_environment,
      },
      constraints: template.constraints,
    });
    setView('editor');
  };

  const handleEdit = (scenario) => {
    setEditingScenario(scenario);
    setView('editor');
  };

  const handleSave = () => {
    setView('list');
    setEditingScenario(null);
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleCancel = () => {
    setView('list');
    setEditingScenario(null);
  };

  // Show login if not authenticated
  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  const isInstructorOrAdmin = ['admin', 'instructor'].includes(user.role);
  const isAdmin = user.role === 'admin';

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <div style={headerInnerStyle}>
          <div>
            <h1 style={titleStyle}>CEW Training Platform</h1>
            <p style={subtitleStyle}>
              Cyber &amp; Electronic Warfare Training Environment
            </p>
          </div>
          <div style={userInfoStyle}>
            <span style={userNameStyle}>
              👤 {user.full_name || user.username}
              <span style={roleBadgeStyle}>{user.role}</span>
            </span>
            <button onClick={handleLogout} style={logoutButtonStyle}>
              Logout
            </button>
          </div>
        </div>

        {/* Navigation tabs - horizontally scrollable on mobile */}
        <nav style={navStyle}>
          {isInstructorOrAdmin && (
            <button
              onClick={() => setView('dashboard')}
              style={view === 'dashboard' ? navButtonActiveStyle : navButtonStyle}
            >
              📊 Dashboard
            </button>
          )}
          <button
            onClick={() => setView('list')}
            style={view === 'list' ? navButtonActiveStyle : navButtonStyle}
          >
            📝 Scenarios
          </button>
          {isInstructorOrAdmin && (
            <button
              onClick={() => setView('topology-editor')}
              style={view === 'topology-editor' ? navButtonActiveStyle : navButtonStyle}
            >
              🗺️ Topology
            </button>
          )}
          <button
            onClick={() => setView('schedule')}
            style={view === 'schedule' ? navButtonActiveStyle : navButtonStyle}
          >
            📅 Schedule
          </button>
          <button
            onClick={() => setView('sessions')}
            style={view === 'sessions' ? navButtonActiveStyle : navButtonStyle}
          >
            👥 Sessions
          </button>
          <button
            onClick={() => setView('marketplace')}
            style={view === 'marketplace' ? navButtonActiveStyle : navButtonStyle}
          >
            🛒 Marketplace
          </button>
          <button
            onClick={() => setView('progress')}
            style={view === 'progress' ? navButtonActiveStyle : navButtonStyle}
          >
            📈 Progress
          </button>
          {isInstructorOrAdmin && (
            <button
              onClick={() => setView('rf-simulation')}
              style={view === 'rf-simulation' ? navButtonActiveStyle : navButtonStyle}
            >
              📡 RF/EW
            </button>
          )}
          {isInstructorOrAdmin && (
            <button
              onClick={() => setView('recordings')}
              style={view === 'recordings' ? navButtonActiveStyle : navButtonStyle}
            >
              📼 Recordings
            </button>
          )}
          {isInstructorOrAdmin && (
            <button
              onClick={() => setView('audit')}
              style={view === 'audit' ? navButtonActiveStyle : navButtonStyle}
            >
              📋 Audit Logs
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => setView('backups')}
              style={view === 'backups' ? navButtonActiveStyle : navButtonStyle}
            >
              💾 Backups
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => setView('rate-limits')}
              style={view === 'rate-limits' ? navButtonActiveStyle : navButtonStyle}
            >
              🚦 Rate Limits
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => setView('integrations')}
              style={view === 'integrations' ? navButtonActiveStyle : navButtonStyle}
            >
              🔌 Integrations
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => setView('users')}
              style={view === 'users' ? navButtonActiveStyle : navButtonStyle}
            >
              👥 Users
            </button>
          )}
        </nav>
      </header>

      <main style={mainStyle}>
        {view === 'dashboard' && isInstructorOrAdmin && (
          <>
            <Dashboard user={user} />
            <InstructorControls user={user} />
          </>
        )}

        {view === 'list' && (
          <>
            <div style={buttonContainerStyle}>
              <button onClick={handleCreateNew} style={btnPrimaryStyle}>
                + Create New Scenario
              </button>
              <button onClick={handleCreateFromTemplate} style={btnSecondaryStyle}>
                📋 Use Template
              </button>
            </div>
            <ScenarioList
              onEdit={handleEdit}
              refreshTrigger={refreshTrigger}
            />
          </>
        )}
        {view === 'editor' && (
          <ScenarioEditor
            scenario={editingScenario}
            onSave={handleSave}
            onCancel={handleCancel}
          />
        )}
        {view === 'topologies' && (
          <TopologySelector
            onSelect={handleTemplateSelect}
            onCancel={handleCancel}
          />
        )}
        {view === 'schedule' && (
          <ScheduleManager user={user} />
        )}
        {view === 'sessions' && (
          <MultiUserSessions user={user} />
        )}
        {view === 'marketplace' && (
          <Marketplace user={user} />
        )}
        {view === 'progress' && (
          <ProgressDashboard user={user} />
        )}
        {view === 'topology-editor' && isInstructorOrAdmin && (
          <TopologyEditor user={user} />
        )}
        {view === 'rf-simulation' && isInstructorOrAdmin && (
          <RFSimulation user={user} />
        )}
        {view === 'recordings' && isInstructorOrAdmin && (
          <RecordingsList user={user} />
        )}
        {view === 'audit' && isInstructorOrAdmin && (
          <AuditLogs />
        )}
        {view === 'backups' && isAdmin && (
          <BackupManager user={user} />
        )}
        {view === 'rate-limits' && isAdmin && (
          <RateLimitsDashboard user={user} />
        )}
        {view === 'integrations' && isAdmin && (
          <IntegrationsManager user={user} />
        )}
        {view === 'users' && isAdmin && (
          <UserManagement currentUser={user} />
        )}
      </main>

      <footer style={footerStyle}>
        <small>
          ⚠️ Training use only. Do not connect to operational networks.
        </small>
      </footer>
    </div>
  );
}

// Mobile-responsive styles using CSS-in-JS
// These styles adapt to different screen sizes

const containerStyle = {
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  maxWidth: '1200px',
  margin: '0 auto',
  padding: '16px',
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
};

const headerStyle = {
  borderBottom: '2px solid #333',
  paddingBottom: '16px',
  marginBottom: '20px',
  position: 'sticky',
  top: 0,
  backgroundColor: 'var(--color-bg, #ffffff)',
  zIndex: 100,
};

const headerInnerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: '12px',
};

const titleStyle = {
  margin: 0,
  fontSize: 'clamp(1.25rem, 4vw, 1.75rem)',
};

const subtitleStyle = {
  color: '#666',
  margin: 0,
  fontSize: 'clamp(0.75rem, 2vw, 0.875rem)',
};

const navStyle = {
  marginTop: '16px',
  display: 'flex',
  gap: '8px',
  flexWrap: 'wrap',
  overflowX: 'auto',
  WebkitOverflowScrolling: 'touch',
  scrollbarWidth: 'none',
  msOverflowStyle: 'none',
  paddingBottom: '4px',
};

const navButtonStyle = {
  padding: '10px 16px',
  backgroundColor: '#e9ecef',
  color: '#333',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontSize: '14px',
  whiteSpace: 'nowrap',
  minHeight: '44px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'background-color 0.2s, transform 0.1s',
  touchAction: 'manipulation',
};

const navButtonActiveStyle = {
  ...navButtonStyle,
  backgroundColor: '#007bff',
  color: 'white',
};

const userInfoStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  flexWrap: 'wrap',
};

const userNameStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
  fontSize: '14px',
};

const roleBadgeStyle = {
  backgroundColor: '#007bff',
  color: 'white',
  padding: '2px 8px',
  borderRadius: '12px',
  fontSize: '11px',
  marginLeft: '4px',
  textTransform: 'uppercase',
  fontWeight: '600',
};

const logoutButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  minHeight: '44px',
  touchAction: 'manipulation',
  transition: 'background-color 0.2s',
};

const mainStyle = {
  minHeight: '400px',
  flex: 1,
  paddingBottom: '80px', // Space for potential bottom navigation
};

const footerStyle = {
  marginTop: 'auto',
  paddingTop: '16px',
  paddingBottom: '16px',
  borderTop: '1px solid #ddd',
  textAlign: 'center',
  color: '#999',
  fontSize: '12px',
};

const buttonContainerStyle = {
  marginBottom: '16px',
  display: 'flex',
  flexWrap: 'wrap',
  gap: '8px',
};

const btnPrimaryStyle = {
  padding: '12px 20px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontSize: '14px',
  minHeight: '44px',
  touchAction: 'manipulation',
  transition: 'background-color 0.2s, transform 0.1s',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '6px',
};

const btnSecondaryStyle = {
  padding: '12px 20px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontSize: '14px',
  minHeight: '44px',
  touchAction: 'manipulation',
  transition: 'background-color 0.2s, transform 0.1s',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '6px',
};
