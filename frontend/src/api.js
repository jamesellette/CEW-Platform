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

// Kill switch API
export const killSwitchApi = {
  activate: () => api.post('/kill-switch'),
};

// Audit API
export const auditApi = {
  logs: (params) => api.get('/audit/logs', { params }),
};

export default api;
