import React, { useState, useEffect, useCallback } from 'react';
import { integrationsApi } from '../api';

/**
 * Integrations Manager component.
 * Provides UI for managing external integrations including MITRE ATT&CK,
 * log forwarding, and network emulation configurations.
 */
export default function IntegrationsManager({ user }) {
  const [integrations, setIntegrations] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [mitreTactics, setMitreTactics] = useState([]);
  const [mitreTechniques, setMitreTechniques] = useState([]);
  const [mitreMappings, setMitreMappings] = useState([]);
  const [forwardingRules, setForwardingRules] = useState([]);
  const [emulationConfigs, setEmulationConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('integrations');
  const [showCreateIntegrationForm, setShowCreateIntegrationForm] = useState(false);
  const [showCreateMappingForm, setShowCreateMappingForm] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState(null);

  const isAdmin = user?.role === 'admin';
  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form states
  const [integrationForm, setIntegrationForm] = useState({
    integration_type: 'siem',
    name: '',
    config: '{}',
    enabled: true,
  });

  const [mappingForm, setMappingForm] = useState({
    scenario_id: '',
    scenario_name: '',
    techniques: '',
    notes: '',
  });

  // Fetch integrations
  const fetchIntegrations = useCallback(async () => {
    try {
      const response = await integrationsApi.listIntegrations();
      setIntegrations(response.data || []);
    } catch (err) {
      console.error('Failed to load integrations:', err);
    }
  }, []);

  // Fetch statistics
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await integrationsApi.getStatistics();
      setStatistics(response.data);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  }, []);

  // Fetch MITRE tactics
  const fetchMitreTactics = useCallback(async () => {
    try {
      const response = await integrationsApi.getTactics();
      setMitreTactics(response.data || []);
    } catch (err) {
      console.error('Failed to load MITRE tactics:', err);
    }
  }, []);

  // Fetch MITRE techniques
  const fetchMitreTechniques = useCallback(async () => {
    try {
      const response = await integrationsApi.listTechniques();
      setMitreTechniques(response.data || []);
    } catch (err) {
      console.error('Failed to load MITRE techniques:', err);
    }
  }, []);

  // Fetch MITRE mappings
  const fetchMitreMappings = useCallback(async () => {
    try {
      const response = await integrationsApi.listMappings();
      setMitreMappings(response.data || []);
    } catch (err) {
      console.error('Failed to load MITRE mappings:', err);
    }
  }, []);

  // Fetch forwarding rules
  const fetchForwardingRules = useCallback(async () => {
    try {
      const response = await integrationsApi.listForwardingRules();
      setForwardingRules(response.data || []);
    } catch (err) {
      console.error('Failed to load forwarding rules:', err);
    }
  }, []);

  // Fetch emulation configs
  const fetchEmulationConfigs = useCallback(async () => {
    try {
      const response = await integrationsApi.listEmulationConfigs();
      setEmulationConfigs(response.data || []);
    } catch (err) {
      console.error('Failed to load emulation configs:', err);
    }
  }, []);

  // Load all data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchIntegrations(),
        fetchStatistics(),
        fetchMitreTactics(),
        fetchMitreTechniques(),
        fetchMitreMappings(),
        fetchForwardingRules(),
        fetchEmulationConfigs(),
      ]);
    } catch (err) {
      setError('Failed to load integrations data');
    } finally {
      setLoading(false);
    }
  }, [
    fetchIntegrations,
    fetchStatistics,
    fetchMitreTactics,
    fetchMitreTechniques,
    fetchMitreMappings,
    fetchForwardingRules,
    fetchEmulationConfigs,
  ]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Create integration
  const handleCreateIntegration = async (e) => {
    e.preventDefault();
    try {
      let config;
      try {
        config = JSON.parse(integrationForm.config);
      } catch {
        setActionError('Invalid JSON format in configuration. Please check for proper syntax, quotes, and brackets.');
        return;
      }
      await integrationsApi.createIntegration(
        integrationForm.integration_type,
        integrationForm.name,
        config,
        integrationForm.enabled
      );
      setShowCreateIntegrationForm(false);
      setIntegrationForm({
        integration_type: 'siem',
        name: '',
        config: '{}',
        enabled: true,
      });
      setSuccessMessage('Integration created successfully');
      fetchIntegrations();
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create integration: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Test integration
  const handleTestIntegration = async (integrationId) => {
    try {
      const response = await integrationsApi.testIntegration(integrationId);
      if (response.data.success) {
        setSuccessMessage('Integration test passed');
      } else {
        setActionError('Integration test failed: ' + (response.data.error || 'Unknown error'));
      }
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to test integration');
    }
  };

  // Delete integration
  const handleDeleteIntegration = async (integrationId) => {
    if (!window.confirm('Are you sure you want to delete this integration?')) return;
    try {
      await integrationsApi.deleteIntegration(integrationId);
      setSuccessMessage('Integration deleted');
      fetchIntegrations();
      fetchStatistics();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete integration');
    }
  };

  // Create MITRE mapping
  const handleCreateMapping = async (e) => {
    e.preventDefault();
    try {
      const techniques = mappingForm.techniques.split(',').map((t) => t.trim()).filter((t) => t);
      await integrationsApi.createMapping(
        mappingForm.scenario_id,
        mappingForm.scenario_name,
        techniques,
        mappingForm.notes
      );
      setShowCreateMappingForm(false);
      setMappingForm({
        scenario_id: '',
        scenario_name: '',
        techniques: '',
        notes: '',
      });
      setSuccessMessage('MITRE mapping created');
      fetchMitreMappings();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create mapping: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Delete mapping
  const handleDeleteMapping = async (mappingId) => {
    if (!window.confirm('Are you sure you want to delete this mapping?')) return;
    try {
      await integrationsApi.deleteMapping(mappingId);
      setSuccessMessage('Mapping deleted');
      fetchMitreMappings();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete mapping');
    }
  };

  // Delete forwarding rule
  const handleDeleteForwardingRule = async (ruleId) => {
    if (!window.confirm('Are you sure you want to delete this forwarding rule?')) return;
    try {
      await integrationsApi.deleteForwardingRule(ruleId);
      setSuccessMessage('Forwarding rule deleted');
      fetchForwardingRules();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete forwarding rule');
    }
  };

  // Delete emulation config
  const handleDeleteEmulationConfig = async (configId) => {
    if (!window.confirm('Are you sure you want to delete this emulation config?')) return;
    try {
      await integrationsApi.deleteEmulationConfig(configId);
      setSuccessMessage('Emulation config deleted');
      fetchEmulationConfigs();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete emulation config');
    }
  };

  // Get Mininet script
  const handleGetMininetScript = async (configId) => {
    try {
      const response = await integrationsApi.getMininetScript(configId);
      const blob = new Blob([response.data.script], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mininet_${configId}.py`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setActionError('Failed to generate Mininet script');
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  // Get integration type color
  const getIntegrationTypeColor = (type) => {
    const colors = {
      siem: '#007bff',
      log_forwarder: '#28a745',
      network_emulator: '#17a2b8',
      vulnerability_scanner: '#ffc107',
      ticketing: '#6c757d',
    };
    return colors[type] || '#6c757d';
  };

  // Get tactic color
  const getTacticColor = (index) => {
    const colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#20c997', '#17a2b8', '#007bff', '#6f42c1', '#e83e8c'];
    return colors[index % colors.length];
  };

  if (loading) {
    return <div style={containerStyle}>Loading integrations...</div>;
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
        <h2>🔌 External Integrations</h2>
        {isAdmin && (
          <button onClick={() => setShowCreateIntegrationForm(true)} style={primaryButtonStyle}>
            + Add Integration
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

      {/* Statistics */}
      {statistics && (
        <div style={statsGridStyle}>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_integrations || 0}</span>
            <span style={statLabelStyle}>Integrations</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.active_integrations || 0}</span>
            <span style={statLabelStyle}>Active</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_mappings || 0}</span>
            <span style={statLabelStyle}>MITRE Mappings</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.forwarding_rules || 0}</span>
            <span style={statLabelStyle}>Log Rules</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('integrations')}
          style={activeTab === 'integrations' ? tabActiveStyle : tabStyle}
        >
          🔌 Integrations ({integrations.length})
        </button>
        <button
          onClick={() => setActiveTab('mitre')}
          style={activeTab === 'mitre' ? tabActiveStyle : tabStyle}
        >
          🎯 MITRE ATT&CK
        </button>
        <button
          onClick={() => setActiveTab('logging')}
          style={activeTab === 'logging' ? tabActiveStyle : tabStyle}
        >
          📋 Log Forwarding ({forwardingRules.length})
        </button>
        <button
          onClick={() => setActiveTab('emulation')}
          style={activeTab === 'emulation' ? tabActiveStyle : tabStyle}
        >
          🌐 Network Emulation ({emulationConfigs.length})
        </button>
      </div>

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <div style={tabContentStyle}>
          {integrations.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>🔌</span>
              <p>No integrations configured. Add your first integration.</p>
            </div>
          ) : (
            <div style={integrationGridStyle}>
              {integrations.map((integration) => (
                <div key={integration.integration_id} style={integrationCardStyle}>
                  <div style={integrationHeaderStyle}>
                    <span
                      style={{
                        ...integrationTypeBadgeStyle,
                        backgroundColor: getIntegrationTypeColor(integration.integration_type),
                      }}
                    >
                      {integration.integration_type}
                    </span>
                    <span style={integration.enabled ? enabledBadgeStyle : disabledBadgeStyle}>
                      {integration.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <h4 style={integrationNameStyle}>{integration.name}</h4>
                  <div style={integrationMetaStyle}>
                    <span>Created: {formatDate(integration.created_at)}</span>
                  </div>
                  <div style={integrationActionsStyle}>
                    <button
                      onClick={() => handleTestIntegration(integration.integration_id)}
                      style={testButtonStyle}
                    >
                      Test
                    </button>
                    <button
                      onClick={() => setSelectedIntegration(integration)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => handleDeleteIntegration(integration.integration_id)}
                        style={deleteButtonStyle}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MITRE ATT&CK Tab */}
      {activeTab === 'mitre' && (
        <div style={tabContentStyle}>
          <div style={mitreHeaderStyle}>
            <h4>MITRE ATT&CK Framework</h4>
            {isInstructor && (
              <button onClick={() => setShowCreateMappingForm(true)} style={addButtonStyle}>
                + Create Mapping
              </button>
            )}
          </div>

          {/* Tactics Overview */}
          <div style={tacticsContainerStyle}>
            <h5>Tactics</h5>
            <div style={tacticsGridStyle}>
              {mitreTactics.map((tactic, idx) => (
                <div key={tactic.tactic_id || idx} style={tacticCardStyle}>
                  <div
                    style={{
                      ...tacticIconStyle,
                      backgroundColor: getTacticColor(idx),
                    }}
                  >
                    {tactic.short_name?.charAt(0) || 'T'}
                  </div>
                  <div style={tacticInfoStyle}>
                    <span style={tacticNameStyle}>{tactic.name}</span>
                    <span style={tacticIdStyle}>{tactic.tactic_id}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Scenario Mappings */}
          <div style={mappingsContainerStyle}>
            <h5>Scenario Mappings ({mitreMappings.length})</h5>
            {mitreMappings.length === 0 ? (
              <p style={emptyTextStyle}>No scenario mappings created yet.</p>
            ) : (
              <div style={mappingsListStyle}>
                {mitreMappings.map((mapping) => (
                  <div key={mapping.mapping_id} style={mappingCardStyle}>
                    <div style={mappingHeaderStyle}>
                      <span style={mappingScenarioStyle}>{mapping.scenario_name}</span>
                      <span style={mappingTechCountStyle}>
                        {mapping.techniques?.length || 0} techniques
                      </span>
                    </div>
                    <div style={mappingTechniquesStyle}>
                      {mapping.techniques?.slice(0, 5).map((tech, idx) => (
                        <span key={idx} style={techniqueBadgeStyle}>
                          {tech}
                        </span>
                      ))}
                      {mapping.techniques?.length > 5 && (
                        <span style={moreBadgeStyle}>+{mapping.techniques.length - 5} more</span>
                      )}
                    </div>
                    {mapping.notes && (
                      <p style={mappingNotesStyle}>{mapping.notes}</p>
                    )}
                    <div style={mappingFooterStyle}>
                      <span>Created: {formatDate(mapping.created_at)}</span>
                      {isInstructor && (
                        <button
                          onClick={() => handleDeleteMapping(mapping.mapping_id)}
                          style={deleteMappingButtonStyle}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Techniques Browser */}
          <div style={techniquesContainerStyle}>
            <h5>Techniques ({mitreTechniques.length})</h5>
            <div style={techniquesGridStyle}>
              {mitreTechniques.slice(0, 20).map((technique) => (
                <div key={technique.technique_id} style={techniqueCardStyle}>
                  <span style={techniqueIdBadgeStyle}>{technique.technique_id}</span>
                  <span style={techniqueNameTextStyle}>{technique.name}</span>
                </div>
              ))}
              {mitreTechniques.length > 20 && (
                <div style={moreItemsStyle}>
                  And {mitreTechniques.length - 20} more techniques...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Log Forwarding Tab */}
      {activeTab === 'logging' && (
        <div style={tabContentStyle}>
          {forwardingRules.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>📋</span>
              <p>No log forwarding rules configured.</p>
            </div>
          ) : (
            <div style={rulesListStyle}>
              {forwardingRules.map((rule) => (
                <div key={rule.rule_id} style={ruleCardStyle}>
                  <div style={ruleHeaderStyle}>
                    <span style={ruleNameStyle}>{rule.name}</span>
                    <span style={rule.enabled ? enabledBadgeStyle : disabledBadgeStyle}>
                      {rule.enabled ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div style={ruleDetailsStyle}>
                    <div style={ruleDetailRowStyle}>
                      <span>Integration:</span>
                      <strong>{rule.integration_name || rule.integration_id}</strong>
                    </div>
                    <div style={ruleDetailRowStyle}>
                      <span>Log Levels:</span>
                      <strong>{rule.log_levels?.join(', ') || 'All'}</strong>
                    </div>
                    <div style={ruleDetailRowStyle}>
                      <span>Batch Size:</span>
                      <strong>{rule.batch_size || 100}</strong>
                    </div>
                    <div style={ruleDetailRowStyle}>
                      <span>Flush Interval:</span>
                      <strong>{rule.flush_interval || 30}s</strong>
                    </div>
                  </div>
                  {isAdmin && (
                    <button
                      onClick={() => handleDeleteForwardingRule(rule.rule_id)}
                      style={deleteRuleButtonStyle}
                    >
                      Delete Rule
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Network Emulation Tab */}
      {activeTab === 'emulation' && (
        <div style={tabContentStyle}>
          {emulationConfigs.length === 0 ? (
            <div style={emptyStateStyle}>
              <span style={emptyIconStyle}>🌐</span>
              <p>No network emulation configurations found.</p>
            </div>
          ) : (
            <div style={emulationGridStyle}>
              {emulationConfigs.map((config) => (
                <div key={config.config_id} style={emulationCardStyle}>
                  <div style={emulationHeaderStyle}>
                    <span style={emulationNameStyle}>{config.name}</span>
                    <span style={emulatorTypeBadgeStyle}>{config.emulator_type}</span>
                  </div>
                  <div style={emulationDetailsStyle}>
                    <div style={emulationDetailRowStyle}>
                      <span>Topology:</span>
                      <strong>{config.topology_id?.substring(0, 8)}...</strong>
                    </div>
                    <div style={emulationDetailRowStyle}>
                      <span>Controller:</span>
                      <strong>{config.controller || 'default'}</strong>
                    </div>
                  </div>
                  <div style={emulationActionsStyle}>
                    <button
                      onClick={() => handleGetMininetScript(config.config_id)}
                      style={scriptButtonStyle}
                    >
                      📄 Get Script
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => handleDeleteEmulationConfig(config.config_id)}
                        style={deleteEmulationButtonStyle}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Integration Modal */}
      {showCreateIntegrationForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Add Integration</h3>
              <button onClick={() => setShowCreateIntegrationForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateIntegration} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Integration Type *</label>
                <select
                  value={integrationForm.integration_type}
                  onChange={(e) =>
                    setIntegrationForm((prev) => ({ ...prev, integration_type: e.target.value }))
                  }
                  style={inputStyle}
                  required
                >
                  <option value="siem">SIEM</option>
                  <option value="log_forwarder">Log Forwarder</option>
                  <option value="network_emulator">Network Emulator</option>
                  <option value="vulnerability_scanner">Vulnerability Scanner</option>
                  <option value="ticketing">Ticketing System</option>
                </select>
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Name *</label>
                <input
                  type="text"
                  value={integrationForm.name}
                  onChange={(e) => setIntegrationForm((prev) => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Splunk SIEM"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Configuration (JSON) *</label>
                <textarea
                  value={integrationForm.config}
                  onChange={(e) => setIntegrationForm((prev) => ({ ...prev, config: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '120px', fontFamily: 'monospace' }}
                  placeholder='{"url": "https://...", "api_key": "..."}'
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={checkboxLabelStyle}>
                  <input
                    type="checkbox"
                    checked={integrationForm.enabled}
                    onChange={(e) =>
                      setIntegrationForm((prev) => ({ ...prev, enabled: e.target.checked }))
                    }
                    style={checkboxStyle}
                  />
                  Enabled
                </label>
              </div>
              <div style={formActionsStyle}>
                <button
                  type="button"
                  onClick={() => setShowCreateIntegrationForm(false)}
                  style={secondaryButtonStyle}
                >
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Integration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Mapping Modal */}
      {showCreateMappingForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Create MITRE Mapping</h3>
              <button onClick={() => setShowCreateMappingForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateMapping} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Scenario ID *</label>
                <input
                  type="text"
                  value={mappingForm.scenario_id}
                  onChange={(e) => setMappingForm((prev) => ({ ...prev, scenario_id: e.target.value }))}
                  style={inputStyle}
                  placeholder="Scenario UUID"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Scenario Name *</label>
                <input
                  type="text"
                  value={mappingForm.scenario_name}
                  onChange={(e) => setMappingForm((prev) => ({ ...prev, scenario_name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Network Reconnaissance"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Techniques (comma-separated) *</label>
                <textarea
                  value={mappingForm.techniques}
                  onChange={(e) => setMappingForm((prev) => ({ ...prev, techniques: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="T1595, T1592, T1589..."
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Notes</label>
                <textarea
                  value={mappingForm.notes}
                  onChange={(e) => setMappingForm((prev) => ({ ...prev, notes: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '60px' }}
                  placeholder="Additional notes about this mapping..."
                />
              </div>
              <div style={formActionsStyle}>
                <button
                  type="button"
                  onClick={() => setShowCreateMappingForm(false)}
                  style={secondaryButtonStyle}
                >
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Mapping
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Integration Details Modal */}
      {selectedIntegration && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Integration Details</h3>
              <button onClick={() => setSelectedIntegration(null)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <div style={modalBodyStyle}>
              <div style={detailRowStyle}>
                <span>Name:</span>
                <strong>{selectedIntegration.name}</strong>
              </div>
              <div style={detailRowStyle}>
                <span>Type:</span>
                <span
                  style={{
                    ...integrationTypeBadgeStyle,
                    backgroundColor: getIntegrationTypeColor(selectedIntegration.integration_type),
                  }}
                >
                  {selectedIntegration.integration_type}
                </span>
              </div>
              <div style={detailRowStyle}>
                <span>Status:</span>
                <span style={selectedIntegration.enabled ? enabledBadgeStyle : disabledBadgeStyle}>
                  {selectedIntegration.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div style={detailRowStyle}>
                <span>Created:</span>
                <strong>{formatDate(selectedIntegration.created_at)}</strong>
              </div>
              {selectedIntegration.last_sync_at && (
                <div style={detailRowStyle}>
                  <span>Last Sync:</span>
                  <strong>{formatDate(selectedIntegration.last_sync_at)}</strong>
                </div>
              )}
              <div style={{ marginTop: '16px' }}>
                <label style={labelStyle}>Configuration:</label>
                <pre style={configPreStyle}>
                  {JSON.stringify(selectedIntegration.config, null, 2)}
                </pre>
              </div>
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

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
};

const integrationGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '16px',
};

const integrationCardStyle = {
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  padding: '16px',
  border: '1px solid #e9ecef',
};

const integrationHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px',
};

const integrationTypeBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
  textTransform: 'uppercase',
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

const integrationNameStyle = {
  margin: '0 0 8px 0',
  fontSize: '16px',
};

const integrationMetaStyle = {
  fontSize: '12px',
  color: '#666',
  marginBottom: '12px',
};

const integrationActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const testButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const viewButtonStyle = {
  ...testButtonStyle,
  backgroundColor: '#007bff',
};

const deleteButtonStyle = {
  ...testButtonStyle,
  backgroundColor: '#dc3545',
};

// MITRE styles
const mitreHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '20px',
};

const tacticsContainerStyle = {
  marginBottom: '24px',
};

const tacticsGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
  gap: '12px',
  marginTop: '12px',
};

const tacticCardStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
};

const tacticIconStyle = {
  width: '36px',
  height: '36px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'white',
  fontWeight: 'bold',
  fontSize: '14px',
};

const tacticInfoStyle = {
  flex: 1,
};

const tacticNameStyle = {
  display: 'block',
  fontWeight: '500',
  fontSize: '13px',
};

const tacticIdStyle = {
  display: 'block',
  fontSize: '11px',
  color: '#666',
};

const mappingsContainerStyle = {
  marginBottom: '24px',
};

const mappingsListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  marginTop: '12px',
};

const mappingCardStyle = {
  padding: '16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  border: '1px solid #e9ecef',
};

const mappingHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const mappingScenarioStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const mappingTechCountStyle = {
  fontSize: '12px',
  color: '#666',
};

const mappingTechniquesStyle = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '8px',
  marginBottom: '8px',
};

const techniqueBadgeStyle = {
  padding: '4px 8px',
  backgroundColor: '#dc3545',
  color: 'white',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
};

const moreBadgeStyle = {
  ...techniqueBadgeStyle,
  backgroundColor: '#6c757d',
};

const mappingNotesStyle = {
  fontSize: '12px',
  color: '#666',
  fontStyle: 'italic',
  marginBottom: '8px',
};

const mappingFooterStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: '11px',
  color: '#666',
  paddingTop: '8px',
  borderTop: '1px solid #e9ecef',
};

const deleteMappingButtonStyle = {
  padding: '4px 8px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '11px',
};

const techniquesContainerStyle = {
  marginBottom: '16px',
};

const techniquesGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
  gap: '8px',
  marginTop: '12px',
};

const techniqueCardStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  fontSize: '12px',
};

const techniqueIdBadgeStyle = {
  padding: '2px 6px',
  backgroundColor: '#dc3545',
  color: 'white',
  borderRadius: '4px',
  fontSize: '10px',
  fontWeight: 'bold',
};

const techniqueNameTextStyle = {
  flex: 1,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const moreItemsStyle = {
  padding: '12px',
  textAlign: 'center',
  color: '#666',
  fontStyle: 'italic',
};

// Log forwarding styles
const rulesListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const ruleCardStyle = {
  padding: '16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  border: '1px solid #e9ecef',
};

const ruleHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const ruleNameStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const ruleDetailsStyle = {
  marginBottom: '12px',
};

const ruleDetailRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  marginBottom: '4px',
  color: '#666',
};

const deleteRuleButtonStyle = {
  width: '100%',
  padding: '8px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

// Network emulation styles
const emulationGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '16px',
};

const emulationCardStyle = {
  padding: '16px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  border: '1px solid #e9ecef',
};

const emulationHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const emulationNameStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const emulatorTypeBadgeStyle = {
  padding: '4px 8px',
  backgroundColor: '#17a2b8',
  color: 'white',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
};

const emulationDetailsStyle = {
  marginBottom: '12px',
};

const emulationDetailRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  marginBottom: '4px',
  color: '#666',
};

const emulationActionsStyle = {
  display: 'flex',
  gap: '8px',
};

const scriptButtonStyle = {
  flex: 1,
  padding: '8px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const deleteEmulationButtonStyle = {
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

const modalBodyStyle = {
  padding: '16px',
};

const detailRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 0',
  borderBottom: '1px solid #eee',
  fontSize: '14px',
};

const configPreStyle = {
  backgroundColor: '#f8f9fa',
  padding: '12px',
  borderRadius: '4px',
  fontSize: '12px',
  fontFamily: 'monospace',
  overflow: 'auto',
  maxHeight: '200px',
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

const checkboxLabelStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '14px',
  cursor: 'pointer',
};

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
  boxSizing: 'border-box',
};

const checkboxStyle = {
  width: '18px',
  height: '18px',
};

const formActionsStyle = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '8px',
  marginTop: '16px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
};
