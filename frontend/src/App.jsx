import React, { useState, useEffect } from 'react';
import { Menu, QrCode, Smartphone } from 'lucide-react';
import Navbar from './components/Navbar';
import DashboardHome from './pages/DashboardHome';
import SessionsPage from './pages/SessionsPage';
import ActiveSessionPage from './pages/ActiveSessionPage';
import LiveAttendancePage from './pages/LiveAttendancePage';
import StudentDirectoryPage from './pages/StudentDirectoryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SecurityPanelPage from './pages/SecurityPanelPage';
import AuditLogPage from './pages/AuditLogPage';
import SessionHistoryPage from './pages/SessionHistoryPage';
import StudentCheckInPortal from './pages/StudentCheckInPortal';
import { sessionService } from './services/sessionService';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [activeSessionCount, setActiveSessionCount] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Check URL query parameters (e.g. from Google Lens or phone QR scanning)
  const urlParams = new URLSearchParams(window.location.search);
  const urlSessionCode = urlParams.get('session');
  const [isStudentCheckInMode, setIsStudentCheckInMode] = useState(Boolean(urlSessionCode));

  // Day / Night Theme State
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('smartattend_theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const checkActiveSessions = async () => {
    try {
      const res = await sessionService.getActiveSessions();
      const count = res.sessions?.length || 0;
      setActiveSessionCount(count);
      if (count > 0 && !selectedSessionId) {
        setSelectedSessionId(res.sessions[0].id);
      }
    } catch (err) {
      console.error('Active session check failed:', err);
    }
  };

  useEffect(() => {
    checkActiveSessions();
    const interval = setInterval(checkActiveSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setCurrentTab('active-session');
    setMobileOpen(false);
  };

  // If accessed directly via Google Lens / Phone QR scanner URL
  if (isStudentCheckInMode) {
    return (
      <StudentCheckInPortal
        sessionCodeFromUrl={urlSessionCode}
        onBackToFaculty={() => {
          setIsStudentCheckInMode(false);
          window.history.replaceState({}, document.title, window.location.pathname);
        }}
      />
    );
  }

  return (
    <div className="app-container">
      {/* Mobile Sliding Overlay */}
      <div
        className={`mobile-overlay ${mobileOpen ? 'open' : ''}`}
        onClick={() => setMobileOpen(false)}
      />

      {/* Sidebar Navigation */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        activeSessionCount={activeSessionCount}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        theme={theme}
        setTheme={setTheme}
        onOpenStudentPortal={() => setIsStudentCheckInMode(true)}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Mobile Topbar */}
        <div className="mobile-topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => setMobileOpen(true)}
              style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex' }}
            >
              <Menu size={22} />
            </button>
            <div className="brand-badge" style={{ height: '30px', fontSize: '11px' }}>AGEMC</div>
            <span style={{ fontWeight: 700, fontSize: '15px' }}>AGEMC Attend AI</span>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setIsStudentCheckInMode(true)}
              title="Open Student Mobile Portal"
            >
              <Smartphone size={13} />
              <span>Student Mode</span>
            </button>

            {activeSessionCount > 0 && (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  setCurrentTab('active-session');
                }}
              >
                <QrCode size={13} />
                <span>Active QR</span>
              </button>
            )}
          </div>
        </div>

        <main className="main-content">
          {currentTab === 'dashboard' && (
            <DashboardHome
              onNavigate={(tab) => setCurrentTab(tab)}
            />
          )}

          {currentTab === 'sessions' && (
            <SessionsPage
              onSelectSession={handleSelectSession}
            />
          )}

          {currentTab === 'active-session' && (
            <ActiveSessionPage
              sessionId={selectedSessionId}
              onSessionClosed={() => {
                checkActiveSessions();
                setCurrentTab('dashboard');
              }}
            />
          )}

          {currentTab === 'attendance' && (
            <LiveAttendancePage
              initialSessionId={selectedSessionId}
            />
          )}

          {currentTab === 'students' && (
            <StudentDirectoryPage />
          )}

          {currentTab === 'analytics' && (
            <AnalyticsPage />
          )}

          {currentTab === 'security' && (
            <SecurityPanelPage />
          )}

          {currentTab === 'audit' && (
            <AuditLogPage />
          )}

          {currentTab === 'history' && (
            <SessionHistoryPage
              onOpenSession={handleSelectSession}
            />
          )}
        </main>
      </div>
    </div>
  );
}
