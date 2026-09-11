import React, { useRef, useState } from 'react';

interface ScanUploadCardProps {
  selectedFile: File | null;
  previewUrl: string | null;
  onFileSelect: (file: File) => void;
  onClear: () => void;
  onViewFull?: () => void;
}

export const ScanUploadCard: React.FC<ScanUploadCardProps> = ({
  selectedFile,
  previewUrl,
  onFileSelect,
  onClear,
  onViewFull,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        padding: '0.85rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.65rem',
        }}
      >
        <span
          style={{
            fontSize: '0.68rem',
            fontFamily: 'monospace',
            letterSpacing: '0.1em',
            color: 'var(--text-muted)',
            fontWeight: 600,
          }}
        >
          SCAN UPLOAD
        </span>
        {selectedFile && (
          <button
            type="button"
            onClick={onClear}
            style={{
              background: 'transparent',
              color: 'var(--accent)',
              fontSize: '0.68rem',
              fontFamily: 'monospace',
              letterSpacing: '0.08em',
              fontWeight: 600,
              padding: '2px 6px',
            }}
          >
            CLEAR
          </button>
        )}
      </div>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
        accept=".dcm,.nii,.nii.gz,.png,.jpg,.jpeg,image/*"
      />

      {previewUrl ? (
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '240px',
            borderRadius: '4px',
            overflow: 'hidden',
            backgroundColor: '#000000',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <img
            src={previewUrl}
            alt="MRI Scan Preview"
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              display: 'block',
            }}
          />

          {/* Bottom Info Overlay */}
          <div
            style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              backgroundColor: 'rgba(5, 10, 18, 0.85)',
              padding: '3px 8px',
              borderRadius: '3px',
              fontSize: '0.65rem',
              fontFamily: 'monospace',
              color: 'var(--text-secondary)',
              border: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              gap: '6px',
            }}
          >
            <span style={{ color: '#ffffff' }}>{selectedFile?.name || 'ff.jpg'}</span>
            <span>{selectedFile ? formatFileSize(selectedFile.size) : '41 KB'}</span>
          </div>

          {/* View Full Button */}
          <button
            type="button"
            onClick={onViewFull}
            style={{
              position: 'absolute',
              bottom: '8px',
              right: '8px',
              backgroundColor: 'var(--accent)',
              color: '#050b14',
              padding: '3px 8px',
              borderRadius: '3px',
              fontSize: '0.65rem',
              fontFamily: 'monospace',
              fontWeight: 700,
              letterSpacing: '0.05em',
            }}
          >
            VIEW FULL
          </button>
        </div>
      ) : (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            height: '180px',
            border: `1.5px dashed ${isDragging ? 'var(--accent)' : 'rgba(255, 255, 255, 0.12)'}`,
            borderRadius: '4px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            backgroundColor: isDragging ? 'rgba(0, 229, 255, 0.03)' : 'transparent',
            transition: 'all 0.2s ease',
            padding: '1rem',
          }}
        >
          <div style={{ color: 'var(--accent)', marginBottom: '0.75rem', opacity: 0.85 }}>
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 500, marginBottom: '0.35rem' }}>
            Drop scan or click to browse
          </div>
          <div
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.1em',
              fontFamily: 'monospace',
            }}
          >
            DICOM &bull; NIFTI &bull; PNG &bull; JPG &bull; DCM
          </div>
        </div>
      )}
    </div>
  );
};
