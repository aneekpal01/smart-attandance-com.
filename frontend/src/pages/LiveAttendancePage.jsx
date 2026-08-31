import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Download, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  PlusCircle, 
  Trash2, 
  Edit3, 
  X, 
  AlertCircle
} from 'lucide-react';
import { sessionService } from '../services/sessionService';
import { attendanceService } from '../services/attendanceService';
import { studentService } from '../services/studentService';

export default function LiveAttendancePage({ initialSessionId }) {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(initialSessionId || '');
  const [attendanceData, setAttendanceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Manual Override Modal
  const [showManualModal, setShowManualModal] = useState(false);
  const [allStudents, setAllStudents] = useState([]);
  const [manualForm, setManualForm] = useState({
    student_id: '',
    status: 'PRESENT',
    reason: 'FACULTY_MANUAL_ENTRY'
  });
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);

  // 1. Fetch available sessions & all registered students
  const loadSessions = async () => {
    try {
      const res = await sessionService.getActiveSessions();
      const active = res.sessions || [];
      const hist = await sessionService.getSessionHistory(20);
      const combined = [...active, ...(hist.history || []).filter(h => !active.some(a => a.id === h.id))];
      setSessions(combined);

      if (combined.length > 0 && !selectedSessionId) {
        setSelectedSessionId(combined[0].id);
      }

      const stuRes = await studentService.listStudents();
      setAllStudents(stuRes.students || []);
    } catch (err) {
      console.error('Failed to load sessions or students:', err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // 2. Fetch attendance for selected session
  const fetchAttendance = async () => {
    if (!selectedSessionId) return;
    try {
      const res = await attendanceService.getSessionAttendance(selectedSessionId);
      setAttendanceData(res);
    } catch (err) {
      console.error('Failed to load session attendance:', err);
    }
  };

  useEffect(() => {
    if (!selectedSessionId) return;
    setLoading(true);
    fetchAttendance().finally(() => setLoading(false));

    if (autoRefresh) {
      const interval = setInterval(fetchAttendance, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedSessionId, autoRefresh]);

  // Consolidate complete roster list
  const buildRoster = () => {
    if (!attendanceData) return [];
    const marked = attendanceData.records || [];
    const markedMap = {};
    marked.forEach((r) => {
      markedMap[r.roll_no] = r;
    });

    const roster = [];

    // Present
    (attendanceData.present_students || []).forEach((p) => {
      const rec = markedMap[p.student_id];
      roster.push({
        student_db_id: p.id || rec?.student_id,
        student_id: p.student_id,
        full_name: p.full_name,
        status: 'PRESENT',
        timestamp: p.timestamp,
        similarity: p.similarity,
        verification: rec?.verification_method || 'QR_FACE_LIVENESS'
      });
    });

    // Late
    (attendanceData.late_students || []).forEach((l) => {
      const rec = markedMap[l.student_id];
      roster.push({
        student_db_id: l.id || rec?.student_id,
        student_id: l.student_id,
        full_name: l.full_name,
        status: 'LATE',
        timestamp: l.timestamp,
        similarity: l.similarity,
        verification: rec?.verification_method || 'QR_FACE_LIVENESS'
      });
    });

    // Absent
    (attendanceData.absent_students || []).forEach((a) => {
      roster.push({
        student_db_id: a.id,
        student_id: a.student_id,
        full_name: a.full_name,
        status: 'ABSENT',
        timestamp: 'N/A',
        similarity: null,
        verification: 'N/A'
      });
    });

    return roster;
  };

  const roster = buildRoster();

  // Filter & search
  const filteredRoster = roster.filter((stu) => {
    const matchesStatus = statusFilter === 'ALL' || stu.status === statusFilter;
    const matchesSearch =
      stu.student_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stu.full_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  // Handle manual status toggle for a student
  const handleQuickStatusChange = async (studentId, studentDbId, newStatus) => {
    if (!selectedSessionId) return;
    try {
      // Find student DB ID if missing
      let dbId = studentDbId;
      if (!dbId) {
        const found = allStudents.find(s => s.student_id === studentId);
        dbId = found ? found.id : null;
      }
      if (!dbId) {
        alert('Student record ID could not be resolved.');
        return;
      }

      await attendanceService.manualMarkAttendance({
        session_id: parseInt(selectedSessionId, 10),
        student_id: dbId,
        status: newStatus,
        reason: 'FACULTY_QUICK_TOGGLE'
      });

      fetchAttendance();
    } catch (err) {
      alert('Failed to update status: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Handle delete / clear attendance record
  const handleDeleteRecord = async (studentId, studentDbId, studentName) => {
    if (!window.confirm(`Clear attendance record for '${studentName}' (${studentId}) and mark as ABSENT?`)) {
      return;
    }
    try {
      let dbId = studentDbId;
      if (!dbId) {
        const found = allStudents.find(s => s.student_id === studentId);
        dbId = found ? found.id : null;
      }
      if (dbId) {
        await attendanceService.deleteAttendanceRecord(selectedSessionId, dbId);
        fetchAttendance();
      }
    } catch (err) {
      alert('Failed to clear record: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Submit Manual Entry Modal
  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualForm.student_id) return;
    setManualSubmitting(true);
    try {
      await attendanceService.manualMarkAttendance({
        session_id: parseInt(selectedSessionId, 10),
        student_id: parseInt(manualForm.student_id, 10),
        status: manualForm.status,
        reason: manualForm.reason
      });
      setShowManualModal(false);
      fetchAttendance();
      setActionSuccess('Manual attendance recorded successfully.');
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err) {
      alert('Failed to record manual attendance: ' + (err.response?.data?.detail || err.message));
    } finally {
      setManualSubmitting(false);
    }
  };

  const csvExportUrl = selectedSessionId ? attendanceService.getExportCsvUrl(selectedSessionId) : '#';
  const counts = attendanceData?.counts || {};

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Live Attendance Roster</h1>
          <div className="page-subtitle">Real-time presence tracking, manual faculty overrides & CSV export</div>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            className={`btn ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw size={15} />
            <span>{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
          </button>

          <button className="btn btn-primary" onClick={() => {
            if (sessions.length === 0) {
              alert("No classroom sessions exist yet. Please create a session first from 'Create Session' menu.");
              return;
            }
            if (!selectedSessionId && sessions.length > 0) {
              setSelectedSessionId(sessions[0].id);
            }
            setShowManualModal(true);
          }}>
            <PlusCircle size={15} />
            <span>Manual Add / Override</span>
          </button>

          {selectedSessionId && (
            <a href={csvExportUrl} className="btn btn-secondary" target="_blank" rel="noreferrer">
              <Download size={15} />
              <span>Export CSV</span>
            </a>
          )}
        </div>
      </div>

      {actionSuccess && (
        <div style={{ padding: '10px 16px', background: 'var(--badge-present-bg)', color: 'var(--status-present)', borderRadius: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <CheckCircle2 size={16} />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Structured 2-Tier Control Bar */}
      <div className="card" style={{ padding: '18px 20px', marginBottom: '20px' }}>
        {/* Tier 1: Session Selector */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', minWidth: '280px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              Select Session:
            </span>
            <select
              className="form-select"
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              style={{ flex: 1, minWidth: '200px' }}
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  [{s.session_code}] {s.subject} ({s.department} Year {s.year}) • {s.status}
                </option>
              ))}
            </select>

            {selectedSessionId && (
              <button
                className="btn btn-danger btn-sm"
                onClick={async () => {
                  const currentSess = sessions.find(s => s.id === parseInt(selectedSessionId, 10));
                  const subjName = currentSess?.subject || 'this session';
                  if (window.confirm(`Permanently remove / delete session '${subjName}' and its records?`)) {
                    await sessionService.deleteSession(selectedSessionId);
                    loadSessions();
                    setSelectedSessionId('');
                  }
                }}
                title="Delete this classroom session"
              >
                <Trash2 size={14} />
                <span>Delete Session</span>
              </button>
            )}
          </div>

          {attendanceData?.session && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span className="badge badge-info">{attendanceData.session.room}</span>
              <span className="badge badge-present">{counts.attendance_rate || 0}% Attended</span>
            </div>
          )}
        </div>

        {/* Tier 2: Status Filter Tabs & Search Box */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', paddingTop: '16px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'All', count: counts.total_registered || roster.length },
              { id: 'PRESENT', label: 'Present', count: counts.present_count || 0 },
              { id: 'LATE', label: 'Late', count: counts.late_count || 0 },
              { id: 'ABSENT', label: 'Absent', count: counts.absent_count || 0 }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`btn ${statusFilter === tab.id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
              >
                <span>{tab.label}</span>
                <span style={{ opacity: 0.75, fontFamily: 'var(--font-mono)', fontSize: '11px' }}>({tab.count})</span>
              </button>
            ))}
          </div>

          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search Roll No or Name..."
              className="form-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '36px', paddingRight: '12px', fontSize: '13px' }}
            />
          </div>
        </div>
      </div>

      {/* Attendance Roster Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Roll Number</th>
                <th>Student Name</th>
                <th>Status</th>
                <th>Verification Method</th>
                <th>Check-In Time</th>
                <th>Similarity</th>
                <th style={{ textAlign: 'right' }}>Faculty Override & Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && !attendanceData ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    Loading attendance records...
                  </td>
                </tr>
              ) : filteredRoster.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No students match the current filter or search criteria.
                  </td>
                </tr>
              ) : (
                filteredRoster.map((stu) => (
                  <tr key={stu.student_id}>
                    <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{stu.student_id}</td>
                    <td style={{ fontWeight: 500 }}>{stu.full_name}</td>
                    <td>
                      <span className={`badge ${stu.status === 'PRESENT' ? 'badge-present' : (stu.status === 'LATE' ? 'badge-late' : 'badge-absent')}`}>
                        {stu.status === 'PRESENT' && <CheckCircle2 size={12} />}
                        {stu.status === 'LATE' && <Clock size={12} />}
                        {stu.status === 'ABSENT' && <XCircle size={12} />}
                        <span>{stu.status}</span>
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      {stu.verification}
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {stu.timestamp ? stu.timestamp.substring(11, 19) || stu.timestamp : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {stu.similarity ? `${(stu.similarity * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                        {/* Quick Status Buttons */}
                        <button
                          className={`btn btn-sm ${stu.status === 'PRESENT' ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '3px 8px', fontSize: '11px', fontWeight: 700 }}
                          onClick={() => handleQuickStatusChange(stu.student_id, stu.student_db_id, 'PRESENT')}
                          title="Mark Present"
                        >
                          P
                        </button>
                        <button
                          className={`btn btn-sm ${stu.status === 'LATE' ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '3px 8px', fontSize: '11px', fontWeight: 700, color: stu.status === 'LATE' ? '#fff' : 'var(--status-late)' }}
                          onClick={() => handleQuickStatusChange(stu.student_id, stu.student_db_id, 'LATE')}
                          title="Mark Late"
                        >
                          L
                        </button>
                        <button
                          className={`btn btn-sm ${stu.status === 'ABSENT' ? 'btn-danger' : 'btn-secondary'}`}
                          style={{ padding: '3px 8px', fontSize: '11px', fontWeight: 700 }}
                          onClick={() => handleQuickStatusChange(stu.student_id, stu.student_db_id, 'ABSENT')}
                          title="Mark Absent"
                        >
                          A
                        </button>

                        {/* Delete / Clear */}
                        {stu.status !== 'ABSENT' && (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '3px 6px', color: 'var(--status-absent)' }}
                            onClick={() => handleDeleteRecord(stu.student_id, stu.student_db_id, stu.full_name)}
                            title="Clear Attendance"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Manual Add / Override Attendance */}
      {showManualModal && (
        <div className="modal-overlay" onClick={() => setShowManualModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Edit3 size={20} style={{ color: 'var(--accent-teal)' }} />
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Manual Attendance Override</h3>
              </div>
              <button
                onClick={() => setShowManualModal(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleManualSubmit}>
              <div className="form-group">
                <label className="form-label">Classroom Session *</label>
                <select
                  required
                  className="form-select"
                  value={selectedSessionId}
                  onChange={(e) => setSelectedSessionId(e.target.value)}
                >
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      [{s.session_code}] {s.subject} ({s.department} Year {s.year}) • {s.status}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Select Student *</label>
                <select
                  required
                  className="form-select"
                  value={manualForm.student_id}
                  onChange={(e) => setManualForm({ ...manualForm, student_id: e.target.value })}
                >
                  <option value="">-- Choose Student --</option>
                  {allStudents.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.student_id} — {s.full_name} ({s.department} Year {s.year})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Attendance Status *</label>
                <select
                  className="form-select"
                  value={manualForm.status}
                  onChange={(e) => setManualForm({ ...manualForm, status: e.target.value })}
                >
                  <option value="PRESENT">PRESENT</option>
                  <option value="LATE">LATE</option>
                  <option value="ABSENT">ABSENT</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Reason / Justification</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Excused Medical Leave, Camera Glitch, Permission"
                  value={manualForm.reason}
                  onChange={(e) => setManualForm({ ...manualForm, reason: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowManualModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={manualSubmitting}>
                  {manualSubmitting ? 'Saving...' : 'Save Attendance Status'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
