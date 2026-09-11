import React from 'react';

export const EmptyResults: React.FC = () => {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        minHeight: '480px',
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 2rem',
      }}
    >
      <div
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          marginBottom: '1.25rem',
          opacity: 0.6,
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>

      <div
        style={{
          fontSize: '1.05rem',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '0.4rem',
        }}
      >
        Upload a scan and run analysis
      </div>

      <div
        style={{
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          fontFamily: 'monospace',
          letterSpacing: '0.04em',
        }}
      >
        Diagnosis and treatment plan will appear here
      </div>
    </div>
  );
};
