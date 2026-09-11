import React from 'react';

interface ScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string | null;
  fileName?: string;
}

export const ScanModal: React.FC<ScanModalProps> = ({
  isOpen,
  onClose,
  imageUrl,
  fileName,
}) => {
  if (!isOpen || !imageUrl) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          maxWidth: '90vw',
          maxHeight: '90vh',
          backgroundColor: '#050b14',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '0.75rem',
            paddingBottom: '0.5rem',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {fileName || 'Scan Viewer (Axial Slice)'}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: '1.2rem',
              lineHeight: 1,
              padding: '2px 8px',
            }}
          >
            &times;
          </button>
        </div>

        <img
          src={imageUrl}
          alt="Full Scan"
          style={{
            maxWidth: '80vw',
            maxHeight: '75vh',
            objectFit: 'contain',
            borderRadius: '4px',
          }}
        />
      </div>
    </div>
  );
};
