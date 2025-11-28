import React, { useState, useEffect } from 'react';
import { scenarioApi } from '../api';

export default function ScenarioList({ onEdit, onRefresh, refreshTrigger }) {
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadScenarios();
  }, [refreshTrigger]);

  const loadScenarios = async () => {
    try {
      setLoading(true);
      const response = await scenarioApi.list();
      setScenarios(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load scenarios');
      console.error('Error loading scenarios:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this scenario?')) {
      try {
        await scenarioApi.delete(id);
        loadScenarios();
      } catch (err) {
        setError('Failed to delete scenario');
        console.error('Error deleting scenario:', err);
      }
    }
  };

  if (loading) return <p>Loading scenarios...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="scenario-list">
      <h2>Scenarios</h2>
      {scenarios.length === 0 ? (
        <p>No scenarios yet. Create one to get started.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Description</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.id}>
                <td style={tdStyle}>{scenario.name}</td>
                <td style={tdStyle}>{scenario.description || '-'}</td>
                <td style={tdStyle}>
                  <button onClick={() => onEdit(scenario)} style={btnStyle}>
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(scenario.id)}
                    style={{ ...btnStyle, ...btnDangerStyle }}
                  >
                    Delete
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

const thStyle = {
  border: '1px solid #ddd',
  padding: '8px',
  backgroundColor: '#f4f4f4',
  textAlign: 'left',
};

const tdStyle = {
  border: '1px solid #ddd',
  padding: '8px',
};

const btnStyle = {
  marginRight: '8px',
  padding: '4px 8px',
  cursor: 'pointer',
};

const btnDangerStyle = {
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
};
