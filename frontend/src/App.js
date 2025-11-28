import React, { useState, useEffect } from 'react';
import ScenarioList from './components/ScenarioList';
import ScenarioEditor from './components/ScenarioEditor';
import TopologySelector from './components/TopologySelector';
import Login from './components/Login';
import InstructorControls from './components/InstructorControls';
import Dashboard from './components/Dashboard';
import { authApi } from './api';

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('dashboard'); // 'dashboard', 'list', 'editor', or 'topologies'
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

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>CEW Training Platform</h1>
            <p style={{ color: '#666', margin: 0 }}>
              Cyber &amp; Electronic Warfare Training Environment
            </p>
          </div>
          <div style={userInfoStyle}>
            <span>
              👤 {user.full_name || user.username}
              <span style={roleBadgeStyle}>{user.role}</span>
            </span>
            <button onClick={handleLogout} style={logoutButtonStyle}>
              Logout
            </button>
          </div>
        </div>

        {/* Navigation tabs */}
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
            <div style={{ marginBottom: '16px' }}>
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
      </main>

      <footer style={footerStyle}>
        <small>
          ⚠️ Training use only. Do not connect to operational networks.
        </small>
      </footer>
    </div>
  );
}

const containerStyle = {
  fontFamily: 'Arial, sans-serif',
  maxWidth: '1200px',
  margin: '0 auto',
  padding: '20px',
};

const headerStyle = {
  borderBottom: '2px solid #333',
  paddingBottom: '16px',
  marginBottom: '20px',
};

const navStyle = {
  marginTop: '16px',
  display: 'flex',
  gap: '8px',
};

const navButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#e9ecef',
  color: '#333',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const navButtonActiveStyle = {
  ...navButtonStyle,
  backgroundColor: '#007bff',
  color: 'white',
};

const userInfoStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
};

const roleBadgeStyle = {
  backgroundColor: '#007bff',
  color: 'white',
  padding: '2px 8px',
  borderRadius: '12px',
  fontSize: '12px',
  marginLeft: '8px',
  textTransform: 'uppercase',
};

const logoutButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};

const mainStyle = {
  minHeight: '400px',
};

const footerStyle = {
  marginTop: '40px',
  paddingTop: '16px',
  borderTop: '1px solid #ddd',
  textAlign: 'center',
  color: '#999',
};

const btnPrimaryStyle = {
  padding: '10px 20px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
  marginRight: '10px',
};

const btnSecondaryStyle = {
  padding: '10px 20px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};
