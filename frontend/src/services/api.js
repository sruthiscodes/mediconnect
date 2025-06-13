import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('mediconnect_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('mediconnect_token');
      localStorage.removeItem('mediconnect_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (email, password) => {
    try {
      const response = await api.post('/api/auth/login', {
        email,
        password,
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  },

  signup: async (email, password) => {
    try {
      const response = await api.post('/api/auth/signup', {
        email,
        password,
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Signup failed');
    }
  },

  getCurrentUser: async () => {
    try {
      const response = await api.get('/api/auth/me');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to get user');
    }
  },
};

// Triage API
export const triageAPI = {
  assessSymptoms: async (symptoms) => {
    try {
      const response = await api.post('/api/triage/assess', {
        symptoms,
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Assessment failed');
    }
  },

  getUrgencyLevels: async () => {
    try {
      const response = await api.get('/api/triage/urgency-levels');
      return response.data;
    } catch (error) {
      throw new Error('Failed to get urgency levels');
    }
  },
};

// History API
export const historyAPI = {
  getUserHistory: async (limit = 10) => {
    try {
      const response = await api.get(`/api/history/?limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to get history');
    }
  },

  getRecentSymptoms: async () => {
    try {
      const response = await api.get('/api/history/recent');
      return response.data;
    } catch (error) {
      throw new Error('Failed to get recent symptoms');
    }
  },

  getUserStats: async () => {
    try {
      const response = await api.get('/api/history/stats');
      return response.data;
    } catch (error) {
      throw new Error('Failed to get user stats');
    }
  },

  updateResolutionStatus: async (symptomLogId, resolutionStatus) => {
    try {
      const response = await api.put('/api/history/resolution', {
        symptom_log_id: symptomLogId,
        resolution_status: resolutionStatus
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to update resolution status');
    }
  },

  getUnresolvedSymptoms: async () => {
    try {
      const response = await api.get('/api/history/unresolved');
      return response.data;
    } catch (error) {
      throw new Error('Failed to get unresolved symptoms');
    }
  },
};

// Utility functions
export const setAuthToken = (token) => {
  localStorage.setItem('mediconnect_token', token);
};

export const removeAuthToken = () => {
  localStorage.removeItem('mediconnect_token');
  localStorage.removeItem('mediconnect_user');
};

export const getAuthToken = () => {
  return localStorage.getItem('mediconnect_token');
};

export default api; 