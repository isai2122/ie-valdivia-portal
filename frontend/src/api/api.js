import axios from 'axios';

// In production (single-URL deployment like Render), REACT_APP_BACKEND_URL
// can be empty, which makes axios use a relative URL (/api) served by the
// same host. During Emergent preview, REACT_APP_BACKEND_URL points to the
// external backend.
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('iev_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
