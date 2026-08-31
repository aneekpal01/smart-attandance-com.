import api from './api';

export const sessionService = {
  async createSession(payload) {
    const res = await api.post('/api/sessions/create', payload);
    return res.data;
  },

  async getActiveSessions() {
    const res = await api.get('/api/sessions/active');
    return res.data;
  },

  async getSessionDetails(sessionId) {
    const res = await api.get(`/api/sessions/${sessionId}`);
    return res.data;
  },

  async closeSession(sessionId) {
    const res = await api.post(`/api/sessions/${sessionId}/close`);
    return res.data;
  },

  async deleteSession(sessionId) {
    const res = await api.delete(`/api/sessions/${sessionId}`);
    return res.data;
  },

  async clearAllSessions() {
    const res = await api.delete('/api/sessions/clear-all');
    return res.data;
  },

  async getSessionHistory(limit = 50) {
    const res = await api.get('/api/sessions/history', { params: { limit } });
    return res.data;
  },

  getQrImageUrl(sessionId) {
    return `${api.defaults.baseURL}/api/sessions/${sessionId}/qr-image`;
  }
};
