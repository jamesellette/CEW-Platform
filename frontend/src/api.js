import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cew_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authApi = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
  register: (userData) => api.post('/auth/register', userData),
  logout: () => {
    localStorage.removeItem('cew_token');
    localStorage.removeItem('cew_user');
  },
  setToken: (token) => localStorage.setItem('cew_token', token),
  getToken: () => localStorage.getItem('cew_token'),
  setUser: (user) => localStorage.setItem('cew_user', JSON.stringify(user)),
  getUser: () => {
    const user = localStorage.getItem('cew_user');
    return user ? JSON.parse(user) : null;
  },
};

// User Management API (admin only)
export const userApi = {
  list: () => api.get('/auth/users'),
  create: (userData) => api.post('/auth/register', userData),
  delete: (username) => api.delete(`/auth/users/${username}`),
};

// Scenario API
export const scenarioApi = {
  list: () => api.get('/scenarios'),
  get: (id) => api.get(`/scenarios/${id}`),
  create: (data) => api.post('/scenarios', data),
  update: (id, data) => api.put(`/scenarios/${id}`, data),
  delete: (id) => api.delete(`/scenarios/${id}`),
  exportJson: (id) => api.get(`/scenarios/${id}/export?format=json`),
  exportYaml: (id) => api.get(`/scenarios/${id}/export?format=yaml`),
  import: (content, format) => api.post('/scenarios/import', { content, format }),
  activate: (id) => api.post(`/scenarios/${id}/activate`),
  deactivate: (id) => api.post(`/scenarios/${id}/deactivate`),
  listActive: () => api.get('/scenarios/active'),
};

// Topology API
export const topologyApi = {
  list: () => api.get('/topologies'),
  get: (filename) => api.get(`/topologies/${filename}`),
};

// Lab API - for detailed lab management
export const labApi = {
  list: () => api.get('/labs'),
  listActive: () => api.get('/labs/active'),
  get: (labId) => api.get(`/labs/${labId}`),
  stop: (labId) => api.post(`/labs/${labId}/stop`),
  getHealth: (labId) => api.get(`/labs/${labId}/health`),
  getResources: (labId) => api.get(`/labs/${labId}/resources`),
  recover: (labId) => api.post(`/labs/${labId}/recover`),
};

// WebSocket API - for real-time lab monitoring
export const wsApi = {
  getStatus: () => api.get('/ws/status'),
  getLabMonitorUrl: (labId, token) => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = API_BASE_URL.replace(/^https?:\/\//, '');
    return `${wsProtocol}//${host}/ws/labs/${labId}?token=${token}`;
  },
};

// Session Recording API - for exercise recording and playback
export const recordingApi = {
  // Start a recording session
  start: (labId, scenarioId, scenarioName, metadata = null) =>
    api.post('/recordings/start', { lab_id: labId, scenario_id: scenarioId, scenario_name: scenarioName, metadata }),

  // Stop a recording session
  stop: (sessionId) => api.post(`/recordings/${sessionId}/stop`),

  // Pause a recording session
  pause: (sessionId) => api.post(`/recordings/${sessionId}/pause`),

  // Resume a recording session
  resume: (sessionId) => api.post(`/recordings/${sessionId}/resume`),

  // List all recordings
  list: (username = null) => api.get('/recordings', { params: username ? { username } : {} }),

  // Get a specific recording
  get: (sessionId) => api.get(`/recordings/${sessionId}`),

  // Get recording summary
  getSummary: (sessionId) => api.get(`/recordings/${sessionId}/summary`),

  // Get recording events
  getEvents: (sessionId, eventTypes = null, limit = 1000) =>
    api.get(`/recordings/${sessionId}/events`, { params: { event_types: eventTypes, limit } }),

  // Get playback data
  getPlayback: (sessionId, speed = 1.0) =>
    api.get(`/recordings/${sessionId}/playback`, { params: { speed } }),

  // Get current recording for a lab
  getCurrent: (labId) => api.get(`/recordings/labs/${labId}/current`),

  // Record an event
  recordEvent: (labId, eventType, containerId = null, hostname = null, data = null) =>
    api.post(`/recordings/labs/${labId}/events`, { event_type: eventType, container_id: containerId, hostname, data }),

  // Record a command execution
  recordCommand: (labId, containerId, hostname, command, output, exitCode, durationMs) =>
    api.post(`/recordings/labs/${labId}/commands`, {
      container_id: containerId,
      hostname,
      command,
      output,
      exit_code: exitCode,
      duration_ms: durationMs,
    }),
};

// Progress Tracking API - for trainee progress and assessments
export const progressApi = {
  // Exercise progress
  startExercise: (exerciseId, exerciseName, scenarioId, objectivesTotal = 0, maxScore = 100) =>
    api.post('/progress/exercises/start', {
      exercise_id: exerciseId,
      exercise_name: exerciseName,
      scenario_id: scenarioId,
      objectives_total: objectivesTotal,
      max_score: maxScore,
    }),

  completeObjective: (progressId, objectiveId, pointsEarned = 0) =>
    api.post(`/progress/exercises/${progressId}/objectives`, {
      objective_id: objectiveId,
      points_earned: pointsEarned,
    }),

  completeExercise: (progressId, finalScore = null, notes = '') =>
    api.post(`/progress/exercises/${progressId}/complete`, { final_score: finalScore, notes }),

  failExercise: (progressId, notes = '') =>
    api.post(`/progress/exercises/${progressId}/fail`, {}, { params: { notes } }),

  recordHint: (progressId) => api.post(`/progress/exercises/${progressId}/hint`),

  getExerciseProgress: (progressId) => api.get(`/progress/exercises/${progressId}`),

  // User progress
  getMyProgress: () => api.get('/progress/me'),

  getMyReport: () => api.get('/progress/me/report'),

  getUserProgress: (username) => api.get(`/progress/users/${username}`),

  getUserReport: (username) => api.get(`/progress/users/${username}/report`),

  // Skills
  assessSkill: (skillName, skillCategory, experienceGained = 0) =>
    api.post('/progress/skills/assess', {
      skill_name: skillName,
      skill_category: skillCategory,
      experience_gained: experienceGained,
    }),

  getUserSkills: (username) => api.get(`/progress/skills/${username}`),

  // Leaderboard and badges
  getLeaderboard: (metric = 'score', limit = 10) =>
    api.get('/progress/leaderboard', { params: { metric, limit } }),

  getBadges: () => api.get('/progress/badges'),

  getSkillCategories: () => api.get('/progress/skill-categories'),

  getAllProfiles: () => api.get('/progress/profiles'),
};

// Marketplace API - for scenario template marketplace
export const marketplaceApi = {
  // Template listing and discovery
  listTemplates: (params = {}) => api.get('/marketplace/templates', { params }),

  getPopular: (limit = 10) => api.get('/marketplace/templates/popular', { params: { limit } }),

  getTopRated: (limit = 10) => api.get('/marketplace/templates/top-rated', { params: { limit } }),

  getRecent: (limit = 10) => api.get('/marketplace/templates/recent', { params: { limit } }),

  getTemplate: (templateId) => api.get(`/marketplace/templates/${templateId}`),

  // Template management
  createTemplate: (data) => api.post('/marketplace/templates', data),

  updateTemplate: (templateId, data) => api.put(`/marketplace/templates/${templateId}`, data),

  deleteTemplate: (templateId) => api.delete(`/marketplace/templates/${templateId}`),

  // Version management
  addVersion: (templateId, version, changelog, scenarioData) =>
    api.post(`/marketplace/templates/${templateId}/versions`, {
      version,
      changelog,
      scenario_data: scenarioData,
    }),

  getVersion: (templateId, version) =>
    api.get(`/marketplace/templates/${templateId}/versions/${version}`),

  // Publishing workflow
  submitForReview: (templateId) => api.post(`/marketplace/templates/${templateId}/submit`),

  approveTemplate: (templateId) => api.post(`/marketplace/templates/${templateId}/approve`),

  rejectTemplate: (templateId, reason) =>
    api.post(`/marketplace/templates/${templateId}/reject`, {}, { params: { reason } }),

  deprecateTemplate: (templateId) => api.post(`/marketplace/templates/${templateId}/deprecate`),

  // Reviews
  addReview: (templateId, rating, title, comment) =>
    api.post(`/marketplace/templates/${templateId}/reviews`, { rating, title, comment }),

  voteHelpful: (templateId, reviewId) =>
    api.post(`/marketplace/templates/${templateId}/reviews/${reviewId}/helpful`),

  // Download/use template
  downloadTemplate: (templateId, version = null) =>
    api.post(`/marketplace/templates/${templateId}/download`, {}, { params: version ? { version } : {} }),

  // Categories and statistics
  getCategories: () => api.get('/marketplace/categories'),

  getStatistics: () => api.get('/marketplace/statistics'),

  // User templates
  getMyTemplates: () => api.get('/marketplace/my-templates'),

  getPending: () => api.get('/marketplace/pending'),
};

// Multi-User Session API - for collaborative training sessions
export const sessionApi = {
  // Session management
  createSession: (name, description, labId, scenarioId, sessionType, maxParticipants = 10, settings = null) =>
    api.post('/sessions', {
      name,
      description,
      lab_id: labId,
      scenario_id: scenarioId,
      session_type: sessionType,
      max_participants: maxParticipants,
      settings,
    }),

  listSessions: (sessionType = null, activeOnly = true) =>
    api.get('/sessions', { params: { session_type: sessionType, active_only: activeOnly } }),

  getMySessions: () => api.get('/sessions/me'),

  getSession: (sessionId) => api.get(`/sessions/${sessionId}`),

  startSession: (sessionId) => api.post(`/sessions/${sessionId}/start`),

  endSession: (sessionId) => api.post(`/sessions/${sessionId}/end`),

  deleteSession: (sessionId) => api.delete(`/sessions/${sessionId}`),

  // Participant management
  addParticipant: (sessionId, username, displayName, teamRole, permissions = null) =>
    api.post(`/sessions/${sessionId}/participants`, {
      username,
      display_name: displayName,
      team_role: teamRole,
      permissions,
    }),

  joinSession: (sessionId) => api.post(`/sessions/${sessionId}/join`),

  leaveSession: (sessionId) => api.post(`/sessions/${sessionId}/leave`),

  removeParticipant: (sessionId, participantId) =>
    api.delete(`/sessions/${sessionId}/participants/${participantId}`),

  // Team management
  createTeam: (sessionId, name, role, color = '#6c757d') =>
    api.post(`/sessions/${sessionId}/teams`, {}, { params: { name, role, color } }),

  assignToTeam: (sessionId, teamId, participantId) =>
    api.post(`/sessions/${sessionId}/teams/${teamId}/assign/${participantId}`),

  updateTeamScore: (sessionId, teamId, points) =>
    api.post(`/sessions/${sessionId}/teams/${teamId}/score`, {}, { params: { points } }),

  // Objectives
  addObjective: (sessionId, name, description, points, teamRole = null) =>
    api.post(`/sessions/${sessionId}/objectives`, {
      name,
      description,
      points,
      team_role: teamRole,
    }),

  completeObjective: (sessionId, objectiveId, teamId) =>
    api.post(`/sessions/${sessionId}/objectives/${objectiveId}/complete`, {}, { params: { team_id: teamId } }),

  // Chat
  sendMessage: (sessionId, content, isTeamOnly = false) =>
    api.post(`/sessions/${sessionId}/messages`, { content, is_team_only: isTeamOnly }),

  getMessages: (sessionId, limit = 50, after = null) =>
    api.get(`/sessions/${sessionId}/messages`, { params: { limit, after } }),

  // Scores
  getScores: (sessionId) => api.get(`/sessions/${sessionId}/scores`),
};

// Scheduling API - for scheduled exercises
export const scheduleApi = {
  // Schedule management
  createSchedule: (data) => api.post('/schedules', data),

  listSchedules: (status = null, fromDate = null, toDate = null) =>
    api.get('/schedules', { params: { status, from_date: fromDate, to_date: toDate } }),

  getSchedule: (scheduleId) => api.get(`/schedules/${scheduleId}`),

  updateSchedule: (scheduleId, data) => api.put(`/schedules/${scheduleId}`, data),

  cancelSchedule: (scheduleId) => api.post(`/schedules/${scheduleId}/cancel`),

  deleteSchedule: (scheduleId) => api.delete(`/schedules/${scheduleId}`),

  // Schedule lifecycle
  startExercise: (scheduleId, labId) =>
    api.post(`/schedules/${scheduleId}/start`, {}, { params: { lab_id: labId } }),

  completeExercise: (scheduleId) => api.post(`/schedules/${scheduleId}/complete`),

  // Participant management
  addParticipant: (scheduleId, username) =>
    api.post(`/schedules/${scheduleId}/participants/${username}`),

  removeParticipant: (scheduleId, username) =>
    api.delete(`/schedules/${scheduleId}/participants/${username}`),

  // Views
  getUpcoming: (days = 7) => api.get('/schedules/upcoming', { params: { days } }),

  getCalendar: (year, month) => api.get(`/schedules/calendar/${year}/${month}`),

  getMySchedules: () => api.get('/schedules/me'),
};

// Notification API - for schedule notifications
export const notificationApi = {
  getNotifications: (unreadOnly = false, limit = 50) =>
    api.get('/notifications', { params: { unread_only: unreadOnly, limit } }),

  getUnreadCount: () => api.get('/notifications/unread-count'),

  markRead: (notificationId) => api.post(`/notifications/${notificationId}/read`),

  markAllRead: () => api.post('/notifications/read-all'),
};

// Topology Editor API - for visual network topology building
export const topologyApi = {
  // Topology management
  createTopology: (name, description, metadata = null) =>
    api.post('/topology-editor', { name, description, metadata }),

  listTopologies: () => api.get('/topology-editor'),

  getTopology: (topologyId) => api.get(`/topology-editor/${topologyId}`),

  updateTopology: (topologyId, name, description, metadata = null) =>
    api.put(`/topology-editor/${topologyId}`, { name, description, metadata }),

  deleteTopology: (topologyId) => api.delete(`/topology-editor/${topologyId}`),

  cloneTopology: (topologyId, newName) =>
    api.post(`/topology-editor/${topologyId}/clone`, {}, { params: { new_name: newName } }),

  // Node management
  addNode: (topologyId, data) => api.post(`/topology-editor/${topologyId}/nodes`, data),

  updateNode: (topologyId, nodeId, data) =>
    api.put(`/topology-editor/${topologyId}/nodes/${nodeId}`, data),

  deleteNode: (topologyId, nodeId) =>
    api.delete(`/topology-editor/${topologyId}/nodes/${nodeId}`),

  moveNode: (topologyId, nodeId, x, y) =>
    api.post(`/topology-editor/${topologyId}/nodes/${nodeId}/move`, {}, { params: { x, y } }),

  // Connection management
  addConnection: (topologyId, data) =>
    api.post(`/topology-editor/${topologyId}/connections`, data),

  deleteConnection: (topologyId, connectionId) =>
    api.delete(`/topology-editor/${topologyId}/connections/${connectionId}`),

  // Subnet management
  addSubnet: (topologyId, data) => api.post(`/topology-editor/${topologyId}/subnets`, data),

  deleteSubnet: (topologyId, subnetId) =>
    api.delete(`/topology-editor/${topologyId}/subnets/${subnetId}`),

  // Validation and export
  validateTopology: (topologyId) => api.get(`/topology-editor/${topologyId}/validate`),

  exportTopology: (topologyId, format = 'json') =>
    api.get(`/topology-editor/${topologyId}/export`, { params: { format } }),

  importTopology: (name, content, format = 'json') =>
    api.post('/topology-editor/import', { name, content, format }),

  // Type references
  getNodeTypes: () => api.get('/topology-editor/node-types'),

  getConnectionTypes: () => api.get('/topology-editor/connection-types'),
};

// Kill switch API
export const killSwitchApi = {
  activate: () => api.post('/kill-switch'),
};

// Audit API
export const auditApi = {
  logs: (params) => api.get('/audit/logs', { params }),
};

// Rate Limiting API - for API rate limit management
export const rateLimitApi = {
  // Status and configuration
  getStatus: () => api.get('/rate-limits/status'),
  
  setEnabled: (enabled) => api.post('/rate-limits/enable', {}, { params: { enabled } }),
  
  // Statistics
  getStatistics: () => api.get('/rate-limits/statistics'),
  
  resetStatistics: () => api.post('/rate-limits/statistics/reset'),
  
  // Violations
  getViolations: (userId = null, limit = 100) =>
    api.get('/rate-limits/violations', { params: { user_id: userId, limit } }),
  
  // Top usage
  getTopUsers: (limit = 10) =>
    api.get('/rate-limits/top-users', { params: { limit } }),
  
  getTopEndpoints: (limit = 10) =>
    api.get('/rate-limits/top-endpoints', { params: { limit } }),
  
  // User management
  getUserState: (userId) => api.get(`/rate-limits/users/${userId}`),
  
  resetUserState: (userId) => api.post(`/rate-limits/users/${userId}/reset`),
  
  blockUser: (userId, durationMinutes = 60) =>
    api.post(`/rate-limits/users/${userId}/block`, { duration_minutes: durationMinutes }),
  
  unblockUser: (userId) => api.post(`/rate-limits/users/${userId}/unblock`),
  
  // Tier configuration
  setTierLimits: (tier, limits) => api.put(`/rate-limits/tiers/${tier}`, limits),
  
  // Endpoint configuration
  setEndpointConfig: (endpoint, config) =>
    api.put(`/rate-limits/endpoints/${endpoint}`, config),
  
  // Current user's status
  getMyStatus: () => api.get('/rate-limits/me'),
};

// Backup & Disaster Recovery API - for backup management
export const backupApi = {
  // Backups
  createBackup: (backupType, description = '', tags = [], retentionDays = 30) =>
    api.post('/backups', {
      backup_type: backupType,
      description,
      tags,
      retention_days: retentionDays,
    }),
  
  listBackups: (backupType = null, status = null, tags = null, limit = 100) =>
    api.get('/backups', { params: { backup_type: backupType, status, tags, limit } }),
  
  getBackup: (backupId) => api.get(`/backups/${backupId}`),
  
  deleteBackup: (backupId) => api.delete(`/backups/${backupId}`),
  
  verifyBackup: (backupId) => api.post(`/backups/${backupId}/verify`),
  
  restoreBackup: (backupId) => api.post(`/backups/${backupId}/restore`),
  
  exportBackup: (backupId, format = 'json') =>
    api.get(`/backups/${backupId}/export`, { params: { format } }),
  
  importBackup: (content, format = 'json') =>
    api.post('/backups/import', { content, format }),
  
  cleanupExpired: () => api.post('/backups/cleanup'),
  
  getStatistics: () => api.get('/backups/statistics'),
  
  // Lab Snapshots
  createSnapshot: (labId, scenarioId, status, containers = [], networks = [], environment = {}, notes = '') =>
    api.post('/snapshots', {
      lab_id: labId,
      scenario_id: scenarioId,
      status,
      containers,
      networks,
      environment,
      notes,
    }),
  
  listSnapshots: (labId = null, scenarioId = null, limit = 50) =>
    api.get('/snapshots', { params: { lab_id: labId, scenario_id: scenarioId, limit } }),
  
  getSnapshot: (snapshotId) => api.get(`/snapshots/${snapshotId}`),
  
  deleteSnapshot: (snapshotId) => api.delete(`/snapshots/${snapshotId}`),
  
  restoreSnapshot: (snapshotId) => api.post(`/snapshots/${snapshotId}/restore`),
  
  // Restore Points
  listRestorePoints: (backupId = null, status = null, limit = 50) =>
    api.get('/restore-points', { params: { backup_id: backupId, status, limit } }),
  
  getRestorePoint: (restoreId) => api.get(`/restore-points/${restoreId}`),
  
  // Backup Schedules
  createSchedule: (backupType, frequency, timeOfDay, dayOfWeek = null, dayOfMonth = null, retentionDays = 30, maxBackups = 10) =>
    api.post('/backup-schedules', {
      backup_type: backupType,
      frequency,
      time_of_day: timeOfDay,
      day_of_week: dayOfWeek,
      day_of_month: dayOfMonth,
      retention_days: retentionDays,
      max_backups: maxBackups,
    }),
  
  listSchedules: (enabledOnly = false) =>
    api.get('/backup-schedules', { params: { enabled_only: enabledOnly } }),
  
  getSchedule: (scheduleId) => api.get(`/backup-schedules/${scheduleId}`),
  
  updateSchedule: (scheduleId, data) => api.put(`/backup-schedules/${scheduleId}`, data),
  
  deleteSchedule: (scheduleId) => api.delete(`/backup-schedules/${scheduleId}`),
};

// External Integrations API - for external tool integrations
export const integrationsApi = {
  // Integration Management
  createIntegration: (integrationType, name, config = {}, enabled = true) =>
    api.post('/integrations', {
      integration_type: integrationType,
      name,
      config,
      enabled,
    }),
  
  listIntegrations: (integrationType = null, enabledOnly = false) =>
    api.get('/integrations', { params: { integration_type: integrationType, enabled_only: enabledOnly } }),
  
  getIntegration: (integrationId) => api.get(`/integrations/${integrationId}`),
  
  updateIntegration: (integrationId, data) => api.put(`/integrations/${integrationId}`, data),
  
  deleteIntegration: (integrationId) => api.delete(`/integrations/${integrationId}`),
  
  testIntegration: (integrationId) => api.post(`/integrations/${integrationId}/test`),
  
  getStatistics: () => api.get('/integrations/statistics'),
  
  // MITRE ATT&CK
  getTactics: () => api.get('/mitre-attack/tactics'),
  
  listTechniques: (tactic = null, platform = null, search = null) =>
    api.get('/mitre-attack/techniques', { params: { tactic, platform, search } }),
  
  getTechnique: (techniqueId) => api.get(`/mitre-attack/techniques/${techniqueId}`),
  
  createMapping: (scenarioId, scenarioName, techniques, notes = '') =>
    api.post('/mitre-attack/mappings', {
      scenario_id: scenarioId,
      scenario_name: scenarioName,
      techniques,
      notes,
    }),
  
  listMappings: (createdBy = null) =>
    api.get('/mitre-attack/mappings', { params: { created_by: createdBy } }),
  
  getMapping: (mappingId) => api.get(`/mitre-attack/mappings/${mappingId}`),
  
  getMappingDetails: (mappingId) => api.get(`/mitre-attack/mappings/${mappingId}/details`),
  
  getScenarioMapping: (scenarioId) => api.get(`/mitre-attack/scenarios/${scenarioId}/mapping`),
  
  updateMapping: (mappingId, data) => api.put(`/mitre-attack/mappings/${mappingId}`, data),
  
  deleteMapping: (mappingId) => api.delete(`/mitre-attack/mappings/${mappingId}`),
  
  // Log Forwarding
  createForwardingRule: (name, integrationId, logLevels = ['info', 'warning', 'error'], sourceFilter = null, batchSize = 100, flushInterval = 30) =>
    api.post('/log-forwarding/rules', {
      name,
      integration_id: integrationId,
      log_levels: logLevels,
      source_filter: sourceFilter,
      batch_size: batchSize,
      flush_interval: flushInterval,
    }),
  
  listForwardingRules: (integrationId = null, enabledOnly = false) =>
    api.get('/log-forwarding/rules', { params: { integration_id: integrationId, enabled_only: enabledOnly } }),
  
  getForwardingRule: (ruleId) => api.get(`/log-forwarding/rules/${ruleId}`),
  
  updateForwardingRule: (ruleId, data) => api.put(`/log-forwarding/rules/${ruleId}`, data),
  
  deleteForwardingRule: (ruleId) => api.delete(`/log-forwarding/rules/${ruleId}`),
  
  // Network Emulation
  createEmulationConfig: (name, topologyId, emulatorType, controller = 'default', linkParams = {}, hostParams = {}, switchParams = {}) =>
    api.post('/emulation/configs', {
      name,
      topology_id: topologyId,
      emulator_type: emulatorType,
      controller,
      link_params: linkParams,
      host_params: hostParams,
      switch_params: switchParams,
    }),
  
  listEmulationConfigs: (topologyId = null, emulatorType = null) =>
    api.get('/emulation/configs', { params: { topology_id: topologyId, emulator_type: emulatorType } }),
  
  getEmulationConfig: (configId) => api.get(`/emulation/configs/${configId}`),
  
  deleteEmulationConfig: (configId) => api.delete(`/emulation/configs/${configId}`),
  
  getMininetScript: (configId) => api.get(`/emulation/configs/${configId}/script`),
};

// RF/EW Simulation API - for radio frequency and electronic warfare training (simulation only)
export const rfSimulationApi = {
  // Simulation management
  createSimulation: (name, description = '', settings = {}) =>
    api.post('/rf-simulation', { name, description, settings }),
  
  listSimulations: (createdBy = null, status = null) =>
    api.get('/rf-simulation', { params: { created_by: createdBy, status } }),
  
  getSimulation: (simulationId) => api.get(`/rf-simulation/${simulationId}`),
  
  startSimulation: (simulationId) => api.post(`/rf-simulation/${simulationId}/start`),
  
  pauseSimulation: (simulationId) => api.post(`/rf-simulation/${simulationId}/pause`),
  
  stopSimulation: (simulationId) => api.post(`/rf-simulation/${simulationId}/stop`),
  
  deleteSimulation: (simulationId) => api.delete(`/rf-simulation/${simulationId}`),
  
  getStatistics: () => api.get('/rf-simulation/statistics'),
  
  getFrequencyBands: () => api.get('/rf-simulation/frequency-bands'),
  
  getPredefinedThreats: () => api.get('/rf-simulation/threats'),
  
  // Signal management
  addSignal: (simulationId, name, signalType, frequencyHz, bandwidthHz, powerDbm, modulation, location = null, metadata = {}) =>
    api.post(`/rf-simulation/${simulationId}/signals`, {
      name,
      signal_type: signalType,
      frequency_hz: frequencyHz,
      bandwidth_hz: bandwidthHz,
      power_dbm: powerDbm,
      modulation,
      location,
      metadata,
    }),
  
  listSignals: (simulationId) => api.get(`/rf-simulation/${simulationId}/signals`),
  
  getSignal: (simulationId, signalId) => api.get(`/rf-simulation/${simulationId}/signals/${signalId}`),
  
  updateSignal: (simulationId, signalId, data) => api.put(`/rf-simulation/${simulationId}/signals/${signalId}`, data),
  
  removeSignal: (simulationId, signalId) => api.delete(`/rf-simulation/${simulationId}/signals/${signalId}`),
  
  // Jamming simulation
  addJamming: (simulationId, name, jammingType, targetFreqHz, bandwidthHz, powerDbm, durationSeconds = null) =>
    api.post(`/rf-simulation/${simulationId}/jamming`, {
      name,
      jamming_type: jammingType,
      target_freq_hz: targetFreqHz,
      bandwidth_hz: bandwidthHz,
      power_dbm: powerDbm,
      duration_seconds: durationSeconds,
    }),
  
  listJamming: (simulationId) => api.get(`/rf-simulation/${simulationId}/jamming`),
  
  removeJamming: (simulationId, effectId) => api.delete(`/rf-simulation/${simulationId}/jamming/${effectId}`),
  
  // Threat management
  addThreat: (simulationId, threatId) => api.post(`/rf-simulation/${simulationId}/threats/${threatId}`),
  
  listThreats: (simulationId) => api.get(`/rf-simulation/${simulationId}/threats`),
  
  removeThreat: (simulationId, threatId) => api.delete(`/rf-simulation/${simulationId}/threats/${threatId}`),
  
  // Spectrum analysis
  captureSpectrum: (simulationId, centerFreqHz, bandwidthHz, fftSize = 1024) =>
    api.post(`/rf-simulation/${simulationId}/spectrum`, {
      center_freq_hz: centerFreqHz,
      bandwidth_hz: bandwidthHz,
      fft_size: fftSize,
    }),
  
  getSpectrumSnapshots: (simulationId, limit = 10) =>
    api.get(`/rf-simulation/${simulationId}/spectrum`, { params: { limit } }),
  
  // SIGINT reports
  createReport: (simulationId, signalsAnalyzed, threatAssessment, recommendations, confidenceLevel) =>
    api.post(`/rf-simulation/${simulationId}/reports`, {
      signals_analyzed: signalsAnalyzed,
      threat_assessment: threatAssessment,
      recommendations,
      confidence_level: confidenceLevel,
    }),
  
  getReports: (simulationId, limit = 10) =>
    api.get(`/rf-simulation/${simulationId}/reports`, { params: { limit } }),
};

export default api;
