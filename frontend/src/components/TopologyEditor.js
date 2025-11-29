import React, { useState, useEffect, useCallback } from 'react';
import { topologyApi } from '../api';

/**
 * Visual Network Topology Editor component.
 * Provides a drag-and-drop interface for designing network diagrams.
 */
export default function TopologyEditor({ user }) {
  const [topologies, setTopologies] = useState([]);
  const [selectedTopology, setSelectedTopology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showNodeForm, setShowNodeForm] = useState(false);
  const [showConnectionForm, setShowConnectionForm] = useState(false);
  const [nodeTypes, setNodeTypes] = useState([]);
  const [connectionTypes, setConnectionTypes] = useState([]);
  const [validationResults, setValidationResults] = useState(null);

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form states
  const [topologyForm, setTopologyForm] = useState({
    name: '',
    description: '',
  });

  const [nodeForm, setNodeForm] = useState({
    label: '',
    node_type: '',
    ip_address: '',
    hostname: '',
    x: 100,
    y: 100,
    properties: {},
  });

  const [connectionForm, setConnectionForm] = useState({
    source_node: '',
    target_node: '',
    connection_type: '',
    bandwidth: '',
    latency: '',
  });

  // Fetch topologies
  const fetchTopologies = useCallback(async () => {
    try {
      setLoading(true);
      const response = await topologyApi.listTopologies();
      setTopologies(response.data || []);
    } catch (err) {
      console.error('Failed to load topologies:', err);
      setError('Failed to load topologies');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch node and connection types
  const fetchTypes = useCallback(async () => {
    try {
      const [nodeTypesRes, connTypesRes] = await Promise.all([
        topologyApi.getNodeTypes(),
        topologyApi.getConnectionTypes(),
      ]);
      setNodeTypes(nodeTypesRes.data || []);
      setConnectionTypes(connTypesRes.data || []);
    } catch (err) {
      console.error('Failed to load types:', err);
    }
  }, []);

  useEffect(() => {
    fetchTopologies();
    fetchTypes();
  }, [fetchTopologies, fetchTypes]);

  // Load topology details
  const handleSelectTopology = async (topologyId) => {
    try {
      const response = await topologyApi.getTopology(topologyId);
      setSelectedTopology(response.data);
      setValidationResults(null);
    } catch (err) {
      setActionError('Failed to load topology details');
    }
  };

  // Create new topology
  const handleCreateTopology = async (e) => {
    e.preventDefault();
    try {
      await topologyApi.createTopology(topologyForm.name, topologyForm.description);
      setShowCreateForm(false);
      setTopologyForm({ name: '', description: '' });
      setSuccessMessage('Topology created successfully');
      fetchTopologies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create topology: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Add node
  const handleAddNode = async (e) => {
    e.preventDefault();
    if (!selectedTopology) return;

    try {
      await topologyApi.addNode(selectedTopology.topology_id, {
        label: nodeForm.label,
        node_type: nodeForm.node_type,
        ip_address: nodeForm.ip_address || null,
        hostname: nodeForm.hostname || null,
        x: parseInt(nodeForm.x),
        y: parseInt(nodeForm.y),
        properties: nodeForm.properties,
      });
      setShowNodeForm(false);
      setNodeForm({
        label: '',
        node_type: '',
        ip_address: '',
        hostname: '',
        x: 100,
        y: 100,
        properties: {},
      });
      await handleSelectTopology(selectedTopology.topology_id);
      setSuccessMessage('Node added');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to add node: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Add connection
  const handleAddConnection = async (e) => {
    e.preventDefault();
    if (!selectedTopology) return;

    try {
      await topologyApi.addConnection(selectedTopology.topology_id, {
        source_node_id: connectionForm.source_node,
        target_node_id: connectionForm.target_node,
        connection_type: connectionForm.connection_type,
        bandwidth: connectionForm.bandwidth || null,
        latency: connectionForm.latency || null,
      });
      setShowConnectionForm(false);
      setConnectionForm({
        source_node: '',
        target_node: '',
        connection_type: '',
        bandwidth: '',
        latency: '',
      });
      await handleSelectTopology(selectedTopology.topology_id);
      setSuccessMessage('Connection added');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to add connection: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Delete node
  const handleDeleteNode = async (nodeId) => {
    if (!selectedTopology) return;
    if (!window.confirm('Are you sure you want to delete this node?')) return;

    try {
      await topologyApi.deleteNode(selectedTopology.topology_id, nodeId);
      await handleSelectTopology(selectedTopology.topology_id);
      setSuccessMessage('Node deleted');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete node');
    }
  };

  // Delete connection
  const handleDeleteConnection = async (connectionId) => {
    if (!selectedTopology) return;
    if (!window.confirm('Are you sure you want to delete this connection?')) return;

    try {
      await topologyApi.deleteConnection(selectedTopology.topology_id, connectionId);
      await handleSelectTopology(selectedTopology.topology_id);
      setSuccessMessage('Connection deleted');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete connection');
    }
  };

  // Validate topology
  const handleValidate = async () => {
    if (!selectedTopology) return;

    try {
      const response = await topologyApi.validateTopology(selectedTopology.topology_id);
      setValidationResults(response.data);
    } catch (err) {
      setActionError('Validation failed');
    }
  };

  // Export topology
  const handleExport = async (format) => {
    if (!selectedTopology) return;

    try {
      const response = await topologyApi.exportTopology(selectedTopology.topology_id, format);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedTopology.name}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setActionError('Export failed');
    }
  };

  // Delete topology
  const handleDeleteTopology = async (topologyId) => {
    if (!window.confirm('Are you sure you want to delete this topology?')) return;

    try {
      await topologyApi.deleteTopology(topologyId);
      if (selectedTopology?.topology_id === topologyId) {
        setSelectedTopology(null);
      }
      fetchTopologies();
      setSuccessMessage('Topology deleted');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete topology');
    }
  };

  // Get node type icon
  const getNodeIcon = (nodeType) => {
    const icons = {
      host: '💻',
      server: '🖥️',
      router: '📡',
      switch: '🔀',
      firewall: '🛡️',
      attacker: '🎯',
      target: '🎪',
      gateway: '🚪',
    };
    return icons[nodeType] || '📦';
  };

  if (loading) {
    return <div style={containerStyle}>Loading topology editor...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={fetchTopologies} style={buttonStyle}>Retry</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>🗺️ Network Topology Editor</h2>
        {isInstructor && (
          <button onClick={() => setShowCreateForm(true)} style={primaryButtonStyle}>
            + New Topology
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

      <div style={layoutStyle}>
        {/* Topologies List */}
        <div style={sidebarStyle}>
          <h3 style={sidebarHeaderStyle}>Topologies</h3>
          {topologies.length === 0 ? (
            <p style={emptyTextStyle}>No topologies created yet.</p>
          ) : (
            <div style={listStyle}>
              {topologies.map((topology) => (
                <div
                  key={topology.topology_id}
                  style={{
                    ...listItemStyle,
                    backgroundColor:
                      selectedTopology?.topology_id === topology.topology_id
                        ? '#e3f2fd'
                        : 'white',
                  }}
                  onClick={() => handleSelectTopology(topology.topology_id)}
                >
                  <div style={listItemContentStyle}>
                    <span style={topologyNameStyle}>{topology.name}</span>
                    <span style={nodeCountStyle}>
                      {topology.nodes?.length || 0} nodes
                    </span>
                  </div>
                  {isInstructor && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTopology(topology.topology_id);
                      }}
                      style={deleteButtonSmallStyle}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Editor Area */}
        <div style={editorAreaStyle}>
          {selectedTopology ? (
            <>
              <div style={editorHeaderStyle}>
                <div>
                  <h3>{selectedTopology.name}</h3>
                  <p style={descriptionTextStyle}>{selectedTopology.description}</p>
                </div>
                <div style={editorActionsStyle}>
                  {isInstructor && (
                    <>
                      <button onClick={() => setShowNodeForm(true)} style={actionButtonStyle}>
                        + Node
                      </button>
                      <button
                        onClick={() => setShowConnectionForm(true)}
                        style={actionButtonStyle}
                        disabled={!selectedTopology.nodes?.length}
                      >
                        + Connection
                      </button>
                    </>
                  )}
                  <button onClick={handleValidate} style={validateButtonStyle}>
                    ✓ Validate
                  </button>
                  <button onClick={() => handleExport('json')} style={exportButtonStyle}>
                    📥 Export
                  </button>
                </div>
              </div>

              {/* Validation Results */}
              {validationResults && (
                <div
                  style={{
                    ...validationBoxStyle,
                    backgroundColor: validationResults.is_valid ? '#d4edda' : '#f8d7da',
                  }}
                >
                  <strong>{validationResults.is_valid ? '✓ Valid' : '✗ Invalid'}</strong>
                  {validationResults.issues?.length > 0 && (
                    <ul style={issueListStyle}>
                      {validationResults.issues.map((issue, idx) => (
                        <li key={idx} style={issueItemStyle}>
                          <span style={issueSeverityStyle(issue.severity)}>
                            {issue.severity}
                          </span>
                          : {issue.message}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Visual Diagram */}
              <div style={diagramContainerStyle}>
                <svg style={svgStyle} viewBox="0 0 800 500">
                  {/* Connections */}
                  {selectedTopology.connections?.map((conn) => {
                    const sourceNode = selectedTopology.nodes?.find(
                      (n) => n.node_id === conn.source_node_id
                    );
                    const targetNode = selectedTopology.nodes?.find(
                      (n) => n.node_id === conn.target_node_id
                    );
                    if (!sourceNode || !targetNode) return null;

                    return (
                      <g key={conn.connection_id}>
                        <line
                          x1={sourceNode.x}
                          y1={sourceNode.y}
                          x2={targetNode.x}
                          y2={targetNode.y}
                          stroke="#666"
                          strokeWidth="2"
                        />
                        <text
                          x={(sourceNode.x + targetNode.x) / 2}
                          y={(sourceNode.y + targetNode.y) / 2 - 5}
                          fontSize="10"
                          fill="#666"
                          textAnchor="middle"
                        >
                          {conn.connection_type}
                        </text>
                      </g>
                    );
                  })}

                  {/* Nodes */}
                  {selectedTopology.nodes?.map((node) => (
                    <g key={node.node_id}>
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r="30"
                        fill="#fff"
                        stroke="#007bff"
                        strokeWidth="2"
                      />
                      <text
                        x={node.x}
                        y={node.y - 5}
                        fontSize="20"
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        {getNodeIcon(node.node_type)}
                      </text>
                      <text
                        x={node.x}
                        y={node.y + 45}
                        fontSize="12"
                        textAnchor="middle"
                        fill="#333"
                      >
                        {node.label}
                      </text>
                      <text
                        x={node.x}
                        y={node.y + 60}
                        fontSize="10"
                        textAnchor="middle"
                        fill="#666"
                      >
                        {node.ip_address || ''}
                      </text>
                    </g>
                  ))}
                </svg>
              </div>

              {/* Node and Connection Lists */}
              <div style={detailsGridStyle}>
                {/* Nodes */}
                <div style={detailsCardStyle}>
                  <h4>Nodes ({selectedTopology.nodes?.length || 0})</h4>
                  {selectedTopology.nodes?.length === 0 ? (
                    <p style={emptyTextStyle}>No nodes yet. Add your first node!</p>
                  ) : (
                    <div style={itemListStyle}>
                      {selectedTopology.nodes?.map((node) => (
                        <div key={node.node_id} style={itemRowStyle}>
                          <span>
                            {getNodeIcon(node.node_type)} {node.label}
                          </span>
                          <span style={itemMetaStyle}>
                            {node.ip_address || 'No IP'}
                          </span>
                          {isInstructor && (
                            <button
                              onClick={() => handleDeleteNode(node.node_id)}
                              style={deleteButtonSmallStyle}
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Connections */}
                <div style={detailsCardStyle}>
                  <h4>Connections ({selectedTopology.connections?.length || 0})</h4>
                  {selectedTopology.connections?.length === 0 ? (
                    <p style={emptyTextStyle}>No connections yet.</p>
                  ) : (
                    <div style={itemListStyle}>
                      {selectedTopology.connections?.map((conn) => {
                        const source = selectedTopology.nodes?.find(
                          (n) => n.node_id === conn.source_node_id
                        );
                        const target = selectedTopology.nodes?.find(
                          (n) => n.node_id === conn.target_node_id
                        );
                        return (
                          <div key={conn.connection_id} style={itemRowStyle}>
                            <span>
                              {source?.label || '?'} ↔ {target?.label || '?'}
                            </span>
                            <span style={itemMetaStyle}>{conn.connection_type}</span>
                            {isInstructor && (
                              <button
                                onClick={() => handleDeleteConnection(conn.connection_id)}
                                style={deleteButtonSmallStyle}
                              >
                                ✕
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div style={placeholderStyle}>
              <span style={placeholderIconStyle}>🗺️</span>
              <p>Select a topology from the list or create a new one</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Topology Modal */}
      {showCreateForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Create New Topology</h3>
              <button onClick={() => setShowCreateForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateTopology} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Name *</label>
                <input
                  type="text"
                  value={topologyForm.name}
                  onChange={(e) => setTopologyForm((prev) => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Corporate Network"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description</label>
                <textarea
                  value={topologyForm.description}
                  onChange={(e) =>
                    setTopologyForm((prev) => ({ ...prev, description: e.target.value }))
                  }
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="Describe the network topology..."
                />
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowCreateForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Node Modal */}
      {showNodeForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Add Node</h3>
              <button onClick={() => setShowNodeForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleAddNode} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Label *</label>
                <input
                  type="text"
                  value={nodeForm.label}
                  onChange={(e) => setNodeForm((prev) => ({ ...prev, label: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Web Server"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Node Type *</label>
                <select
                  value={nodeForm.node_type}
                  onChange={(e) => setNodeForm((prev) => ({ ...prev, node_type: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="">Select type...</option>
                  {nodeTypes.map((type) => (
                    <option key={type} value={type}>
                      {getNodeIcon(type)} {type}
                    </option>
                  ))}
                </select>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>IP Address</label>
                  <input
                    type="text"
                    value={nodeForm.ip_address}
                    onChange={(e) => setNodeForm((prev) => ({ ...prev, ip_address: e.target.value }))}
                    style={inputStyle}
                    placeholder="10.0.0.1"
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Hostname</label>
                  <input
                    type="text"
                    value={nodeForm.hostname}
                    onChange={(e) => setNodeForm((prev) => ({ ...prev, hostname: e.target.value }))}
                    style={inputStyle}
                    placeholder="webserver-01"
                  />
                </div>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>X Position</label>
                  <input
                    type="number"
                    value={nodeForm.x}
                    onChange={(e) => setNodeForm((prev) => ({ ...prev, x: e.target.value }))}
                    style={inputStyle}
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Y Position</label>
                  <input
                    type="number"
                    value={nodeForm.y}
                    onChange={(e) => setNodeForm((prev) => ({ ...prev, y: e.target.value }))}
                    style={inputStyle}
                  />
                </div>
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowNodeForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Add Node
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Connection Modal */}
      {showConnectionForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Add Connection</h3>
              <button onClick={() => setShowConnectionForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleAddConnection} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Source Node *</label>
                <select
                  value={connectionForm.source_node}
                  onChange={(e) =>
                    setConnectionForm((prev) => ({ ...prev, source_node: e.target.value }))
                  }
                  style={inputStyle}
                  required
                >
                  <option value="">Select source...</option>
                  {selectedTopology?.nodes?.map((node) => (
                    <option key={node.node_id} value={node.node_id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Target Node *</label>
                <select
                  value={connectionForm.target_node}
                  onChange={(e) =>
                    setConnectionForm((prev) => ({ ...prev, target_node: e.target.value }))
                  }
                  style={inputStyle}
                  required
                >
                  <option value="">Select target...</option>
                  {selectedTopology?.nodes?.map((node) => (
                    <option key={node.node_id} value={node.node_id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Connection Type *</label>
                <select
                  value={connectionForm.connection_type}
                  onChange={(e) =>
                    setConnectionForm((prev) => ({ ...prev, connection_type: e.target.value }))
                  }
                  style={inputStyle}
                  required
                >
                  <option value="">Select type...</option>
                  {connectionTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Bandwidth</label>
                  <input
                    type="text"
                    value={connectionForm.bandwidth}
                    onChange={(e) =>
                      setConnectionForm((prev) => ({ ...prev, bandwidth: e.target.value }))
                    }
                    style={inputStyle}
                    placeholder="100Mbps"
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Latency</label>
                  <input
                    type="text"
                    value={connectionForm.latency}
                    onChange={(e) =>
                      setConnectionForm((prev) => ({ ...prev, latency: e.target.value }))
                    }
                    style={inputStyle}
                    placeholder="5ms"
                  />
                </div>
              </div>
              <div style={formActionsStyle}>
                <button
                  type="button"
                  onClick={() => setShowConnectionForm(false)}
                  style={secondaryButtonStyle}
                >
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Add Connection
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

const layoutStyle = {
  display: 'flex',
  gap: '20px',
  minHeight: '600px',
};

const sidebarStyle = {
  width: '250px',
  backgroundColor: 'white',
  borderRadius: '8px',
  padding: '16px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const sidebarHeaderStyle = {
  marginTop: 0,
  marginBottom: '12px',
  fontSize: '16px',
};

const listStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const listItemStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px',
  borderRadius: '4px',
  cursor: 'pointer',
  border: '1px solid #e9ecef',
};

const listItemContentStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

const topologyNameStyle = {
  fontWeight: '500',
  fontSize: '14px',
};

const nodeCountStyle = {
  fontSize: '12px',
  color: '#666',
};

const editorAreaStyle = {
  flex: 1,
  backgroundColor: 'white',
  borderRadius: '8px',
  padding: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const editorHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  marginBottom: '20px',
};

const editorActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const descriptionTextStyle = {
  fontSize: '13px',
  color: '#666',
  margin: '4px 0 0 0',
};

const diagramContainerStyle = {
  border: '2px dashed #e9ecef',
  borderRadius: '8px',
  marginBottom: '20px',
  backgroundColor: '#fafafa',
};

const svgStyle = {
  width: '100%',
  height: '400px',
};

const detailsGridStyle = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '16px',
};

const detailsCardStyle = {
  padding: '16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
};

const itemListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  maxHeight: '200px',
  overflowY: 'auto',
};

const itemRowStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px',
  backgroundColor: 'white',
  borderRadius: '4px',
  fontSize: '13px',
};

const itemMetaStyle = {
  marginLeft: 'auto',
  color: '#666',
  fontSize: '12px',
};

const placeholderStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '400px',
  color: '#999',
};

const placeholderIconStyle = {
  fontSize: '64px',
  marginBottom: '16px',
};

const validationBoxStyle = {
  padding: '12px 16px',
  borderRadius: '4px',
  marginBottom: '16px',
};

const issueListStyle = {
  margin: '8px 0 0 0',
  paddingLeft: '20px',
};

const issueItemStyle = {
  fontSize: '13px',
  marginBottom: '4px',
};

const issueSeverityStyle = (severity) => ({
  fontWeight: '600',
  color: severity === 'error' ? '#dc3545' : severity === 'warning' ? '#ffc107' : '#17a2b8',
});

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

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
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

const primaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
};

const secondaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#6c757d',
};

const actionButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#17a2b8',
  padding: '6px 12px',
  fontSize: '13px',
};

const validateButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#ffc107',
  color: '#333',
  padding: '6px 12px',
  fontSize: '13px',
};

const exportButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#6c757d',
  padding: '6px 12px',
  fontSize: '13px',
};

const deleteButtonSmallStyle = {
  padding: '4px 8px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
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
