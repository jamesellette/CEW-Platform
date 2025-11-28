import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const scenarioApi = {
  list: () => api.get('/scenarios'),
  get: (id) => api.get(`/scenarios/${id}`),
  create: (data) => api.post('/scenarios', data),
  update: (id, data) => api.put(`/scenarios/${id}`, data),
  delete: (id) => api.delete(`/scenarios/${id}`),
};

export const topologyApi = {
  list: () => api.get('/topologies'),
  get: (filename) => api.get(`/topologies/${filename}`),
};

export default api;
