import React, { useState } from 'react';
import { Scan, Report, api } from '../services/api';

interface ReportViewerProps {
  selectedScan: Scan | null;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({ selectedScan }) => {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [clinicalHistory, setClinicalHistory] = useState('');

  const handleGenerate = async () => {
    if (!selectedScan) return;
    setLoading(true);
    try {
      const rep = await api.generateReport(selectedScan.id, clinicalHistory);
      setReport(rep);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedScan) {
    return (
      <div style={{ background: 'var(--bg-card)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', color: 'var(--accent)' }}>Gemini Clinical Report</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Select an MRI scan from the left panel to generate or view a report.</p>
      </div>
    );
  }

  return (
    <div style={{ background: 'var(--bg-card)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
      <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--accent)' }}>
        Gemini Clinical Report (Patient: {selectedScan.patient_id})
      </h2>

      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
          Clinical Context / History
        </label>
        <textarea
          rows={2}
          value={clinicalHistory}
          onChange={(e) => setClinicalHistory(e.target.value)}
          placeholder="e.g. 54 yo male presenting with progressive headache and sensory changes..."
          style={{ width: '100%', resize: 'vertical' }}
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          background: 'var(--accent)',
          color: '#0f172a',
          padding: '0.5rem 1rem',
          width: '100%',
          marginBottom: '1rem',
        }}
      >
        {loading ? 'Generating with Gemini...' : 'Generate Radiology Report'}
      </button>

      {report && (
        <div style={{ background: 'var(--bg-primary)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: '1rem', color: 'var(--accent)', marginBottom: '0.5rem' }}>Findings</h3>
          <p style={{ fontSize: '0.9rem', lineHeight: '1.5', whiteSpace: 'pre-line', marginBottom: '1rem' }}>
            {report.findings}
          </p>

          <h3 style={{ fontSize: '1rem', color: 'var(--accent)', marginBottom: '0.5rem' }}>Impression</h3>
          <p style={{ fontSize: '0.9rem', lineHeight: '1.5', marginBottom: '1rem' }}>
            {report.impression}
          </p>

          {report.recommendations && (
            <>
              <h3 style={{ fontSize: '1rem', color: 'var(--accent)', marginBottom: '0.5rem' }}>Recommendations</h3>
              <p style={{ fontSize: '0.9rem', lineHeight: '1.5' }}>
                {report.recommendations}
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
};
