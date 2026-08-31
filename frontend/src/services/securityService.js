import api from './api';

export const securityService = {
  async getSessionSecuritySummary(sessionId) {
    const res = await api.get(`/api/security/summary/${sessionId}`);
    return res.data;
  },

  async getSuspiciousActivityFeed(limit = 50) {
    const res = await api.get('/api/security/suspicious', { params: { limit } });
    return res.data;
  },

  async getAuditEvents(params = {}) {
    const res = await api.get('/api/audit/events', { params });
    return res.data;
  },

  async getDashboardOverview() {
    const res = await api.get('/api/dashboard/overview');
    return res.data;
  }
};
