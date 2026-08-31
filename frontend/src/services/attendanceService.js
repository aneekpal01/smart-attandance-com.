import api from './api';

export const attendanceService = {
  async getSessionAttendance(sessionId) {
    const res = await api.get(`/api/attendance/session/${sessionId}`);
    return res.data;
  },

  async verifyAttendance(payload) {
    const res = await api.post('/api/attendance/verify', payload);
    return res.data;
  },

  async manualMarkAttendance(payload) {
    const res = await api.post('/api/attendance/manual-mark', payload);
    return res.data;
  },

  async deleteAttendanceRecord(sessionId, studentId) {
    const res = await api.delete(`/api/attendance/session/${sessionId}/student/${studentId}`);
    return res.data;
  },

  async mobileCheckIn(payload) {
    const res = await api.post('/api/attendance/mobile-checkin', payload);
    return res.data;
  },

  async processBiometricPhoto(imageBase64) {
    const res = await api.post('/api/attendance/process-biometric-photo', { image_base64: imageBase64 });
    return res.data;
  },

  getExportCsvUrl(sessionId) {
    return `${api.defaults.baseURL}/api/attendance/session/${sessionId}/export-csv`;
  }
};
