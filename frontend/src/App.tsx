import React, { useEffect, useState } from 'react';
import { api, Scan } from './services/api';
import { ScanList } from './components/ScanList';
import { ReportViewer } from './components/ReportViewer';
import { AgentChat } from './components/AgentChat';

export const App: React.FC = () => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);

  const loadScans = async () => {
    try {
      const data = await api.getScans();
      setScans(data);
      if (data.length > 0 && !selectedScan) {
        setSelectedScan(data[0]);
      }
    } catch (err) {
      console.error('Could not load scans:', err);
    }
  };

  useEffect(() => {
    loadScans();
  }, []);

  const handleCreateScan = async (patientId: string) => {
    try {
      const newScan = await api.createScan(patientId);
      setScans((prev) => [newScan, ...prev]);
      setSelectedScan(newScan);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunSegmentation = async (scanId: number) => {
    try {
      const res = await api.runSegmentation(scanId);
      setScans((prev) =>
        prev.map((s) => (s.id === scanId ? { ...s, ...res, status: 'completed' } : s))
      );
      if (selectedScan?.id === scanId) {
        setSelectedScan((prev) => (prev ? { ...prev, ...res, status: 'completed' } : null));
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1.5rem' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          COS30018 Intelligent Systems Platform
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', fontSize: '0.95rem' }}>
          MONAI SegResNet (BraTS) &bull; smolagents &bull; Gemini Clinical Reporting &bull; FastAPI &bull; PostgreSQL
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.5rem' }}>
        <div>
          <ScanList
            scans={scans}
            selectedScan={selectedScan}
            onSelectScan={setSelectedScan}
            onRunSegmentation={handleRunSegmentation}
            onCreateScan={handleCreateScan}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <ReportViewer selectedScan={selectedScan} />
          <AgentChat selectedScan={selectedScan} />
        </div>
      </div>
    </div>
  );
};

export default App;
