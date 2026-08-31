import React, { useState, useEffect } from 'react';
import { PlusCircle, QrCode, CheckCircle2, AlertCircle, Trash2, XCircle, RefreshCw } from 'lucide-react';
import { sessionService } from '../services/sessionService';

export default function SessionsPage({ onSelectSession }) {
  const [formData, setFormData] = useState({
    subject: '',
    department: 'CSE',
    year: 3,
    room: 'Room-101',
    faculty_name: '',
    regular_window_minutes: 10,
    late_window_minutes: 20
  });

  const [activeSessions, setActiveSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchActive = async () => {
    try {
      const res = await sessionService.getActiveSessions();
      setActiveSessions(res.sessions || []);
    } catch (err) {
      console.error('Failed to load active sessions:', err);
    }
  };

  useEffect(() => {
    fetchActive();
    const interval = setInterval(fetchActive, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: (name === 'year' || name === 'regular_window_minutes' || name === 'late_window_minutes')
        ? parseInt(value, 10)
        : value
    }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await sessionService.createSession({
        ...formData,
        section: ""
      });
      setSuccessMsg(`Session created successfully: ${res.session.session_code}`);
      fetchActive();
      if (onSelectSession) {
        onSelectSession(res.session.id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create session.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Are you sure you want to purge ALL past sessions and records from history?")) {
      return;
    }
    try {
      await sessionService.clearAllSessions();
      fetchActive();
      setSuccessMsg("All session history cleared successfully.");
    } catch (err) {
      alert("Failed to clear sessions: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Classroom Session Management</h1>
          <div className="page-subtitle">Create attendance sessions & generate temporary session QRs for AGEMC</div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={fetchActive}>
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
          <button className="btn btn-danger" onClick={handleClearAll} title="Wipe all past demo sessions">
            <Trash2 size={15} />
            <span>Clear All Sessions</span>
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Create Session Form */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Create New Classroom Session</h2>
          </div>

          {error && (
            <div style={{ padding: '12px', background: 'var(--badge-absent-bg)', color: 'var(--status-absent)', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', fontSize: '13px' }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div style={{ padding: '12px', background: 'var(--badge-present-bg)', color: 'var(--status-present)', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', fontSize: '13px' }}>
              <CheckCircle2 size={18} />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label className="form-label">Subject / Course Name *</label>
              <input
                type="text"
                name="subject"
                className="form-input"
                placeholder="e.g. Data Structures & Algorithms"
                value={formData.subject}
                onChange={handleChange}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Department *</label>
                <select name="department" className="form-select" value={formData.department} onChange={handleChange}>
                  <option value="CSE">CSE (Computer Science)</option>
                  <option value="AI">AI (Artificial Intelligence)</option>
                  <option value="ECE">ECE (Electronics & Comm.)</option>
                  <option value="EE">EE (Electrical Engg.)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Year of Study *</label>
                <select name="year" className="form-select" value={formData.year} onChange={handleChange}>
                  <option value={1}>1st Year</option>
                  <option value={2}>2nd Year</option>
                  <option value={3}>3rd Year</option>
                  <option value={4}>4th Year</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Room / Hall *</label>
              <input
                type="text"
                name="room"
                className="form-input"
                placeholder="e.g. LH-101 / AI-Lab"
                value={formData.room}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Faculty Name *</label>
              <input
                type="text"
                name="faculty_name"
                className="form-input"
                placeholder="e.g. Prof. R. K. Sen"
                value={formData.faculty_name}
                onChange={handleChange}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Regular Window (mins)</label>
                <input
                  type="number"
                  name="regular_window_minutes"
                  className="form-input"
                  min="1"
                  max="120"
                  value={formData.regular_window_minutes}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Late Window (mins)</label>
                <input
                  type="number"
                  name="late_window_minutes"
                  className="form-input"
                  min="1"
                  max="240"
                  value={formData.late_window_minutes}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div style={{ marginTop: '20px' }}>
              <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', padding: '11px' }}>
                <PlusCircle size={18} />
                <span>{loading ? 'Generating Session...' : 'Create & Start Classroom Session'}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Active Sessions List */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Currently Active Sessions ({activeSessions.length})</h2>
          </div>

          {activeSessions.length === 0 ? (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No active sessions running. Create a new session on the left to start live attendance.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {activeSessions.map((sess) => (
                <div
                  key={sess.id}
                  style={{
                    padding: '16px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge badge-present">{sess.session_code}</span>
                        <strong style={{ fontSize: '15px' }}>{sess.subject}</strong>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Room: {sess.room} | Dept: {sess.department} Year {sess.year} | Faculty: {sess.faculty_name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--accent-teal)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                        Present: {sess.present_count} | Late: {sess.late_count} | Total: {sess.total_students}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onSelectSession && onSelectSession(sess.id)}
                      title="View Classroom Projector QR"
                    >
                      <QrCode size={14} />
                      <span>View QR</span>
                    </button>

                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={async () => {
                        if (window.confirm(`Close attendance window for '${sess.subject}'?`)) {
                          await sessionService.closeSession(sess.id);
                          fetchActive();
                        }
                      }}
                      title="Close Active Session"
                    >
                      <XCircle size={14} />
                      <span>Close</span>
                    </button>

                    <button
                      className="btn btn-danger btn-sm"
                      onClick={async () => {
                        if (window.confirm(`Permanently delete session '${sess.subject}' [${sess.session_code}]?`)) {
                          await sessionService.deleteSession(sess.id);
                          fetchActive();
                        }
                      }}
                      title="Delete Session"
                    >
                      <Trash2 size={14} />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
