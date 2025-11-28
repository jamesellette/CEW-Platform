import React, { useState, useEffect } from 'react';
import { topologyApi } from '../api';

export default function TopologySelector({ onSelect, onCancel }) {
  const [topologies, setTopologies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateDetails, setTemplateDetails] = useState(null);

  useEffect(() => {
    loadTopologies();
  }, []);

  const loadTopologies = async () => {
    try {
      setLoading(true);
      const response = await topologyApi.list();
      setTopologies(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load topology templates');
      console.error('Error loading topologies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateClick = async (template) => {
    setSelectedTemplate(template);
    try {
      const response = await topologyApi.get(template.filename);
      setTemplateDetails(response.data);
    } catch (err) {
      setError('Failed to load template details');
      console.error('Error loading template:', err);
    }
  };

  const handleUseTemplate = () => {
    if (templateDetails) {
      onSelect(templateDetails);
    }
  };

  if (loading) return <p>Loading topology templates...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="topology-selector">
      <h2>Select Topology Template</h2>
      <p style={{ color: '#666' }}>
        Choose a pre-configured topology template for your scenario.
      </p>

      <div style={{ display: 'flex', gap: '20px', marginTop: '16px' }}>
        {/* Template List */}
        <div style={{ flex: 1 }}>
          <h3>Available Templates</h3>
          {topologies.length === 0 ? (
            <p>No templates available.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {topologies.map((template) => (
                <li
                  key={template.filename}
                  onClick={() => handleTemplateClick(template)}
                  style={{
                    ...templateItemStyle,
                    backgroundColor:
                      selectedTemplate?.filename === template.filename
                        ? '#e3f2fd'
                        : '#f9f9f9',
                  }}
                >
                  <strong>{template.name}</strong>
                  <br />
                  <small style={{ color: '#666' }}>
                    {template.description}
                  </small>
                  <br />
                  <small>
                    Nodes: {template.node_count} | Networks:{' '}
                    {template.networks.join(', ')}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Template Details */}
        <div style={{ flex: 1 }}>
          <h3>Template Details</h3>
          {templateDetails ? (
            <div style={detailsStyle}>
              <h4>{templateDetails.name}</h4>
              <p>{templateDetails.description}</p>

              <h5>Nodes ({templateDetails.nodes?.length || 0})</h5>
              <ul>
                {templateDetails.nodes?.map((node) => (
                  <li key={node.id}>
                    <strong>{node.hostname}</strong> ({node.type}) - {node.ip}
                  </li>
                ))}
              </ul>

              <h5>Networks</h5>
              <ul>
                {templateDetails.networks?.map((net) => (
                  <li key={net.name}>
                    <strong>{net.name}</strong>: {net.subnet}
                    {net.isolated && ' (isolated)'}
                  </li>
                ))}
              </ul>

              <h5>Safety Constraints</h5>
              <ul>
                <li>
                  <span aria-label={templateDetails.constraints?.allow_external_network ? 'Warning: External network allowed' : 'External network blocked'}>
                    External Network:{' '}
                    {templateDetails.constraints?.allow_external_network
                      ? '⚠️ Allowed'
                      : '✅ Blocked'}
                  </span>
                </li>
                <li>
                  <span aria-label={templateDetails.constraints?.allow_real_rf ? 'Warning: Real RF allowed' : 'Real RF blocked, simulated only'}>
                    Real RF Transmission:{' '}
                    {templateDetails.constraints?.allow_real_rf
                      ? '⚠️ Allowed'
                      : '✅ Blocked (Simulated Only)'}
                  </span>
                </li>
              </ul>
            </div>
          ) : (
            <p style={{ color: '#999' }}>
              Select a template to view details.
            </p>
          )}
        </div>
      </div>

      <div style={{ marginTop: '20px' }}>
        <button
          onClick={handleUseTemplate}
          disabled={!templateDetails}
          style={{
            ...btnPrimaryStyle,
            opacity: templateDetails ? 1 : 0.5,
          }}
        >
          Use This Template
        </button>
        <button onClick={onCancel} style={btnSecondaryStyle}>
          Cancel
        </button>
      </div>
    </div>
  );
}

const templateItemStyle = {
  padding: '12px',
  marginBottom: '8px',
  border: '1px solid #ddd',
  borderRadius: '4px',
  cursor: 'pointer',
};

const detailsStyle = {
  padding: '16px',
  backgroundColor: '#f9f9f9',
  borderRadius: '4px',
  border: '1px solid #ddd',
};

const btnPrimaryStyle = {
  padding: '10px 20px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  marginRight: '8px',
};

const btnSecondaryStyle = {
  padding: '10px 20px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};
