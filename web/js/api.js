import { state, setConnectionState } from './state.js';

const API_BASE = '/api';
let onUnauthorizedCallback = null;

export function setOnUnauthorized(fn) {
  onUnauthorizedCallback = fn;
}

export function vibrate(ms = 10) {
  try {
    if (navigator.vibrate) navigator.vibrate(ms);
  } catch (_) {}
}

export const api = {
  async request(endpoint, method = 'GET', body = null, isFormData = false) {
    const headers = {};
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers,
        body: isFormData ? body : body ? JSON.stringify(body) : null,
      });

      if (res.status === 401) {
        if (onUnauthorizedCallback && endpoint !== '/auth/login') {
          onUnauthorizedCallback();
        }
        throw new Error('Unauthorized');
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${res.status})`);
      }

      setConnectionState('connected');
      return await res.json();
    } catch (err) {
      if (err.message !== 'Unauthorized' && endpoint !== '/auth/login') {
        setConnectionState('reconnecting');
      }
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, 'GET');
  },

  post(endpoint, body = {}) {
    vibrate(10);
    return this.request(endpoint, 'POST', body);
  },

  put(endpoint, body = {}) {
    vibrate(10);
    return this.request(endpoint, 'PUT', body);
  },

  patch(endpoint, body = {}) {
    vibrate(10);
    return this.request(endpoint, 'PATCH', body);
  },

  delete(endpoint) {
    vibrate(14);
    return this.request(endpoint, 'DELETE');
  },

  upload(endpoint, formData) {
    vibrate(10);
    return this.request(endpoint, 'POST', formData, true);
  },
};
