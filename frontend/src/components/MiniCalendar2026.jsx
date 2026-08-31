import React, { useState } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';

export default function MiniCalendar2026() {
  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth()); // 0-11
  const year = 2026;

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const daysOfWeek = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

  // Days in selected month for 2026
  const daysInMonth = new Date(year, currentMonth + 1, 0).getDate();
  const firstDayIndex = new Date(year, currentMonth, 1).getDay();

  const prevMonth = () => {
    setCurrentMonth((prev) => (prev === 0 ? 11 : prev - 1));
  };

  const nextMonth = () => {
    setCurrentMonth((prev) => (prev === 11 ? 0 : prev + 1));
  };

  // Check if a day is today
  const isToday = (day) => {
    return (
      today.getFullYear() === year &&
      today.getMonth() === currentMonth &&
      today.getDate() === day
    );
  };

  const blanks = Array.from({ length: firstDayIndex }, (_, i) => i);
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  return (
    <div className="card" style={{ padding: '16px 18px', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      {/* Calendar Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={16} style={{ color: 'var(--accent-teal)' }} />
          <span style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-primary)' }}>
            {monthNames[currentMonth]} {year}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={prevMonth}
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 6px', height: '24px' }}
            title="Previous Month"
          >
            <ChevronLeft size={12} />
          </button>
          <button
            onClick={nextMonth}
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 6px', height: '24px' }}
            title="Next Month"
          >
            <ChevronRight size={12} />
          </button>
        </div>
      </div>

      {/* Weekday Labels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', textAlign: 'center', gap: '2px', marginBottom: '4px' }}>
        {daysOfWeek.map((d, i) => (
          <div key={i} style={{ fontSize: '11px', fontWeight: 700, color: i === 0 ? 'var(--status-absent)' : 'var(--text-muted)' }}>
            {d}
          </div>
        ))}
      </div>

      {/* Day Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center' }}>
        {blanks.map((b) => (
          <div key={`b-${b}`} style={{ height: '26px' }} />
        ))}
        {days.map((d) => {
          const active = isToday(d);
          return (
            <div
              key={d}
              style={{
                height: '26px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: active ? 800 : 500,
                borderRadius: '6px',
                background: active ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-cyan))' : 'transparent',
                color: active ? '#042f2e' : 'var(--text-primary)',
                boxShadow: active ? '0 0 10px rgba(20, 184, 166, 0.5)' : 'none',
                cursor: 'default',
                transition: 'all 0.2s ease'
              }}
            >
              {d}
            </div>
          );
        })}
      </div>

      {/* Academic Semester Badge */}
      <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
        <span>AGEMC Academic 2026</span>
        <span className="badge badge-present" style={{ fontSize: '10px', padding: '2px 6px' }}>Semester Active</span>
      </div>
    </div>
  );
}
