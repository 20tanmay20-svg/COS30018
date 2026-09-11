import React, { useState } from 'react';
import { Header } from './components/Header';
import { ScanUploadCard } from './components/ScanUploadCard';
import { PatientInfoCard } from './components/PatientInfoCard';
import { EmptyResults } from './components/EmptyResults';
import { DiagnosticResults } from './components/DiagnosticResults';
import { ScanModal } from './components/ScanModal';
import { api } from './services/api';
import { DiagnosticResult, PatientInfo } from './types/diagnostic';

export const App: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State matching Image 1 & 2
  const [patientInfo, setPatientInfo] = useState<PatientInfo>({
    fullName: 'Hayden Janezic',
    dateOfBirth: '27/08/2005',
    biologicalSex: 'Male',
    weightKg: '20',
    scanType: 'MRI Brain',
    contrastAdministered: false,
    presentingSymptoms: 'dizziness',
    clinicalNotes: 'extreme history of migranes',
  });

  const [loading, setLoading] = useState(false);
  const [diagnosticResult, setDiagnosticResult] = useState<DiagnosticResult | null>(null);
  const [showHelpModal, setShowHelpModal] = useState(false);

  const handlePatientInfoChange = (field: keyof PatientInfo, value: any) => {
    setPatientInfo((prev) => ({ ...prev, [field]: value }));
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      // Non-standard image (DICOM / NIfTI) - generate representative preview
      setPreviewUrl('/sample_mri.png');
    }
  };

  const handleClear = () => {
    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setDiagnosticResult(null);
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    try {
      // If no file was uploaded, generate representative default preview to mirror Image 2
      if (!previewUrl) {
        setPreviewUrl('/sample_mri.svg');
      }
      const result = await api.runDiagnosticAnalysis(selectedFile, patientInfo);
      setDiagnosticResult(result);
    } catch (err) {
      console.error('Diagnostic analysis error:', err);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-primary)' }}>
      <Header />

      {/* Main Container */}
      <main
        style={{
          flex: 1,
          maxWidth: '1600px',
          width: '100%',
          margin: '0 auto',
          padding: '1.25rem 1.75rem',
          display: 'grid',
          gridTemplateColumns: '390px 1fr',
          gap: '1.5rem',
          alignItems: 'start',
        }}
      >
        {/* Left Column: Inputs & Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <ScanUploadCard
            selectedFile={selectedFile}
            previewUrl={previewUrl}
            onFileSelect={handleFileSelect}
            onClear={handleClear}
            onViewFull={() => setIsModalOpen(true)}
          />

          <PatientInfoCard
            patientInfo={patientInfo}
            onChange={handlePatientInfoChange}
          />

          {/* Action Button */}
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={loading}
            style={{
              width: '100%',
              backgroundColor: 'var(--accent)',
              color: '#050a12',
              fontWeight: 700,
              fontSize: '0.88rem',
              letterSpacing: '0.02em',
              padding: '0.85rem',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.75 : 1,
            }}
          >
            {loading ? (
              <>
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  style={{ animation: 'spin 1s linear infinite' }}
                >
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" />
                </svg>
                Processing SegResNet & Gemini...
              </>
            ) : (
              'Run Diagnostic Analysis'
            )}
          </button>

          {/* Disclaimer Text */}
          <p
            style={{
              fontSize: '0.62rem',
              lineHeight: '1.4',
              color: 'var(--text-muted)',
              fontFamily: 'monospace',
              letterSpacing: '0.03em',
              textTransform: 'uppercase',
              margin: '0 0.25rem',
            }}
          >
            FOR CLINICAL DECISION SUPPORT ONLY. All output must be reviewed by a qualified physician. Not a substitute for professional medical judgment.
          </p>
        </div>

        {/* Right Column: Diagnostic Results / Empty State */}
        <div style={{ width: '100%', height: '100%' }}>
          {diagnosticResult ? (
            <DiagnosticResults result={diagnosticResult} />
          ) : (
            <EmptyResults />
          )}
        </div>
      </main>

      {/* Floating Help Button (?) */}
      <button
        type="button"
        onClick={() => setShowHelpModal(true)}
        style={{
          position: 'fixed',
          bottom: '18px',
          right: '20px',
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          backgroundColor: '#151f2e',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '0.85rem',
          fontFamily: 'monospace',
          fontWeight: 700,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          zIndex: 50,
        }}
      >
        ?
      </button>

      {/* Help Modal */}
      {showHelpModal && (
        <div
          onClick={() => setShowHelpModal(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '1.5rem',
              maxWidth: '480px',
              width: '90%',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: 'var(--accent)', marginBottom: '0.75rem' }}>
              MedScan AI Diagnostic Workstation
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '1rem' }}>
              This interface is engineered for internal clinical research and diagnostic decision support. It orchestrates:
            </p>
            <ul style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.6, paddingLeft: '1.25rem', marginBottom: '1.25rem' }}>
              <li><strong>MONAI SegResNet:</strong> 3D BraTS multi-parametric tumor segmentation.</li>
              <li><strong>smolagents:</strong> Tool-calling agent for quantitative volumetric queries.</li>
              <li><strong>Google Gemini:</strong> Structured neuroradiology report & RANO differential drafting.</li>
              <li><strong>FastAPI & PostgreSQL:</strong> Async backend and persistent audit log.</li>
            </ul>
            <button
              onClick={() => setShowHelpModal(false)}
              style={{
                width: '100%',
                backgroundColor: 'var(--border)',
                color: '#ffffff',
                padding: '0.5rem',
                borderRadius: '4px',
                fontWeight: 600,
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Full Scan Viewer Modal */}
      <ScanModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        imageUrl={previewUrl}
        fileName={selectedFile?.name || 'ff.jpg'}
      />

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default App;
