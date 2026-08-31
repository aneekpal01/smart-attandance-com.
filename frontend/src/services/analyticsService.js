import api from './api';

export const analyticsService = {
  async getOverview(params = {}) {
    const res = await api.get('/api/analytics/overview', { params });
    return res.data;
  },

  async getAttendanceTrend(days = 30) {
    const res = await api.get('/api/analytics/attendance-trend', { params: { days } });
    return res.data;
  },

  async getSubjectBreakdown() {
    const res = await api.get('/api/analytics/subjects');
    return res.data;
  },

  async getStudentProfiles(params = {}) {
    const res = await api.get('/api/analytics/students', { params });
    return res.data;
  },

  async getRiskAnalysis(requiredThreshold = 75.0, params = {}) {
    const res = await api.get('/api/analytics/risk', {
      params: { required_threshold: requiredThreshold, ...params }
    });
    return res.data;
  },

  async getSecurityAnalytics() {
    const res = await api.get('/api/analytics/security');
    return res.data;
  },

  async getAiInsights(requiredThreshold = 75.0) {
    const res = await api.get('/api/analytics/insights', {
      params: { required_threshold: requiredThreshold }
    });
    return res.data;
  },

  async getStudentDetailedBreakdown(studentIdOrRoll) {
    const res = await api.get(`/api/analytics/student/${studentIdOrRoll}/breakdown`);
    return res.data;
  }
};
