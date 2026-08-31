import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  UserX, 
  RefreshCw, 
  Copy, 
  AlertTriangle, 
  Search,
  UserCheck
} from 'lucide-react';
import { securityService } from '../services/securityService';

export default function SecurityPanelPage() {
  const [suspiciousEvents, setSuspiciousEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchSecurityFeed = async () => {
    try {
      const res = await securityService.getSuspiciousActivityFeed(100);
      setSuspiciousEvents(res.suspicious_events || []);
    } catch (err) {
      console.error('Failed to load security feed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityFeed();
    const interval = setInterval(fetchSecurityFeed, 4000);
    return () => clearInterval(interval);
  }, []);

  const filteredEvents = suspiciousEvents.filter((evt) => {
    const q = searchQuery.toLowerCase();
    return (
      evt.reason?.toLowerCase().includes(q) ||
      evt.event_type?.toLowerCase().includes(q) ||
      evt.culprit_roll_no?.toLowerCase().includes(q) ||
      evt.culprit_name?.toLowerCase().includes(q) ||
      evt.target_roll_no?.toLowerCase().includes(q) ||
      evt.target_name?.toLowerCase().includes(q) ||
      evt.session_code?.toLowerCase().includes(q)
    );
  });

  const countByType = (type) => suspiciousEvents.filter((e) => e.event_type === type).length;

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Security & Anti-Proxy Control Panel</h1>
          <div className="page-subtitle">Tracks student proxy attempts, identity mismatches, and spoofing alerts</div>
        </div>

        <button className="btn btn-secondary" onClick={fetchSecurityFeed}>
          <RefreshCw size={15} />
          <span>Refresh Feed</span>
        </button>
      </div>

      {/* Security Telemetry Counters */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Proxy Mismatches</span>
            <div className="metric-icon" style={{ color: 'var(--status-rejected)' }}><UserX size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-rejected)' }}>
            {countByType('IDENTITY_MISMATCH')}
          </div>
          <div className="metric-footer">Scanning friend's QR with own face</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Spoof Blocks</span>
            <div className="metric-icon" style={{ color: 'var(--status-absent)' }}><ShieldAlert size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-absent)' }}>
            {countByType('LIVENESS_FAILED')}
          </div>
          <div className="metric-footer">Photo / phone screen replays</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Replay Attempts</span>
            <div className="metric-icon" style={{ color: 'var(--status-late)' }}><Copy size={18} /></div>
          </div>
          <div className="metric-value" style={{ color: 'var(--status-late)' }}>
            {countByType('REPLAY_ATTEMPT')}
          </div>
          <div className="metric-footer">Reused token transactions</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Unknown Faces</span>
            <div className="metric-icon"><AlertTriangle size={18} /></div>
          </div>
          <div className="metric-value">
            {countByType('FACE_UNKNOWN')}
          </div>
          <div className="metric-footer">Unenrolled faces presented</div>
        </div>
      </div>

      {/* Security Events Table with Culprit and Target Info */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="card-header" style={{ padding: '20px 24px 12px' }}>
          <div>
            <h2 className="card-title">Live Security Telemetry & Cheating Attempt Log</h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Identifies who attempted proxy cheating and whose attendance they tried to falsely record
            </div>
          </div>

          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={15} style={{ position: 'absolute', left: '10px', top: '11px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search Culprit / Target / Roll..."
              className="form-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '32px', fontSize: '13px' }}
            />
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Attempted By (Culprit)</th>
                <th>Whose Proxy Was Attempted (Target)</th>
                <th>Violation Type</th>
                <th>Class Session</th>
                <th>Diagnostic Reason</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    ✓ No proxy or suspicious activities flagged. All verifications genuine.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr key={evt.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {evt.timestamp?.substring(11, 19)}
                    </td>
                    <td>
                      <div style={{ fontWeight: 700, color: 'var(--status-absent)' }}>
                        {evt.culprit_name}
                      </div>
                      <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        Roll: {evt.culprit_roll_no}
                      </div>
                    </td>
                    <td>
                      {evt.target_roll_no ? (
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {evt.target_name}
                          </div>
                          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent-teal)' }}>
                            Roll: {evt.target_roll_no}
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>N/A</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${evt.severity === 'HIGH' ? 'badge-high' : 'badge-warning'}`}>
                        {evt.event_type}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{evt.subject || 'Session'}</div>
                      <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {evt.session_code}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '12px', maxWidth: '300px' }}>
                      {evt.reason}
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
