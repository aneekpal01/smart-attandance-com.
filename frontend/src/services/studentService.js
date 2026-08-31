import api from './api';

export const studentService = {
  async listStudents(params = {}) {
    const res = await api.get('/api/students/', { params });
    return res.data;
  },

  async registerStudent(payload) {
    const res = await api.post('/api/students/register', payload);
    return res.data;
  },

  async deleteStudent(studentId) {
    const res = await api.delete(`/api/students/${studentId}`);
    return res.data;
  },

  getStudentQrUrl(studentId) {
    return `${api.defaults.baseURL}/api/students/${studentId}/qr-image`;
  }
};
