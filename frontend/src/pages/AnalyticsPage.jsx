import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  Sparkles, 
  BookOpen, 
  UserX, 
  RefreshCw, 
  CheckCircle2, 
  ShieldAlert, 
  Search,
  Clock,
  XCircle,
  ChevronRight,
  GraduationCap,
  Calendar
} from 'lucide-react';
import { analyticsService } from '../services/analyticsService';

export default function AnalyticsPage() {
  const [overview, setOverview] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [riskData, setRiskData] = useState(null);
  const [insightsData, setInsightsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [requiredThreshold, setRequiredThreshold] = useState(75.0);

  // Student Attendance Explorer State
  const [students, setStudents] = useState([]);
  const [selectedStudentRoll, setSelectedStudentRoll] = useState('');
  const [studentBreakdown, setStudentBreakdown] = useState(null);
  const [breakdownLoading, setBreakdownLoading] = useState(false);
  const [studentSearch, setStudentSearch] = useState('');

  const fetchAllAnalytics = async () => {
    setLoading(true);
    try {
      const [ov, tr, sb, rk, ins, stus] = await Promise.all([
        analyticsService.getOverview(),
        analyticsService.getAttendanceTrend(30),
        analyticsService.getSubjectBreakdown(),
        analyticsService.getRiskAnalysis(requiredThreshold),
        analyticsService.getAiInsights(requiredThreshold),
        analyticsService.getStudentProfiles()
      ]);

      setOverview(ov);
      setTrendData(tr);
      setSubjects(sb.subjects || []);
      setRiskData(rk);
      setInsightsData(ins);
      const stuList = stus.students || [];
      setStudents(stuList);

      if (stuList.length > 0 && !selectedStudentRoll) {
        setSelectedStudentRoll(stuList[0].student_id);
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAnalytics();
  }, [requiredThreshold]);

  // Fetch individual student breakdown
  useEffect(() => {
    if (!selectedStudentRoll) return;
    setBreakdownLoading(true);
    analyticsService.getStudentDetailedBreakdown(selectedStudentRoll)
      .then((data) => setStudentBreakdown(data))
      .catch((err) => console.error('Failed to load student breakdown:', err))
      .finally(() => setBreakdownLoading(false));
  }, [selectedStudentRoll]);

  const ovStats = overview?.overall_summary;
  const riskSummary = riskData || overview?.risk_summary;

  // Round Donut SVG Chart Calculations
  const presentPct = ovStats?.overall_attendance_percentage || 0;
  const absentPct = Math.max(0, 100 - presentPct);
  const circumference = 2 * Math.PI * 42; // r=42
  const strokeDashoffset = circumference - (presentPct / 100) * circumference;

  const filteredStudents = students.filter(s => 
    s.student_id.toLowerCase().includes(studentSearch.toLowerCase()) ||
    s.full_name.toLowerCase().includes(studentSearch.toLowerCase())
  );

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Attendance Analytics & Intelligence</h1>
          <div className="page-subtitle">Predictive risk analysis, round trend visualization & student class breakdowns</div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Threshold:</span>
            <select
              className="form-select"
              value={requiredThreshold}
              onChange={(e) => setRequiredThreshold(parseFloat(e.target.value))}
              style={{ padding: '6px 12px', fontSize: '13px' }}
            >
              <option value={75.0}>75% (AGEMC Standard)</option>
              <option value={80.0}>80% (Strict)</option>
              <option value={70.0}>70% (Relaxed)</option>
            </select>
          </div>

          <button className="btn btn-secondary" onClick={fetchAllAnalytics}>
            <RefreshCw size={15} />
            <span>Refresh Analytics</span>
          </button>
        </div>
      </div>

      {/* Top Level Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Overall Attendance</span>
            <div className="metric-icon"><TrendingUp size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: (ovStats?.overall_attendance_percentage || 0) >= requiredThreshold ? 'var(--status-present)' : 'var(--status-absent)' }}>
            {ovStats?.overall_attendance_percentage || 0}%
          </div>
          <div className="metric-footer">Across {ovStats?.total_classes || 0} total class sessions</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Total Enrolled</span>
            <div className="metric-icon"><GraduationCap size={18} /></div>
          </div>
          <div className="metric-value">{ovStats?.total_students || 0}</div>
          <div className="metric-footer">Active students in department</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">At-Risk Students</span>
            <div className="metric-icon" style={{ color: 'var(--status-absent)' }}><UserX size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-absent)' }}>
            {riskSummary?.high_risk_count || 0}
          </div>
          <div className="metric-footer">&lt; {requiredThreshold}% attendance trajectory</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Security Alerts</span>
            <div className="metric-icon" style={{ color: 'var(--status-late)' }}><ShieldAlert size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-late)' }}>
            {overview?.security_summary?.suspicious_events_today || 0}
          </div>
          <div className="metric-footer">Anti-proxy / spoof flags today</div>
        </div>
      </div>

      {/* Round Form Attendance Visualization & AI Insights */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        {/* Round Form Donut Gauge */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Daily Attendance Trends (Round Form)</h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around', flexWrap: 'wrap', gap: '24px', padding: '16px 0' }}>
            {/* SVG Circular Donut */}
            <div style={{ position: 'relative', width: '150px', height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="150" height="150" viewBox="0 0 100 100">
                {/* Background Ring */}
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="transparent"
                  stroke="rgba(239, 68, 68, 0.2)"
                  strokeWidth="9"
                />
                {/* Active Progress Ring */}
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="transparent"
                  stroke="var(--accent-teal)"
                  strokeWidth="9"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  transform="rotate(-90 50 50)"
                  style={{ transition: 'stroke-dashoffset 0.8s ease' }}
                />
              </svg>

              <div style={{ position: 'absolute', textAlign: 'center' }}>
                <div style={{ fontSize: '26px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  {presentPct}%
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Present Rate</div>
              </div>
            </div>

            {/* Legend Stats */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent-teal)' }}></span>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Present & On-Time:</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{presentPct}%</strong>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.5)' }}></span>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Absent / Missed:</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{absentPct.toFixed(1)}%</strong>
              </div>

              <div style={{ marginTop: '8px', padding: '8px 12px', background: 'var(--bg-card)', borderRadius: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                Required Minimum: <strong style={{ color: 'var(--accent-teal)' }}>{requiredThreshold}%</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Explainable AI Insights */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} style={{ color: 'var(--accent-teal)' }} />
              <h2 className="card-title">AI Academic Insights & Recommendations</h2>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {insightsData?.insights?.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                Conduct classroom sessions to generate AI insights.
              </div>
            ) : (
              insightsData?.insights?.slice(0, 3).map((ins, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px 16px',
                    background: 'var(--bg-card)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13px', color: 'var(--accent-teal)' }}>{ins.title}</strong>
                    <span className="badge badge-info" style={{ fontSize: '10px' }}>{ins.category}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{ins.message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 6. STUDENT-WISE DETAILED ATTENDANCE EXPLORER (CLASS-BY-CLASS) */}
      {/* ========================================================================= */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Student Class-by-Class Attendance Explorer</h2>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Select or search any student by Roll / Registration Number to view their detailed history across all classes
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '20px' }}>
          {/* Student Picker */}
          <div>
            <label className="form-label">Search / Select Student</label>
            <div style={{ position: 'relative', marginBottom: '8px' }}>
              <Search size={15} style={{ position: 'absolute', left: '10px', top: '11px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Filter by Roll or Name..."
                className="form-input"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
                style={{ paddingLeft: '32px', fontSize: '13px' }}
              />
            </div>

            <select
              className="form-select"
              value={selectedStudentRoll}
              onChange={(e) => setSelectedStudentRoll(e.target.value)}
            >
              {filteredStudents.map((s) => (
                <option key={s.student_id} value={s.student_id}>
                  {s.student_id} — {s.full_name} ({s.department} Y{s.year})
                </option>
              ))}
            </select>
          </div>

          {/* Quick Student Summary Card */}
          {studentBreakdown?.student && (
            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>{studentBreakdown.student.full_name}</h3>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                  Roll: {studentBreakdown.student.student_id} | {studentBreakdown.student.department} Year {studentBreakdown.student.year}
                </div>
                <div style={{ fontSize: '12px', marginTop: '6px' }}>
                  Present: <strong style={{ color: 'var(--status-present)' }}>{studentBreakdown.present_count}</strong> | 
                  Late: <strong style={{ color: 'var(--status-late)' }}> {studentBreakdown.late_count}</strong> | 
                  Absent: <strong style={{ color: 'var(--status-absent)' }}> {studentBreakdown.absent_count}</strong>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '26px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: studentBreakdown.attendance_rate >= requiredThreshold ? 'var(--status-present)' : 'var(--status-absent)' }}>
                  {studentBreakdown.attendance_rate}%
                </div>
                <span className={`badge ${studentBreakdown.attendance_rate >= requiredThreshold ? 'badge-present' : 'badge-absent'}`}>
                  {studentBreakdown.attendance_rate >= requiredThreshold ? 'SAFE' : 'AT RISK'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Detailed Class-by-Class Attendance Table */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>Subject / Course</th>
                <th>Room</th>
                <th>Faculty</th>
                <th>Attendance Status</th>
                <th>Check-In Time</th>
                <th>Verification</th>
              </tr>
            </thead>
            <tbody>
              {breakdownLoading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    Loading student class breakdown...
                  </td>
                </tr>
              ) : !studentBreakdown || studentBreakdown.classes?.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No classroom sessions recorded yet for this student's department/year.
                  </td>
                </tr>
              ) : (
                studentBreakdown.classes.map((cls, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {cls.start_time?.substring(0, 16).replace('T', ' ')}
                    </td>
                    <td style={{ fontWeight: 600 }}>{cls.subject}</td>
                    <td>{cls.room}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{cls.faculty_name}</td>
                    <td>
                      <span className={`badge ${cls.attendance_status === 'PRESENT' ? 'badge-present' : (cls.attendance_status === 'LATE' ? 'badge-late' : 'badge-absent')}`}>
                        {cls.attendance_status === 'PRESENT' && <CheckCircle2 size={12} />}
                        {cls.attendance_status === 'LATE' && <Clock size={12} />}
                        {cls.attendance_status === 'ABSENT' && <XCircle size={12} />}
                        <span>{cls.attendance_status}</span>
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-muted)' }}>
                      {cls.checkin_time ? cls.checkin_time.substring(11, 19) : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                      {cls.verification_method || 'N/A'}
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
