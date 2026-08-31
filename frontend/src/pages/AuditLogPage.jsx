import React, { useState, useEffect } from 'react';
import { FileText, Search, Filter, RefreshCw, Download } from 'lucide-react';
import { securityService } from '../services/securityService';

export default function AuditLogPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');

  const fetchAuditEvents = async () => {
    setLoading(true);
    try {
      const params = {};
      if (severityFilter) params.severity = severityFilter;
      if (eventTypeFilter) params.event_type = eventTypeFilter;
      if (searchQuery) params.search = searchQuery;

      const res = await securityService.getAuditEvents(params);
      setEvents(res.events || []);
    } catch (err) {
      console.error('Failed to load audit events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, [severityFilter, eventTypeFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchAuditEvents();
  };

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Attendance Security Audit Trail</h1>
          <div className="page-subtitle">Immutable chronological log of all session verifications, mismatches & marks</div>
        </div>

        <button className="btn btn-secondary" onClick={fetchAuditEvents}>
          <RefreshCw size={16} />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: '20px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
            <div className="form-group" style={{ minWidth: '150px' }}>
              <select
                className="form-select"
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
              >
                <option value="">All Severities</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="HIGH">HIGH</option>
              </select>
            </div>

            <div className="form-group" style={{ minWidth: '180px' }}>
              <select
                className="form-select"
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
              >
                <option value="">All Event Types</option>
                <option value="ATTENDANCE_MARKED">ATTENDANCE_MARKED</option>
                <option value="IDENTITY_MISMATCH">IDENTITY_MISMATCH</option>
                <option value="LIVENESS_FAILED">LIVENESS_FAILED</option>
                <option value="LIVENESS_UNCERTAIN">LIVENESS_UNCERTAIN</option>
                <option value="REPLAY_ATTEMPT">REPLAY_ATTEMPT</option>
                <option value="DUPLICATE_ATTEMPT">DUPLICATE_ATTEMPT</option>
                <option value="QR_REJECTED">QR_REJECTED</option>
                <option value="SESSION_EXPIRED">SESSION_EXPIRED</option>
                <option value="SUSPICIOUS_ACTIVITY">SUSPICIOUS_ACTIVITY</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flex: '1', maxWidth: '360px' }}>
            <div style={{ position: 'relative', flex: '1' }}>
              <Search size={16} style={{ position: 'absolute', left: '10px', top: '12px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search reason, roll, session..."
                className="form-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '32px', width: '100%' }}
              />
            </div>
            <button type="submit" className="btn btn-primary">
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Audit Log Table */}
      <div className="card">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Timestamp</th>
                <th>Session</th>
                <th>Student</th>
                <th>Event Type</th>
                <th>Severity</th>
                <th>Result</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No audit records match the current filter criteria.
                  </td>
                </tr>
              ) : (
                events.map((evt) => (
                  <tr key={evt.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {evt.event_id}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {evt.timestamp?.substring(0, 19).replace('T', ' ')}
                    </td>
                    <td>{evt.session_code || `Session #${evt.session_id}`}</td>
                    <td>{evt.roll_no ? `${evt.full_name} (${evt.roll_no})` : '—'}</td>
                    <td>
                      <span className={`badge ${evt.severity === 'HIGH' ? 'badge-high' : (evt.severity === 'WARNING' ? 'badge-warning' : 'badge-info')}`}>
                        {evt.event_type}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${evt.severity === 'HIGH' ? 'badge-high' : (evt.severity === 'WARNING' ? 'badge-warning' : 'badge-info')}`}>
                        {evt.severity}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${evt.result === 'SUCCESS' ? 'badge-present' : 'badge-rejected'}`}>
                        {evt.result}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
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
