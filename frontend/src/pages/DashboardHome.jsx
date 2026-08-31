import React, { useEffect, useState } from 'react';
import { 
  Calendar, 
  Activity, 
  UserCheck, 
  TrendingUp, 
  ShieldAlert, 
  ArrowRight, 
  PlusCircle, 
  QrCode,
  AlertTriangle,
  CalendarPlus
} from 'lucide-react';
import { securityService } from '../services/securityService';
import MiniCalendar2026 from '../components/MiniCalendar2026';

export default function DashboardHome({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOverview = async () => {
    try {
      const res = await securityService.getDashboardOverview();
      setData(res);
      setError(null);
    } catch (err) {
      console.error('Failed to load dashboard overview:', err);
      setError('Could not connect to local backend API. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 4000); // 4s local poll
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="page-wrapper">
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          Loading AGEMC Attend AI Dashboard...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="page-wrapper">
        <div className="card" style={{ borderColor: 'var(--status-absent)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--status-absent)' }}>
            <AlertTriangle size={24} />
            <div>
              <h3 style={{ margin: 0 }}>Backend Connection Error</h3>
              <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)' }}>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const activeSess = data?.active_session;

  return (
    <div className="page-wrapper">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Faculty Dashboard</h1>
          <div className="page-subtitle">Real-time attendance monitor & AI vision security control</div>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => onNavigate('sessions')}>
            <PlusCircle size={16} />
            <span>New Session</span>
          </button>
          {activeSess && (
            <button className="btn btn-primary" onClick={() => onNavigate('active-session')}>
              <QrCode size={16} />
              <span>View Active QR</span>
            </button>
          )}
        </div>
      </div>

      {/* Top 5 High-Level KPI Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Today's Sessions</span>
            <div className="metric-icon"><Calendar size={18} /></div>
          </div>
          <div className="metric-value">{data?.today_sessions_count || 0}</div>
          <div className="metric-footer">Classroom sessions today</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Session</span>
            <div className="metric-icon" style={{ color: activeSess ? 'var(--status-present)' : 'var(--text-muted)' }}>
              <Activity size={18} />
            </div>
          </div>
          <div className="metric-value" style={{ fontSize: '18px', color: activeSess ? 'var(--status-present)' : 'var(--text-muted)' }}>
            {activeSess ? activeSess.subject : 'No Active Session'}
          </div>
          <div className="metric-footer">
            {activeSess ? `Room: ${activeSess.room} (${activeSess.session_code})` : 'No session running'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Enrolled Students</span>
            <div className="metric-icon"><UserCheck size={18} /></div>
          </div>
          <div className="metric-value">{data?.total_students || data?.enrolled_students || 0}</div>
          <div className="metric-footer">Active students in department</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Today's Present</span>
            <div className="metric-icon"><TrendingUp size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-present)' }}>
            {data?.today_present_total || 0}
          </div>
          <div className="metric-footer">Marked today (Present + Late)</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Security Alerts</span>
            <div className="metric-icon" style={{ color: (data?.security_alerts_count || 0) > 0 ? 'var(--status-late)' : 'var(--text-muted)' }}>
              <ShieldAlert size={18} />
            </div>
          </div>
          <div className="metric-value" style={{ color: (data?.security_alerts_count || 0) > 0 ? 'var(--status-late)' : 'var(--text-primary)' }}>
            {data?.security_alerts_count || 0}
          </div>
          <div className="metric-footer">Suspicious / Mismatch flags</div>
        </div>
      </div>

      {/* Active Session Live Card (if active) */}
      {activeSess && (
        <div className="card" style={{ borderColor: 'rgba(20, 184, 166, 0.4)', background: 'linear-gradient(180deg, rgba(20, 184, 166, 0.05) 0%, var(--bg-surface) 100%)', marginBottom: '24px' }}>
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="badge badge-present" style={{ fontSize: '13px' }}>● LIVE NOW</span>
              <h2 className="card-title" style={{ margin: 0 }}>
                {activeSess.subject} [{activeSess.session_code}]
              </h2>
            </div>
            <button className="btn btn-primary" onClick={() => onNavigate('active-session')}>
              <span>Launch Classroom Screen</span>
              <ArrowRight size={16} />
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Room & Cohort</span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '2px' }}>
                {activeSess.room} | {activeSess.department} Year {activeSess.year}
              </div>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Faculty</span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '2px' }}>
                {activeSess.faculty_name}
              </div>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Present / Total</span>
              <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-present)', fontFamily: 'var(--font-mono)' }}>
                {activeSess.present_count || 0} / {activeSess.total_cohort || 0}
              </div>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Late / Absent</span>
              <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-late)', fontFamily: 'var(--font-mono)' }}>
                {activeSess.late_count || 0} / {activeSess.absent_count || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid: 2026 Mini Calendar Widget + Recent Security Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        {/* 2026 Academic Calendar Widget */}
        <div style={{ minHeight: '260px' }}>
          <MiniCalendar2026 />
        </div>

        {/* Recent Security Alerts Widget */}
        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <h2 className="card-title">Recent Anti-Proxy & Security Activity</h2>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('security')}>
              <span>Security Telemetry</span>
              <ArrowRight size={13} />
            </button>
          </div>

          <div style={{ flex: 1 }}>
            {data?.recent_alerts?.length === 0 ? (
              <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                ✓ No suspicious verification events recorded. All attendance verified cleanly.
              </div>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Session</th>
                      <th>Student</th>
                      <th>Type</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.recent_alerts?.slice(0, 4).map((alert) => (
                      <tr key={alert.id}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                          {alert.timestamp?.substring(11, 19)}
                        </td>
                        <td style={{ fontSize: '12px' }}>{alert.session_code || `Session #${alert.session_id}`}</td>
                        <td style={{ fontSize: '12px' }}>{alert.roll_no ? `${alert.full_name} (${alert.roll_no})` : 'Unknown / N/A'}</td>
                        <td>
                          <span className={`badge ${alert.severity === 'HIGH' ? 'badge-high' : 'badge-warning'}`} style={{ fontSize: '10px' }}>
                            {alert.event_type}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${alert.severity === 'HIGH' ? 'badge-high' : 'badge-warning'}`} style={{ fontSize: '10px' }}>
                            {alert.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Hero: Quick Create & Start New Classroom Session */}
      <div className="card" style={{ marginTop: '24px', padding: '20px 24px', background: 'linear-gradient(135deg, rgba(20, 184, 166, 0.12) 0%, rgba(56, 189, 248, 0.06) 100%)', border: '1px solid rgba(20, 184, 166, 0.35)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CalendarPlus size={20} style={{ color: 'var(--accent-teal)' }} />
            <span>Ready to Take Classroom Attendance?</span>
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Start a new lecture session for CSE (30), AI (30), ECE (60), or EE (60) with live Projector QR & Retina verification.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => onNavigate('sessions')} style={{ padding: '10px 20px', fontSize: '14px', fontWeight: 700 }}>
          <PlusCircle size={16} />
          <span>Create & Start New Session</span>
        </button>
      </div>
    </div>
  );
}
