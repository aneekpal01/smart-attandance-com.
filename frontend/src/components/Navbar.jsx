import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  CalendarPlus, 
  QrCode, 
  Users, 
  UserCheck,
  TrendingUp, 
  ShieldAlert, 
  FileText, 
  History,
  Clock,
  Sun,
  Moon,
  Smartphone,
  X
} from 'lucide-react';

export default function Navbar({ 
  currentTab, 
  setCurrentTab, 
  activeSessionCount,
  mobileOpen,
  setMobileOpen,
  theme,
  setTheme,
  onOpenStudentPortal
}) {
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'sessions', label: 'Create Session', icon: CalendarPlus },
    { id: 'active-session', label: 'Active Session', icon: QrCode, badge: activeSessionCount > 0 ? 'LIVE' : null },
    { id: 'attendance', label: 'Live Monitor', icon: Users },
    { id: 'students', label: 'Student Directory', icon: UserCheck },
    { id: 'analytics', label: 'AI Analytics & Risk', icon: TrendingUp },
    { id: 'security', label: 'Security & Anti-Proxy', icon: ShieldAlert },
    { id: 'audit', label: 'Audit Log', icon: FileText },
    { id: 'history', label: 'Session History', icon: History },
  ];

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('smartattend_theme', nextTheme);
  };

  return (
    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
      <div className="sidebar-header" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="brand-badge" style={{ fontSize: '11px', letterSpacing: '0.5px' }}>AGEMC</div>
          <div>
            <div className="brand-title">AGEMC Attend AI</div>
            <div className="brand-sub">FACULTY PORTAL</div>
          </div>
        </div>

        {/* Mobile Close Button */}
        {mobileOpen && (
          <button
            onClick={() => setMobileOpen(false)}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        )}
      </div>

      <ul className="nav-links">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <li key={item.id}>
              <button
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setCurrentTab(item.id);
                  if (setMobileOpen) setMobileOpen(false);
                }}
                style={{ width: '100%', background: 'none', textAlign: 'left', border: 'none' }}
              >
                <Icon size={18} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge && (
                  <span className="badge badge-present" style={{ fontSize: '10px', padding: '2px 6px' }}>
                    {item.badge}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="sidebar-footer">
        {/* Day / Night Theme Toggle Button */}
        <button
          className="btn btn-secondary"
          onClick={toggleTheme}
          style={{ width: '100%', justifyContent: 'space-between', padding: '8px 12px', fontSize: '12px', marginBottom: '8px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {theme === 'dark' ? <Moon size={15} style={{ color: 'var(--accent-teal)' }} /> : <Sun size={15} style={{ color: '#f59e0b' }} />}
            <span>{theme === 'dark' ? 'Night Mode' : 'Day Mode'}</span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Toggle</span>
        </button>

        {onOpenStudentPortal && (
          <button
            className="btn btn-secondary"
            onClick={onOpenStudentPortal}
            style={{ width: '100%', justifyContent: 'center', padding: '7px 12px', fontSize: '12px', marginBottom: '12px', color: 'var(--accent-teal)' }}
            title="Open Student Mobile Self Check-In"
          >
            <Smartphone size={14} />
            <span>Student Mobile Portal</span>
          </button>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
          <Clock size={14} />
          <span style={{ fontSize: '13px' }}>{time}</span>
        </div>
      </div>
    </aside>
  );
}
