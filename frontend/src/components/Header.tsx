import React from 'react';

export const Header: React.FC = () => {
  const currentDate = new Date().toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.85rem 1.75rem',
        borderBottom: '1px solid var(--border)',
        backgroundColor: 'var(--bg-header)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            border: '1.5px solid var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 229, 255, 0.08)',
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            <path d="M2 12h20" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '0.02em', color: '#ffffff' }}>
            MedScan AI
          </div>
          <div
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              fontFamily: 'monospace',
              marginTop: '1px',
            }}
          >
            DIAGNOSTIC IMAGING ANALYSIS SYSTEM v2.4
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            fontSize: '0.72rem',
            fontFamily: 'monospace',
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: 'var(--status-green)',
              boxShadow: '0 0 8px var(--status-green)',
            }}
          />
          <span style={{ color: 'var(--status-green)', fontWeight: 600 }}>MODEL ONLINE</span>
        </div>
        <div
          style={{
            fontSize: '0.75rem',
            fontFamily: 'monospace',
            color: 'var(--text-secondary)',
          }}
        >
          {currentDate}
        </div>
      </div>
    </header>
  );
};
