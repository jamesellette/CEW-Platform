import React, { useState } from 'react';
import ScenarioList from './components/ScenarioList';
import ScenarioEditor from './components/ScenarioEditor';

export default function App() {
  const [view, setView] = useState('list'); // 'list' or 'editor'
  const [editingScenario, setEditingScenario] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleCreateNew = () => {
    setEditingScenario(null);
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

  return (
    <div style={containerStyle}>
      <header style={headerStyle}>
        <h1>CEW Training Platform</h1>
        <p style={{ color: '#666', margin: 0 }}>
          Cyber &amp; Electronic Warfare Training Environment
        </p>
      </header>

      <main style={mainStyle}>
        {view === 'list' ? (
          <>
            <div style={{ marginBottom: '16px' }}>
              <button onClick={handleCreateNew} style={btnPrimaryStyle}>
                + Create New Scenario
              </button>
            </div>
            <ScenarioList
              onEdit={handleEdit}
              refreshTrigger={refreshTrigger}
            />
          </>
        ) : (
          <ScenarioEditor
            scenario={editingScenario}
            onSave={handleSave}
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
  maxWidth: '1000px',
  margin: '0 auto',
  padding: '20px',
};

const headerStyle = {
  borderBottom: '2px solid #333',
  paddingBottom: '16px',
  marginBottom: '20px',
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
};
