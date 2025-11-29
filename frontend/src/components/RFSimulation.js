import React, { useState, useEffect, useCallback } from 'react';
import { rfSimulationApi } from '../api';

/**
 * RF/EW Simulation Dashboard component.
 * Provides a simulated radio frequency and electronic warfare training environment.
 * SAFETY: All operations are SIMULATED - no real RF transmission occurs.
 */
export default function RFSimulation({ user }) {
  const [simulations, setSimulations] = useState([]);
  const [selectedSimulation, setSelectedSimulation] = useState(null);
  const [frequencyBands, setFrequencyBands] = useState([]);
  const [predefinedThreats, setPredefinedThreats] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showSignalForm, setShowSignalForm] = useState(false);
  const [showJammingForm, setShowJammingForm] = useState(false);
  const [spectrumData, setSpectrumData] = useState(null);

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form states
  const [simulationForm, setSimulationForm] = useState({
    name: '',
    description: '',
  });

  const [signalForm, setSignalForm] = useState({
    name: '',
    signal_type: 'communication',
    frequency_hz: 100000000,
    bandwidth_hz: 10000,
    power_dbm: -30,
    modulation: 'AM',
  });

  const [jammingForm, setJammingForm] = useState({
    name: '',
    jamming_type: 'barrage',
    target_freq_hz: 100000000,
    bandwidth_hz: 50000,
    power_dbm: -20,
    duration_seconds: 60,
  });

  // Fetch simulations
  const fetchSimulations = useCallback(async () => {
    try {
      setLoading(true);
      const response = await rfSimulationApi.listSimulations();
      setSimulations(response.data || []);
    } catch (err) {
      console.error('Failed to load simulations:', err);
      setError('Failed to load simulations');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch reference data
  const fetchReferenceData = useCallback(async () => {
    try {
      const [bandsRes, threatsRes, statsRes] = await Promise.all([
        rfSimulationApi.getFrequencyBands(),
        rfSimulationApi.getPredefinedThreats(),
        isInstructor ? rfSimulationApi.getStatistics() : Promise.resolve({ data: null }),
      ]);
      setFrequencyBands(bandsRes.data || []);
      setPredefinedThreats(threatsRes.data || []);
      if (statsRes.data) setStatistics(statsRes.data);
    } catch (err) {
      console.error('Failed to load reference data:', err);
    }
  }, [isInstructor]);

  useEffect(() => {
    fetchSimulations();
    fetchReferenceData();
  }, [fetchSimulations, fetchReferenceData]);

  // Load simulation details
  const handleSelectSimulation = async (simulationId) => {
    try {
      const response = await rfSimulationApi.getSimulation(simulationId);
      setSelectedSimulation(response.data);
      setActiveTab('signals');
    } catch (err) {
      setActionError('Failed to load simulation details');
    }
  };

  // Create new simulation
  const handleCreateSimulation = async (e) => {
    e.preventDefault();
    try {
      const response = await rfSimulationApi.createSimulation(
        simulationForm.name,
        simulationForm.description
      );
      setShowCreateForm(false);
      setSimulationForm({ name: '', description: '' });
      setSuccessMessage('Simulation created successfully');
      fetchSimulations();
      setSelectedSimulation(response.data);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to create simulation: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Start/Stop/Pause simulation
  const handleStartSimulation = async () => {
    if (!selectedSimulation) return;
    try {
      const response = await rfSimulationApi.startSimulation(selectedSimulation.simulation_id);
      setSelectedSimulation(response.data);
      setSuccessMessage('Simulation started');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to start simulation');
    }
  };

  const handlePauseSimulation = async () => {
    if (!selectedSimulation) return;
    try {
      const response = await rfSimulationApi.pauseSimulation(selectedSimulation.simulation_id);
      setSelectedSimulation(response.data);
      setSuccessMessage('Simulation paused');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to pause simulation');
    }
  };

  const handleStopSimulation = async () => {
    if (!selectedSimulation) return;
    try {
      const response = await rfSimulationApi.stopSimulation(selectedSimulation.simulation_id);
      setSelectedSimulation(response.data);
      setSuccessMessage('Simulation stopped');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to stop simulation');
    }
  };

  // Add signal
  const handleAddSignal = async (e) => {
    e.preventDefault();
    if (!selectedSimulation) return;

    try {
      await rfSimulationApi.addSignal(
        selectedSimulation.simulation_id,
        signalForm.name,
        signalForm.signal_type,
        parseFloat(signalForm.frequency_hz),
        parseFloat(signalForm.bandwidth_hz),
        parseFloat(signalForm.power_dbm),
        signalForm.modulation
      );
      setShowSignalForm(false);
      setSignalForm({
        name: '',
        signal_type: 'communication',
        frequency_hz: 100000000,
        bandwidth_hz: 10000,
        power_dbm: -30,
        modulation: 'AM',
      });
      await handleSelectSimulation(selectedSimulation.simulation_id);
      setSuccessMessage('Signal added');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to add signal: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Add jamming
  const handleAddJamming = async (e) => {
    e.preventDefault();
    if (!selectedSimulation) return;

    try {
      await rfSimulationApi.addJamming(
        selectedSimulation.simulation_id,
        jammingForm.name,
        jammingForm.jamming_type,
        parseFloat(jammingForm.target_freq_hz),
        parseFloat(jammingForm.bandwidth_hz),
        parseFloat(jammingForm.power_dbm),
        jammingForm.duration_seconds ? parseFloat(jammingForm.duration_seconds) : null
      );
      setShowJammingForm(false);
      setJammingForm({
        name: '',
        jamming_type: 'barrage',
        target_freq_hz: 100000000,
        bandwidth_hz: 50000,
        power_dbm: -20,
        duration_seconds: 60,
      });
      await handleSelectSimulation(selectedSimulation.simulation_id);
      setSuccessMessage('Jamming effect added');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to add jamming: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Add predefined threat
  const handleAddThreat = async (threatId) => {
    if (!selectedSimulation) return;

    try {
      await rfSimulationApi.addThreat(selectedSimulation.simulation_id, threatId);
      await handleSelectSimulation(selectedSimulation.simulation_id);
      setSuccessMessage('Threat added to simulation');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to add threat');
    }
  };

  // Capture spectrum
  const handleCaptureSpectrum = async () => {
    if (!selectedSimulation) return;

    try {
      const response = await rfSimulationApi.captureSpectrum(
        selectedSimulation.simulation_id,
        100000000, // center frequency
        50000000,  // bandwidth
        1024       // FFT size
      );
      setSpectrumData(response.data);
      setSuccessMessage('Spectrum captured');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to capture spectrum');
    }
  };

  // Delete signal
  const handleDeleteSignal = async (signalId) => {
    if (!selectedSimulation) return;
    try {
      await rfSimulationApi.removeSignal(selectedSimulation.simulation_id, signalId);
      await handleSelectSimulation(selectedSimulation.simulation_id);
      setSuccessMessage('Signal removed');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to remove signal');
    }
  };

  // Delete jamming
  const handleDeleteJamming = async (effectId) => {
    if (!selectedSimulation) return;
    try {
      await rfSimulationApi.removeJamming(selectedSimulation.simulation_id, effectId);
      await handleSelectSimulation(selectedSimulation.simulation_id);
      setSuccessMessage('Jamming effect removed');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to remove jamming');
    }
  };

  // Delete simulation
  const handleDeleteSimulation = async (simulationId) => {
    if (!window.confirm('Are you sure you want to delete this simulation?')) return;
    try {
      await rfSimulationApi.deleteSimulation(simulationId);
      if (selectedSimulation?.simulation_id === simulationId) {
        setSelectedSimulation(null);
      }
      fetchSimulations();
      setSuccessMessage('Simulation deleted');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setActionError('Failed to delete simulation');
    }
  };

  // Format frequency
  const formatFrequency = (hz) => {
    if (hz >= 1e9) return `${(hz / 1e9).toFixed(2)} GHz`;
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(2)} MHz`;
    if (hz >= 1e3) return `${(hz / 1e3).toFixed(2)} kHz`;
    return `${hz} Hz`;
  };

  // Get status color
  const getStatusColor = (status) => {
    const colors = {
      created: '#6c757d',
      running: '#28a745',
      paused: '#ffc107',
      stopped: '#dc3545',
    };
    return colors[status] || '#6c757d';
  };

  if (loading) {
    return <div style={containerStyle}>Loading RF/EW simulation...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={fetchSimulations} style={buttonStyle}>Retry</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Safety Banner */}
      <div style={safetyBannerStyle}>
        ⚠️ <strong>SIMULATION ONLY</strong> - All RF operations are simulated. No real radio frequency transmission occurs.
      </div>

      <div style={headerStyle}>
        <h2>📡 RF/EW Simulation Environment</h2>
        {isInstructor && (
          <button onClick={() => setShowCreateForm(true)} style={primaryButtonStyle}>
            + New Simulation
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

      {/* Statistics Panel */}
      {statistics && (
        <div style={statsGridStyle}>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_simulations || 0}</span>
            <span style={statLabelStyle}>Total Simulations</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.active_simulations || 0}</span>
            <span style={statLabelStyle}>Active</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_signals || 0}</span>
            <span style={statLabelStyle}>Total Signals</span>
          </div>
          <div style={statCardStyle}>
            <span style={statValueStyle}>{statistics.total_jamming_effects || 0}</span>
            <span style={statLabelStyle}>Jamming Effects</span>
          </div>
        </div>
      )}

      <div style={layoutStyle}>
        {/* Simulations List */}
        <div style={sidebarStyle}>
          <h3 style={sidebarHeaderStyle}>Simulations</h3>
          {simulations.length === 0 ? (
            <p style={emptyTextStyle}>No simulations created yet.</p>
          ) : (
            <div style={listStyle}>
              {simulations.map((sim) => (
                <div
                  key={sim.simulation_id}
                  style={{
                    ...listItemStyle,
                    backgroundColor:
                      selectedSimulation?.simulation_id === sim.simulation_id
                        ? '#e3f2fd'
                        : 'white',
                  }}
                  onClick={() => handleSelectSimulation(sim.simulation_id)}
                >
                  <div style={listItemContentStyle}>
                    <span style={simNameStyle}>{sim.name}</span>
                    <div style={simMetaStyle}>
                      <span style={{ ...statusBadgeStyle, backgroundColor: getStatusColor(sim.status) }}>
                        {sim.status}
                      </span>
                    </div>
                  </div>
                  {isInstructor && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSimulation(sim.simulation_id);
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

          {/* Frequency Bands Reference */}
          <h4 style={{ marginTop: '24px', marginBottom: '12px' }}>📊 Frequency Bands</h4>
          <div style={bandsListStyle}>
            {frequencyBands.slice(0, 5).map((band, idx) => (
              <div key={idx} style={bandItemStyle}>
                <span style={bandNameStyle}>{band.name}</span>
                <span style={bandRangeStyle}>
                  {formatFrequency(band.min_freq)} - {formatFrequency(band.max_freq)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Main Content Area */}
        <div style={mainContentStyle}>
          {selectedSimulation ? (
            <>
              {/* Simulation Header */}
              <div style={simHeaderStyle}>
                <div>
                  <h3>{selectedSimulation.name}</h3>
                  <p style={descriptionTextStyle}>{selectedSimulation.description}</p>
                  <span style={{ ...statusBadgeStyle, backgroundColor: getStatusColor(selectedSimulation.status) }}>
                    {selectedSimulation.status}
                  </span>
                </div>
                <div style={simControlsStyle}>
                  {isInstructor && (
                    <>
                      {selectedSimulation.status !== 'running' && (
                        <button onClick={handleStartSimulation} style={startButtonStyle}>
                          ▶ Start
                        </button>
                      )}
                      {selectedSimulation.status === 'running' && (
                        <button onClick={handlePauseSimulation} style={pauseButtonStyle}>
                          ⏸ Pause
                        </button>
                      )}
                      {selectedSimulation.status !== 'stopped' && (
                        <button onClick={handleStopSimulation} style={stopButtonStyle}>
                          ⏹ Stop
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Tabs */}
              <div style={tabsStyle}>
                <button
                  onClick={() => setActiveTab('signals')}
                  style={activeTab === 'signals' ? tabActiveStyle : tabStyle}
                >
                  📻 Signals
                </button>
                <button
                  onClick={() => setActiveTab('jamming')}
                  style={activeTab === 'jamming' ? tabActiveStyle : tabStyle}
                >
                  🔇 Jamming
                </button>
                <button
                  onClick={() => setActiveTab('threats')}
                  style={activeTab === 'threats' ? tabActiveStyle : tabStyle}
                >
                  ⚠️ Threats
                </button>
                <button
                  onClick={() => setActiveTab('spectrum')}
                  style={activeTab === 'spectrum' ? tabActiveStyle : tabStyle}
                >
                  📊 Spectrum
                </button>
              </div>

              {/* Signals Tab */}
              {activeTab === 'signals' && (
                <div style={tabContentStyle}>
                  <div style={tabHeaderStyle}>
                    <h4>Signals ({selectedSimulation.signals?.length || 0})</h4>
                    {isInstructor && (
                      <button onClick={() => setShowSignalForm(true)} style={addButtonStyle}>
                        + Add Signal
                      </button>
                    )}
                  </div>
                  {selectedSimulation.signals?.length === 0 ? (
                    <p style={emptyTextStyle}>No signals in this simulation.</p>
                  ) : (
                    <div style={itemGridStyle}>
                      {selectedSimulation.signals?.map((signal) => (
                        <div key={signal.signal_id} style={signalCardStyle}>
                          <div style={cardHeaderStyle}>
                            <span style={signalNameStyle}>{signal.name}</span>
                            <span style={signalTypeBadgeStyle}>{signal.signal_type}</span>
                          </div>
                          <div style={cardBodyStyle}>
                            <div style={signalDetailStyle}>
                              <span>Frequency:</span>
                              <strong>{formatFrequency(signal.frequency_hz)}</strong>
                            </div>
                            <div style={signalDetailStyle}>
                              <span>Bandwidth:</span>
                              <strong>{formatFrequency(signal.bandwidth_hz)}</strong>
                            </div>
                            <div style={signalDetailStyle}>
                              <span>Power:</span>
                              <strong>{signal.power_dbm} dBm</strong>
                            </div>
                            <div style={signalDetailStyle}>
                              <span>Modulation:</span>
                              <strong>{signal.modulation}</strong>
                            </div>
                          </div>
                          {isInstructor && (
                            <button
                              onClick={() => handleDeleteSignal(signal.signal_id)}
                              style={deleteButtonStyle}
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Jamming Tab */}
              {activeTab === 'jamming' && (
                <div style={tabContentStyle}>
                  <div style={tabHeaderStyle}>
                    <h4>Jamming Effects ({selectedSimulation.jamming_effects?.length || 0})</h4>
                    {isInstructor && (
                      <button onClick={() => setShowJammingForm(true)} style={addButtonStyle}>
                        + Add Jamming
                      </button>
                    )}
                  </div>
                  {selectedSimulation.jamming_effects?.length === 0 ? (
                    <p style={emptyTextStyle}>No jamming effects in this simulation.</p>
                  ) : (
                    <div style={itemGridStyle}>
                      {selectedSimulation.jamming_effects?.map((effect) => (
                        <div key={effect.effect_id} style={jammingCardStyle}>
                          <div style={cardHeaderStyle}>
                            <span style={signalNameStyle}>{effect.name}</span>
                            <span style={jammingTypeBadgeStyle}>{effect.jamming_type}</span>
                          </div>
                          <div style={cardBodyStyle}>
                            <div style={signalDetailStyle}>
                              <span>Target Freq:</span>
                              <strong>{formatFrequency(effect.target_freq_hz)}</strong>
                            </div>
                            <div style={signalDetailStyle}>
                              <span>Bandwidth:</span>
                              <strong>{formatFrequency(effect.bandwidth_hz)}</strong>
                            </div>
                            <div style={signalDetailStyle}>
                              <span>Power:</span>
                              <strong>{effect.power_dbm} dBm</strong>
                            </div>
                          </div>
                          {isInstructor && (
                            <button
                              onClick={() => handleDeleteJamming(effect.effect_id)}
                              style={deleteButtonStyle}
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Threats Tab */}
              {activeTab === 'threats' && (
                <div style={tabContentStyle}>
                  <div style={tabHeaderStyle}>
                    <h4>Active Threats ({selectedSimulation.threats?.length || 0})</h4>
                  </div>
                  
                  {/* Active threats */}
                  {selectedSimulation.threats?.length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h5>In Simulation</h5>
                      <div style={itemGridStyle}>
                        {selectedSimulation.threats?.map((threat) => (
                          <div key={threat.threat_id} style={threatCardStyle}>
                            <span style={threatNameStyle}>{threat.name}</span>
                            <span style={threatTypeBadgeStyle}>{threat.threat_type}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Predefined threats to add */}
                  <h5>Available Threats</h5>
                  <div style={itemGridStyle}>
                    {predefinedThreats.map((threat) => (
                      <div key={threat.threat_id} style={threatCardStyle}>
                        <div style={threatInfoStyle}>
                          <span style={threatNameStyle}>{threat.name}</span>
                          <span style={threatDescStyle}>{threat.description}</span>
                        </div>
                        {isInstructor && (
                          <button
                            onClick={() => handleAddThreat(threat.threat_id)}
                            style={addThreatButtonStyle}
                          >
                            Add
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Spectrum Tab */}
              {activeTab === 'spectrum' && (
                <div style={tabContentStyle}>
                  <div style={tabHeaderStyle}>
                    <h4>Spectrum Analysis</h4>
                    <button onClick={handleCaptureSpectrum} style={addButtonStyle}>
                      📷 Capture Spectrum
                    </button>
                  </div>
                  
                  {spectrumData ? (
                    <div style={spectrumDisplayStyle}>
                      <div style={spectrumHeaderStyle}>
                        <span>Center: {formatFrequency(spectrumData.center_freq_hz)}</span>
                        <span>Span: {formatFrequency(spectrumData.bandwidth_hz)}</span>
                        <span>FFT Size: {spectrumData.fft_size}</span>
                      </div>
                      <div style={spectrumVisualizationStyle}>
                        {/* Simple bar visualization of spectrum data */}
                        <svg style={spectrumSvgStyle} viewBox="0 0 1024 200">
                          {spectrumData.power_spectrum?.map((power, idx) => {
                            const height = Math.max(0, Math.min(180, (power + 100) * 1.8));
                            return (
                              <rect
                                key={idx}
                                x={idx}
                                y={200 - height}
                                width="1"
                                height={height}
                                fill="#007bff"
                              />
                            );
                          })}
                        </svg>
                        <div style={spectrumLabelStyle}>
                          <span>{formatFrequency(spectrumData.center_freq_hz - spectrumData.bandwidth_hz / 2)}</span>
                          <span>{formatFrequency(spectrumData.center_freq_hz)}</span>
                          <span>{formatFrequency(spectrumData.center_freq_hz + spectrumData.bandwidth_hz / 2)}</span>
                        </div>
                      </div>
                      <div style={spectrumStatsStyle}>
                        <span>Peak: {spectrumData.peak_power?.toFixed(1)} dBm @ {formatFrequency(spectrumData.peak_freq_hz || 0)}</span>
                        <span>Noise Floor: {spectrumData.noise_floor?.toFixed(1)} dBm</span>
                      </div>
                    </div>
                  ) : (
                    <p style={emptyTextStyle}>Click "Capture Spectrum" to analyze the RF environment.</p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div style={placeholderStyle}>
              <span style={placeholderIconStyle}>📡</span>
              <p>Select a simulation from the list or create a new one</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Simulation Modal */}
      {showCreateForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Create New RF Simulation</h3>
              <button onClick={() => setShowCreateForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateSimulation} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Name *</label>
                <input
                  type="text"
                  value={simulationForm.name}
                  onChange={(e) => setSimulationForm((prev) => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., EW Training Scenario 1"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description</label>
                <textarea
                  value={simulationForm.description}
                  onChange={(e) => setSimulationForm((prev) => ({ ...prev, description: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="Describe the simulation scenario..."
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

      {/* Add Signal Modal */}
      {showSignalForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Add Signal</h3>
              <button onClick={() => setShowSignalForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleAddSignal} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Name *</label>
                <input
                  type="text"
                  value={signalForm.name}
                  onChange={(e) => setSignalForm((prev) => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Friendly Comms"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Signal Type *</label>
                <select
                  value={signalForm.signal_type}
                  onChange={(e) => setSignalForm((prev) => ({ ...prev, signal_type: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="communication">Communication</option>
                  <option value="radar">Radar</option>
                  <option value="navigation">Navigation</option>
                  <option value="broadcast">Broadcast</option>
                  <option value="beacon">Beacon</option>
                </select>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Frequency (Hz) *</label>
                  <input
                    type="number"
                    value={signalForm.frequency_hz}
                    onChange={(e) => setSignalForm((prev) => ({ ...prev, frequency_hz: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Bandwidth (Hz) *</label>
                  <input
                    type="number"
                    value={signalForm.bandwidth_hz}
                    onChange={(e) => setSignalForm((prev) => ({ ...prev, bandwidth_hz: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Power (dBm) *</label>
                  <input
                    type="number"
                    value={signalForm.power_dbm}
                    onChange={(e) => setSignalForm((prev) => ({ ...prev, power_dbm: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Modulation *</label>
                  <select
                    value={signalForm.modulation}
                    onChange={(e) => setSignalForm((prev) => ({ ...prev, modulation: e.target.value }))}
                    style={inputStyle}
                    required
                  >
                    <option value="AM">AM</option>
                    <option value="FM">FM</option>
                    <option value="PSK">PSK</option>
                    <option value="QAM">QAM</option>
                    <option value="FSK">FSK</option>
                    <option value="OFDM">OFDM</option>
                  </select>
                </div>
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowSignalForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Add Signal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Jamming Modal */}
      {showJammingForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>Add Jamming Effect</h3>
              <button onClick={() => setShowJammingForm(false)} style={closeButtonStyle}>
                ✕
              </button>
            </div>
            <form onSubmit={handleAddJamming} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Name *</label>
                <input
                  type="text"
                  value={jammingForm.name}
                  onChange={(e) => setJammingForm((prev) => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Barrage Jammer"
                  required
                />
              </div>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Jamming Type *</label>
                <select
                  value={jammingForm.jamming_type}
                  onChange={(e) => setJammingForm((prev) => ({ ...prev, jamming_type: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="barrage">Barrage</option>
                  <option value="spot">Spot</option>
                  <option value="sweep">Sweep</option>
                  <option value="pulse">Pulse</option>
                  <option value="repeater">Repeater</option>
                </select>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Target Frequency (Hz) *</label>
                  <input
                    type="number"
                    value={jammingForm.target_freq_hz}
                    onChange={(e) => setJammingForm((prev) => ({ ...prev, target_freq_hz: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Bandwidth (Hz) *</label>
                  <input
                    type="number"
                    value={jammingForm.bandwidth_hz}
                    onChange={(e) => setJammingForm((prev) => ({ ...prev, bandwidth_hz: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
              </div>
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Power (dBm) *</label>
                  <input
                    type="number"
                    value={jammingForm.power_dbm}
                    onChange={(e) => setJammingForm((prev) => ({ ...prev, power_dbm: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Duration (seconds)</label>
                  <input
                    type="number"
                    value={jammingForm.duration_seconds}
                    onChange={(e) => setJammingForm((prev) => ({ ...prev, duration_seconds: e.target.value }))}
                    style={inputStyle}
                    placeholder="Leave empty for continuous"
                  />
                </div>
              </div>
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowJammingForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Add Jamming
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

const safetyBannerStyle = {
  padding: '12px 16px',
  backgroundColor: '#fff3cd',
  color: '#856404',
  borderRadius: '4px',
  marginBottom: '20px',
  textAlign: 'center',
  fontSize: '14px',
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

const layoutStyle = {
  display: 'flex',
  gap: '20px',
  minHeight: '500px',
};

const sidebarStyle = {
  width: '280px',
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

const simNameStyle = {
  fontWeight: '500',
  fontSize: '14px',
};

const simMetaStyle = {
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
};

const bandsListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const bandItemStyle = {
  padding: '8px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  fontSize: '12px',
};

const bandNameStyle = {
  display: 'block',
  fontWeight: '500',
};

const bandRangeStyle = {
  display: 'block',
  color: '#666',
  fontSize: '11px',
};

const mainContentStyle = {
  flex: 1,
  backgroundColor: 'white',
  borderRadius: '8px',
  padding: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const simHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  marginBottom: '20px',
  paddingBottom: '16px',
  borderBottom: '1px solid #e9ecef',
};

const simControlsStyle = {
  display: 'flex',
  gap: '8px',
};

const descriptionTextStyle = {
  fontSize: '13px',
  color: '#666',
  margin: '4px 0 8px 0',
};

const statusBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
  textTransform: 'uppercase',
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
  minHeight: '300px',
};

const tabHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px',
};

const itemGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
  gap: '16px',
};

const signalCardStyle = {
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  padding: '16px',
  border: '1px solid #e9ecef',
};

const jammingCardStyle = {
  ...signalCardStyle,
  borderLeft: '4px solid #dc3545',
};

const threatCardStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  padding: '12px 16px',
  border: '1px solid #e9ecef',
};

const threatInfoStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

const threatNameStyle = {
  fontWeight: '500',
  fontSize: '14px',
};

const threatDescStyle = {
  fontSize: '12px',
  color: '#666',
};

const threatTypeBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#dc3545',
  color: 'white',
};

const cardHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const cardBodyStyle = {
  marginBottom: '12px',
};

const signalNameStyle = {
  fontWeight: '500',
  fontSize: '14px',
};

const signalTypeBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#17a2b8',
  color: 'white',
};

const jammingTypeBadgeStyle = {
  ...signalTypeBadgeStyle,
  backgroundColor: '#dc3545',
};

const signalDetailStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  marginBottom: '4px',
  color: '#666',
};

const spectrumDisplayStyle = {
  backgroundColor: '#1a1a2e',
  borderRadius: '8px',
  padding: '16px',
  color: 'white',
};

const spectrumHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-around',
  marginBottom: '16px',
  fontSize: '12px',
  color: '#aaa',
};

const spectrumVisualizationStyle = {
  backgroundColor: '#0f0f23',
  borderRadius: '4px',
  padding: '16px',
};

const spectrumSvgStyle = {
  width: '100%',
  height: '200px',
};

const spectrumLabelStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '11px',
  color: '#666',
  marginTop: '8px',
};

const spectrumStatsStyle = {
  display: 'flex',
  justifyContent: 'space-around',
  marginTop: '16px',
  fontSize: '12px',
  color: '#aaa',
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

const addButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#17a2b8',
  padding: '6px 12px',
  fontSize: '13px',
};

const addThreatButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
  padding: '6px 12px',
  fontSize: '12px',
};

const startButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
  padding: '6px 12px',
  fontSize: '13px',
};

const pauseButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#ffc107',
  color: '#333',
  padding: '6px 12px',
  fontSize: '13px',
};

const stopButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#dc3545',
  padding: '6px 12px',
  fontSize: '13px',
};

const deleteButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
  width: '100%',
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
