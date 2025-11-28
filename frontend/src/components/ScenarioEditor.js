import React, { useState, useEffect } from 'react';
import { scenarioApi } from '../api';

export default function ScenarioEditor({ scenario, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    topology: '{}',
    constraints: '{}',
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (scenario) {
      setFormData({
        name: scenario.name || '',
        description: scenario.description || '',
        topology: JSON.stringify(scenario.topology || {}, null, 2),
        constraints: JSON.stringify(scenario.constraints || {}, null, 2),
      });
    } else {
      setFormData({
        name: '',
        description: '',
        topology: '{}',
        constraints: '{}',
      });
    }
  }, [scenario]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      // Parse JSON fields
      let topology, constraints;
      try {
        topology = JSON.parse(formData.topology);
      } catch {
        throw new Error('Invalid topology JSON');
      }
      try {
        constraints = JSON.parse(formData.constraints);
      } catch {
        throw new Error('Invalid constraints JSON');
      }

      const data = {
        name: formData.name,
        description: formData.description,
        topology,
        constraints,
      };

      if (scenario?.id) {
        await scenarioApi.update(scenario.id, data);
      } else {
        await scenarioApi.create(data);
      }

      onSave();
    } catch (err) {
      const message =
        err.response?.data?.detail || err.message || 'Failed to save scenario';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="scenario-editor">
      <h2>{scenario?.id ? 'Edit Scenario' : 'Create New Scenario'}</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label htmlFor="name">Name *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </div>
        <div style={fieldStyle}>
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={3}
            style={inputStyle}
          />
        </div>
        <div style={fieldStyle}>
          <label htmlFor="topology">Topology (JSON)</label>
          <textarea
            id="topology"
            name="topology"
            value={formData.topology}
            onChange={handleChange}
            rows={5}
            style={{ ...inputStyle, fontFamily: 'monospace' }}
          />
        </div>
        <div style={fieldStyle}>
          <label htmlFor="constraints">Constraints (JSON)</label>
          <textarea
            id="constraints"
            name="constraints"
            value={formData.constraints}
            onChange={handleChange}
            rows={5}
            style={{ ...inputStyle, fontFamily: 'monospace' }}
          />
          <small style={{ color: '#666' }}>
            Note: "allow_external_network" and "allow_real_rf" are blocked for safety.
          </small>
        </div>
        <div style={{ marginTop: '16px' }}>
          <button type="submit" disabled={saving} style={btnPrimaryStyle}>
            {saving ? 'Saving...' : scenario?.id ? 'Update' : 'Create'}
          </button>
          <button type="button" onClick={onCancel} style={btnSecondaryStyle}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

const fieldStyle = {
  marginBottom: '16px',
  display: 'flex',
  flexDirection: 'column',
};

const inputStyle = {
  padding: '8px',
  fontSize: '14px',
  border: '1px solid #ccc',
  borderRadius: '4px',
  marginTop: '4px',
};

const btnPrimaryStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  marginRight: '8px',
};

const btnSecondaryStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};
