import React, { useState } from 'react';
import { Scan } from '../services/api';

interface ScanListProps {
  scans: Scan[];
  selectedScan: Scan | null;
  onSelectScan: (scan: Scan) => void;
  onRunSegmentation: (scanId: number) => Promise<void>;
  onCreateScan: (patientId: string) => Promise<void>;
}

export const ScanList: React.FC<ScanListProps> = ({
  scans,
  selectedScan,
  onSelectScan,
  onRunSegmentation,
  onCreateScan,
}) => {
  const [patientId, setPatientId] = useState('');
  const [loadingId, setLoadingId] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId.trim()) return;
    await onCreateScan(patientId);
    setPatientId('');
  };

  const handleSeg = async (scanId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setLoadingId(scanId);
    try {
      await onRunSegmentation(scanId);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div style={{ background: 'var(--bg-card)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
      <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--accent)' }}>MRI Scans (BraTS)</h2>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="Patient ID (e.g. BraTS-GLI-001)"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" style={{ background: 'var(--accent)', color: '#0f172a', padding: '0.5rem 1rem' }}>
          Add Scan
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {scans.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No scans available. Add one above to begin.</p>
        ) : (
          scans.map((scan) => {
            const isSelected = selectedScan?.id === scan.id;
            return (
              <div
                key={scan.id}
                onClick={() => onSelectScan(scan)}
                style={{
                  padding: '0.75rem',
                  borderRadius: '6px',
                  border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
                  background: isSelected ? 'var(--bg-hover)' : 'var(--bg-primary)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{scan.patient_id}</strong>
                  <span style={{ fontSize: '0.8rem', color: scan.status === 'completed' ? 'var(--success)' : 'var(--warning)' }}>
                    {scan.status.toUpperCase()}
                  </span>
                </div>

                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {scan.wt_volume_cm3 !== null && scan.wt_volume_cm3 !== undefined ? (
                    <div>
                      WT: {scan.wt_volume_cm3.toFixed(1)} cm³ | TC: {scan.tc_volume_cm3?.toFixed(1)} cm³ | ET: {scan.et_volume_cm3?.toFixed(1)} cm³
                    </div>
                  ) : (
                    <span>Not segmented yet</span>
                  )}
                </div>

                {scan.status !== 'completed' && (
                  <button
                    onClick={(e) => handleSeg(scan.id, e)}
                    disabled={loadingId === scan.id}
                    style={{
                      marginTop: '0.5rem',
                      width: '100%',
                      background: 'var(--bg-hover)',
                      color: 'var(--text-primary)',
                      padding: '0.35rem 0.5rem',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {loadingId === scan.id ? 'Running MONAI SegResNet...' : 'Run MONAI SegResNet'}
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
