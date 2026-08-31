import React, { useState, useEffect } from 'react';
import { 
  QrCode, 
  Clock, 
  Users, 
  XCircle, 
  CheckCircle, 
  AlertTriangle, 
  RefreshCw, 
  Download,
  ShieldCheck,
  Copy,
  ExternalLink
} from 'lucide-react';
import { sessionService } from '../services/sessionService';
import { attendanceService } from '../services/attendanceService';

export default function ActiveSessionPage({ sessionId, onSessionClosed }) {
  const [sessionData, setSessionData] = useState(null);
  const [attendanceData, setAttendanceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [closing, setClosing] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const fetchSessionDetails = async () => {
    try {
      let targetId = sessionId;
      if (!targetId) {
        const activeRes = await sessionService.getActiveSessions();
        if (activeRes.sessions?.length > 0) {
          targetId = activeRes.sessions[0].id;
        }
      }

      if (!targetId) {
        setSessionData(null);
        setLoading(false);
        return;
      }

      const res = await sessionService.getSessionDetails(targetId);
      setSessionData(res);
      setCountdown(res.remaining_seconds || 0);

      const attRes = await attendanceService.getSessionAttendance(targetId);
      setAttendanceData(attRes);
    } catch (err) {
      console.error('Failed to fetch active session details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessionDetails();
    const interval = setInterval(fetchSessionDetails, 3000); // 3s polling
    return () => clearInterval(interval);
  }, [sessionId]);

  // Countdown timer local tick
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const handleCloseSession = async () => {
    if (!sessionData?.session?.id) return;
    if (!window.confirm(`Are you sure you want to close attendance for '${sessionData.session.subject}'?`)) {
      return;
    }

    setClosing(true);
    try {
      await sessionService.closeSession(sessionData.session.id);
      fetchSessionDetails();
      if (onSessionClosed) onSessionClosed();
    } catch (err) {
      alert('Failed to close session: ' + (err.response?.data?.detail || err.message));
    } finally {
      setClosing(false);
    }
  };

  const formatCountdown = (secs) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading && !sessionData) {
    return (
      <div className="page-wrapper">
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          Loading Active Classroom Session...
        </div>
      </div>
    );
  }

  if (!sessionData || !sessionData.session) {
    return (
      <div className="page-wrapper">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <QrCode size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 16px' }} />
          <h2>No Active Classroom Session</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
            There are currently no open attendance sessions. Create one from the Session Management menu.
          </p>
        </div>
      </div>
    );
  }

  const sess = sessionData.session;
  const isClosed = sess.status === 'CLOSED';
  const qrUrl = sessionService.getQrImageUrl(sess.id);
  const csvUrl = attendanceService.getExportCsvUrl(sess.id);

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 className="page-title">{sess.subject}</h1>
            <span className={`badge ${isClosed ? 'badge-absent' : 'badge-present'}`}>
              {sess.status}
            </span>
          </div>
          <div className="page-subtitle">
            Session Code: <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{sess.session_code}</span> | Room: {sess.room} | Faculty: {sess.faculty_name}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <a href={csvUrl} className="btn btn-secondary" target="_blank" rel="noreferrer">
            <Download size={16} />
            <span>Export CSV</span>
          </a>
          {!isClosed && (
            <button className="btn btn-danger" onClick={handleCloseSession} disabled={closing}>
              <XCircle size={16} />
              <span>{closing ? 'Closing...' : 'Close Attendance Session'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: QR Card on Left, Live Stats on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        {/* QR Projector Card */}
        <div className="card" style={{ textAlign: 'center' }}>
          <h2 className="card-title" style={{ marginBottom: '16px' }}>Classroom Projection QR</h2>
          
          <div className="qr-container">
            <img
              src={qrUrl}
              alt="Classroom Session QR"
              className="qr-image"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            <div className="qr-caption">{sess.session_code}</div>
          </div>

          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <Clock size={18} style={{ color: countdown < 120 ? 'var(--status-absent)' : 'var(--accent-teal)' }} />
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              {isClosed ? 'Session Closed' : `Attendance window closes in: `}
            </span>
            {!isClosed && (
              <strong style={{ fontSize: '18px', color: countdown < 120 ? 'var(--status-absent)' : 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {formatCountdown(countdown)}
              </strong>
            )}
          </div>
          
          <div style={{ marginTop: '8px' }}>
            <span className={`badge ${sessionData.timing_status === 'PRESENT' ? 'badge-present' : (sessionData.timing_status === 'LATE' ? 'badge-late' : 'badge-absent')}`}>
              Status: {sessionData.timing_status || sess.status}
            </span>
          </div>

          {/* Direct Mobile Link Box */}
          <div style={{ marginTop: '16px', padding: '12px', background: 'var(--bg-card)', borderRadius: '10px', border: '1px solid var(--border-color)', textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-teal)', textTransform: 'uppercase' }}>
                📱 Direct Student Mobile Link
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  const url = `http://${window.location.hostname}:5173/?session=${sess.session_code}`;
                  navigator.clipboard.writeText(url);
                  alert('Copied link: ' + url);
                }}
                style={{ padding: '2px 8px', fontSize: '11px' }}
                title="Copy student check-in link"
              >
                <Copy size={11} />
                <span>Copy Link</span>
              </button>
            </div>

            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)', wordBreak: 'break-all', background: 'var(--bg-surface)', padding: '6px 8px', borderRadius: '6px' }}>
              http://{window.location.hostname}:5173/?session={sess.session_code}
            </div>

            <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
              <a
                href={`/?session=${sess.session_code}`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary btn-sm"
                style={{ width: '100%', justifyContent: 'center', fontSize: '12px', padding: '7px 12px' }}
              >
                <ExternalLink size={13} />
                <span>Open Student Check-In (Test in Browser)</span>
              </a>
            </div>
          </div>

          <div style={{ marginTop: '14px', padding: '10px 14px', background: 'rgba(20, 184, 166, 0.08)', borderRadius: '6px', border: '1px solid rgba(20, 184, 166, 0.2)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'left' }}>
            <ShieldCheck size={16} style={{ color: 'var(--accent-teal)', flexShrink: 0 }} />
            <span>Face data is processed locally for attendance verification. No raw camera frames are permanently stored.</span>
          </div>
        </div>

        {/* Live Counters & Cohort Status */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Attendance Telemetry</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Auto-updating live</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div style={{ padding: '16px', background: 'var(--status-present-bg)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--status-present)', fontWeight: 600 }}>PRESENT</div>
              <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--status-present)', fontFamily: 'var(--font-mono)' }}>
                {attendanceData?.counts?.present_count || 0}
              </div>
            </div>

            <div style={{ padding: '16px', background: 'var(--status-late-bg)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--status-late)', fontWeight: 600 }}>LATE</div>
              <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--status-late)', fontFamily: 'var(--font-mono)' }}>
                {attendanceData?.counts?.late_count || 0}
              </div>
            </div>

            <div style={{ padding: '16px', background: 'var(--status-absent-bg)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--status-absent)', fontWeight: 600 }}>ABSENT</div>
              <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--status-absent)', fontFamily: 'var(--font-mono)' }}>
                {attendanceData?.counts?.absent_count || 0}
              </div>
            </div>

            <div style={{ padding: '16px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 600 }}>ATTENDANCE RATE</div>
              <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)' }}>
                {attendanceData?.counts?.attendance_rate || 0}%
              </div>
            </div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(20, 184, 166, 0.08)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={20} style={{ color: 'var(--accent-teal)' }} />
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Anti-Proxy & Liveness Verification Active: QR + 128-D SFace + Temporal Micro-motion.
            </div>
          </div>
        </div>
      </div>

      {/* Live Incoming Attendance Roster */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Live Attendance Feed ({attendanceData?.records?.length || 0})</h2>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Roll No</th>
                <th>Student Name</th>
                <th>Status</th>
                <th>Verification</th>
                <th>Similarity</th>
              </tr>
            </thead>
            <tbody>
              {attendanceData?.records?.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    Waiting for students to scan QR and verify face...
                  </td>
                </tr>
              ) : (
                attendanceData?.records?.map((rec) => (
                  <tr key={rec.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {rec.timestamp?.substring(11, 19)}
                    </td>
                    <td style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{rec.roll_no}</td>
                    <td>{rec.full_name}</td>
                    <td>
                      <span className={`badge ${rec.status === 'PRESENT' ? 'badge-present' : 'badge-late'}`}>
                        {rec.status}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-info" style={{ fontSize: '11px' }}>
                        {rec.verification_method}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {(rec.similarity_score * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
