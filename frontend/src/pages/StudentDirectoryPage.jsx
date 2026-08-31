import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserPlus, 
  Trash2, 
  QrCode, 
  Search, 
  RefreshCw, 
  CheckCircle, 
  X, 
  Download,
  AlertCircle,
  GraduationCap
} from 'lucide-react';
import { studentService } from '../services/studentService';

export default function StudentDirectoryPage() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('ALL');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedStudentQr, setSelectedStudentQr] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  // Form State (No Section, Only CSE / AI / ECE / EE)
  const [formData, setFormData] = useState({
    student_id: '',
    full_name: '',
    department: 'CSE',
    year: 3
  });
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const res = await studentService.listStudents({ 
        search: search || undefined,
        department: departmentFilter !== 'ALL' ? departmentFilter : undefined
      });
      setStudents(res.students || []);
    } catch (err) {
      console.error('Failed to load students:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [search, departmentFilter]);

  const handleAddStudent = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await studentService.registerStudent({
        student_id: formData.student_id.trim().toUpperCase(),
        full_name: formData.full_name.trim(),
        department: formData.department.trim().toUpperCase(),
        year: parseInt(formData.year, 10),
        section: ""
      });
      setShowAddModal(false);
      setFormData({
        student_id: '',
        full_name: '',
        department: 'CSE',
        year: 3
      });
      fetchStudents();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to register student.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteStudent = async (studentId, studentName) => {
    if (!window.confirm(`Are you sure you want to delete student '${studentName}' (${studentId})? This will also remove their face enrollment and attendance history.`)) {
      return;
    }
    setDeletingId(studentId);
    try {
      await studentService.deleteStudent(studentId);
      fetchStudents();
    } catch (err) {
      alert('Failed to delete student: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Student Directory & Enrollment</h1>
          <div className="page-subtitle">Register AGEMC students by Roll / Registration Number & generate QR tokens</div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={fetchStudents}>
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            <UserPlus size={15} />
            <span>Add New Student</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          {/* Department Tabs */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'All Departments' },
              { id: 'CSE', label: 'CSE (Cap: 30)' },
              { id: 'AI', label: 'AI (Cap: 30)' },
              { id: 'ECE', label: 'ECE (Cap: 60)' },
              { id: 'EE', label: 'EE (Cap: 60)' }
            ].map((dept) => (
              <button
                key={dept.id}
                onClick={() => setDepartmentFilter(dept.id)}
                className={`btn btn-sm ${departmentFilter === dept.id ? 'btn-primary' : 'btn-secondary'}`}
              >
                {dept.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', maxWidth: '380px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search by Roll / Reg No or Name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: '36px', fontSize: '13px' }}
              />
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
              {students.length} Students
            </span>
          </div>
        </div>
      </div>

      {/* Student Roster Table / Empty State */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {students.length === 0 && !loading ? (
          <div style={{ padding: '60px 24px', textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '16px', background: 'rgba(20, 184, 166, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: 'var(--accent-teal)' }}>
              <GraduationCap size={32} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>No Students Registered Yet</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '420px', margin: '0 auto 24px' }}>
              Add your college students using their Registration / Roll Number to generate their QR codes and enable AI attendance.
            </p>
            <button className="btn btn-primary" onClick={() => setShowAddModal(true)} style={{ padding: '10px 20px', fontSize: '14px' }}>
              <UserPlus size={16} />
              <span>Register First Student</span>
            </button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Roll / Reg No</th>
                  <th>Student Full Name</th>
                  <th>Department</th>
                  <th>Year</th>
                  <th>Biometric Status</th>
                  <th>Identity QR Token</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                      Loading students...
                    </td>
                  </tr>
                ) : (
                  students.map((stu) => (
                    <tr key={stu.student_id}>
                      <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-teal)' }}>
                        {stu.student_id}
                      </td>
                      <td style={{ fontWeight: 600 }}>{stu.full_name}</td>
                      <td>
                        <span className="badge badge-info">{stu.department}</span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>Year {stu.year}</td>
                      <td>
                        {stu.is_enrolled ? (
                          <span className="badge badge-present">
                            <CheckCircle size={12} /> Enrolled
                          </span>
                        ) : (
                          <span className="badge badge-info">Registered</span>
                        )}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                        {stu.qr_token}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setSelectedStudentQr(stu)}
                            title="View Student QR Code"
                          >
                            <QrCode size={14} />
                            <span>View QR</span>
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDeleteStudent(stu.student_id, stu.full_name)}
                            disabled={deletingId === stu.student_id}
                            title="Delete Student"
                          >
                            <Trash2 size={14} />
                            <span>{deletingId === stu.student_id ? 'Deleting...' : 'Delete'}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Add New Student */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <UserPlus size={20} style={{ color: 'var(--accent-teal)' }} />
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Register New Student</h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div style={{ padding: '10px 14px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: 'var(--status-absent)', fontSize: '13px', marginBottom: '16px' }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleAddStudent}>
              <div className="form-group">
                <label className="form-label">Roll Number / Registration Number *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. 231001001 or AGEMC-CSE-01"
                  value={formData.student_id}
                  onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Student Full Name *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. Rahul Sharma"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Department *</label>
                  <select
                    className="form-select"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  >
                    <option value="CSE">CSE (Computer Science)</option>
                    <option value="AI">AI (Artificial Intelligence)</option>
                    <option value="ECE">ECE (Electronics & Comm.)</option>
                    <option value="EE">EE (Electrical Engg.)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Year of Study *</label>
                  <select
                    className="form-select"
                    value={formData.year}
                    onChange={(e) => setFormData({ ...formData, year: e.target.value })}
                  >
                    <option value={1}>1st Year</option>
                    <option value={2}>2nd Year</option>
                    <option value={3}>3rd Year</option>
                    <option value={4}>4th Year</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Registering...' : 'Register Student & Generate QR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: View Student QR Code */}
      {selectedStudentQr && (
        <div className="modal-overlay" onClick={() => setSelectedStudentQr(null)}>
          <div className="modal-dialog" style={{ textAlign: 'center', maxWidth: '420px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700 }}>Student Identity QR Token</h3>
              <button
                onClick={() => setSelectedStudentQr(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {selectedStudentQr.full_name}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginBottom: '16px' }}>
              Roll/Reg: {selectedStudentQr.student_id} | {selectedStudentQr.department} Year {selectedStudentQr.year}
            </div>

            <div className="qr-container" style={{ margin: '0 auto' }}>
              <img
                src={studentService.getStudentQrUrl(selectedStudentQr.student_id)}
                alt="Student QR"
                className="qr-image"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
              <div className="qr-caption" style={{ fontSize: '12px' }}>{selectedStudentQr.qr_token}</div>
            </div>

            <div style={{ marginTop: '20px' }}>
              <a
                href={studentService.getStudentQrUrl(selectedStudentQr.student_id)}
                download={`${selectedStudentQr.student_id}_QR.png`}
                className="btn btn-secondary"
                target="_blank"
                rel="noreferrer"
              >
                <Download size={15} />
                <span>Download QR Code Image</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
