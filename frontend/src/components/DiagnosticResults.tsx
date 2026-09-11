import React, { useState } from 'react';
import { DiagnosticResult } from '../types/diagnostic';

interface DiagnosticResultsProps {
  result: DiagnosticResult;
}

export const DiagnosticResults: React.FC<DiagnosticResultsProps> = ({ result }) => {
  const [activeTab, setActiveTab] = useState<'findings' | 'treatment'>('findings');
  const { primaryDiagnosis, imagingFindings, differentialDiagnoses, clinicalNotes, treatmentProtocol } = result;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      {/* Primary Diagnosis Header Card */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div
              style={{
                fontSize: '0.65rem',
                fontFamily: 'monospace',
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                marginBottom: '0.35rem',
              }}
            >
              PRIMARY DIAGNOSIS
            </div>
            <h2
              style={{
                fontSize: '1.45rem',
                fontWeight: 700,
                color: '#ffffff',
                letterSpacing: '0.01em',
                marginBottom: '0.5rem',
              }}
            >
              {primaryDiagnosis.title}
            </h2>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontFamily: 'monospace',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: 'var(--text-secondary)',
                  padding: '2px 7px',
                  borderRadius: '3px',
                  fontWeight: 600,
                }}
              >
                {primaryDiagnosis.icdCode}
              </span>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontFamily: 'monospace',
                  backgroundColor: 'var(--badge-critical)',
                  color: '#ffffff',
                  padding: '2px 7px',
                  borderRadius: '3px',
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                }}
              >
                {primaryDiagnosis.severity}
              </span>
            </div>
          </div>

          {/* AI Confidence */}
          <div style={{ textAlign: 'right', minWidth: '180px' }}>
            <div
              style={{
                fontSize: '0.65rem',
                fontFamily: 'monospace',
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                marginBottom: '0.45rem',
              }}
            >
              AI CONFIDENCE
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <div
                style={{
                  width: '120px',
                  height: '5px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${primaryDiagnosis.confidence}%`,
                    height: '100%',
                    backgroundColor: 'var(--accent-glow)',
                    borderRadius: '3px',
                  }}
                />
              </div>
              <span
                style={{
                  fontSize: '0.9rem',
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  color: 'var(--accent-glow)',
                }}
              >
                {primaryDiagnosis.confidence}%
              </span>
            </div>
          </div>
        </div>

        {/* Patient & Processing Metadata Strip */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1.75rem',
            marginTop: '1.25rem',
            paddingTop: '0.85rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            fontSize: '0.68rem',
            fontFamily: 'monospace',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            <span style={{ color: 'var(--text-muted)' }}>PT: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{primaryDiagnosis.patientName}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>DOB: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{primaryDiagnosis.dateOfBirth}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>SCAN: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{primaryDiagnosis.scanType}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>PROCESSED: </span>
            <span style={{ color: 'var(--text-secondary)' }}>{primaryDiagnosis.processedTime}</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
          gap: '1.5rem',
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('findings')}
          style={{
            background: 'transparent',
            color: activeTab === 'findings' ? 'var(--accent)' : 'var(--text-muted)',
            fontSize: '0.78rem',
            fontFamily: 'monospace',
            letterSpacing: '0.08em',
            fontWeight: 600,
            padding: '0.6rem 0',
            borderBottom: activeTab === 'findings' ? '2px solid var(--accent)' : '2px solid transparent',
            borderRadius: 0,
          }}
        >
          IMAGING FINDINGS & DIFFERENTIALS
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('treatment')}
          style={{
            background: 'transparent',
            color: activeTab === 'treatment' ? 'var(--accent)' : 'var(--text-muted)',
            fontSize: '0.78rem',
            fontFamily: 'monospace',
            letterSpacing: '0.08em',
            fontWeight: 600,
            padding: '0.6rem 0',
            borderBottom: activeTab === 'treatment' ? '2px solid var(--accent)' : '2px solid transparent',
            borderRadius: 0,
          }}
        >
          TREATMENT PROTOCOL
        </button>
      </div>

      {/* Tab 1: Findings & Differentials */}
      {activeTab === 'findings' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Subcard 1: Imaging Findings */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '1.15rem 1.25rem',
            }}
          >
            <div
              style={{
                fontSize: '0.68rem',
                fontFamily: 'monospace',
                letterSpacing: '0.1em',
                color: 'var(--text-muted)',
                marginBottom: '0.85rem',
                fontWeight: 600,
              }}
            >
              IMAGING FINDINGS
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {imagingFindings.map((finding) => (
                <div key={finding.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontFamily: 'monospace',
                      color: 'var(--accent)',
                      backgroundColor: 'rgba(0, 229, 255, 0.08)',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      minWidth: '22px',
                      textAlign: 'center',
                      marginTop: '2px',
                    }}
                  >
                    {finding.id}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                    {finding.text}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Subcard 2: Differential Diagnoses */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '1.15rem 1.25rem',
            }}
          >
            <div
              style={{
                fontSize: '0.68rem',
                fontFamily: 'monospace',
                letterSpacing: '0.1em',
                color: 'var(--text-muted)',
                marginBottom: '0.85rem',
                fontWeight: 600,
              }}
            >
              DIFFERENTIAL DIAGNOSES
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {differentialDiagnoses.map((diff, index) => (
                <div key={index}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.82rem',
                      color: diff.isPrimary ? '#ffffff' : 'var(--text-secondary)',
                      fontWeight: diff.isPrimary ? 600 : 400,
                      marginBottom: '0.35rem',
                    }}
                  >
                    <span>{diff.name}</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: diff.isPrimary ? 'var(--accent)' : 'var(--text-muted)' }}>
                      {diff.probability}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: '4px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${diff.probability}%`,
                        height: '100%',
                        backgroundColor: diff.isPrimary ? 'var(--accent)' : 'rgba(255, 255, 255, 0.2)',
                        borderRadius: '2px',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Subcard 3: Clinical Notes */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-amber)',
              borderRadius: '6px',
              padding: '1.15rem 1.25rem',
            }}
          >
            <div
              style={{
                fontSize: '0.68rem',
                fontFamily: 'monospace',
                letterSpacing: '0.1em',
                color: 'var(--accent-amber)',
                marginBottom: '0.65rem',
                fontWeight: 700,
              }}
            >
              CLINICAL NOTES
            </div>
            <p
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {clinicalNotes}
            </p>
          </div>
        </div>
      )}

      {/* Tab 2: Treatment Protocol */}
      {activeTab === 'treatment' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {treatmentProtocol.map((section, idx) => (
            <div
              key={idx}
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                padding: '1.15rem 1.25rem',
              }}
            >
              <div
                style={{
                  fontSize: '0.78rem',
                  fontFamily: 'monospace',
                  letterSpacing: '0.08em',
                  color: 'var(--accent)',
                  marginBottom: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {section.title.toUpperCase()}
              </div>
              <ul style={{ paddingLeft: '1.25rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {section.details.map((detail, dIdx) => (
                  <li key={dIdx} style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {detail}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
