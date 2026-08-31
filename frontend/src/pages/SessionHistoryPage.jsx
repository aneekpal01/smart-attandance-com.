import React, { useState, useEffect } from 'react';
import { History, Download, Eye, Calendar, Users, Trash2 } from 'lucide-react';
import { sessionService } from '../services/sessionService';
import { attendanceService } from '../services/attendanceService';

export default function SessionHistoryPage({ onOpenSession }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const res = await sessionService.getSessionHistory(50);
      setHistory(res.history || []);
    } catch (err) {
      console.error('Failed to load session history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Session History & Archives</h1>
          <div className="page-subtitle">View past classroom sessions, attendance summaries, and download reports</div>
        </div>
      </div>

      <div className="card">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>Session Code</th>
                <th>Subject</th>
                <th>Cohort</th>
                <th>Faculty</th>
                <th>Present</th>
                <th>Late</th>
                <th>Absent</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No sessions recorded in database yet.
                  </td>
                </tr>
              ) : (
                history.map((sess) => {
                  const csvUrl = attendanceService.getExportCsvUrl(sess.id);
                  return (
                    <tr key={sess.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                        {sess.start_time?.substring(0, 16).replace('T', ' ')}
                      </td>
                      <td style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                        {sess.session_code}
                      </td>
                      <td style={{ fontWeight: 600 }}>{sess.subject}</td>
                      <td>{sess.department} Year {sess.year}</td>
                      <td>{sess.faculty_name}</td>
                      <td style={{ color: 'var(--status-present)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        {sess.present_count}
                      </td>
                      <td style={{ color: 'var(--status-late)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        {sess.late_count}
                      </td>
                      <td style={{ color: 'var(--status-absent)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        {sess.absent_count}
                      </td>
                      <td>
                        <span className={`badge ${sess.status === 'ACTIVE' ? 'badge-present' : 'badge-absent'}`}>
                          {sess.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                            onClick={() => onOpenSession && onOpenSession(sess.id)}
                            title="View Session Details"
                          >
                            <Eye size={14} />
                            <span>View</span>
                          </button>
                          <a
                            href={csvUrl}
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                            target="_blank"
                            rel="noreferrer"
                            title="Export CSV"
                          >
                            <Download size={14} />
                          </a>
                          <button
                            className="btn btn-danger"
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                            onClick={async () => {
                              if (window.confirm(`Permanently delete session '${sess.subject}' [${sess.session_code}] and its attendance records?`)) {
                                await sessionService.deleteSession(sess.id);
                                fetchHistory();
                              }
                            }}
                            title="Delete Session"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
