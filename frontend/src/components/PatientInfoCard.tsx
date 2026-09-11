import React from 'react';
import { PatientInfo } from '../types/diagnostic';

interface PatientInfoCardProps {
  patientInfo: PatientInfo;
  onChange: (field: keyof PatientInfo, value: any) => void;
}

export const PatientInfoCard: React.FC<PatientInfoCardProps> = ({
  patientInfo,
  onChange,
}) => {
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
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '0.85rem',
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
          PATIENT INFORMATION
        </span>
        <span
          style={{
            fontSize: '0.58rem',
            fontFamily: 'monospace',
            letterSpacing: '0.06em',
            color: 'var(--text-muted)',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border)',
            padding: '1px 5px',
            borderRadius: '3px',
          }}
        >
          OPTIONAL
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* Name & DOB */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
          <div>
            <label className="field-label">FULL NAME</label>
            <input
              type="text"
              placeholder="Jane Doe"
              value={patientInfo.fullName}
              onChange={(e) => onChange('fullName', e.target.value)}
              className="dark-input"
            />
          </div>
          <div>
            <label className="field-label">DATE OF BIRTH</label>
            <input
              type="text"
              placeholder="dd/mm/yyyy"
              value={patientInfo.dateOfBirth}
              onChange={(e) => onChange('dateOfBirth', e.target.value)}
              className="dark-input"
            />
          </div>
        </div>

        {/* Sex & Weight */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
          <div>
            <label className="field-label">BIOLOGICAL SEX</label>
            <select
              value={patientInfo.biologicalSex}
              onChange={(e) => onChange('biologicalSex', e.target.value)}
              className="dark-input"
            >
              <option value="">— Select —</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label className="field-label">WEIGHT (KG)</label>
            <input
              type="number"
              placeholder="70"
              value={patientInfo.weightKg}
              onChange={(e) => onChange('weightKg', e.target.value)}
              className="dark-input"
            />
          </div>
        </div>

        {/* Scan Type */}
        <div>
          <label className="field-label">SCAN TYPE</label>
          <select
            value={patientInfo.scanType}
            onChange={(e) => onChange('scanType', e.target.value)}
            className="dark-input"
          >
            <option value="MRI Brain">MRI Brain</option>
            <option value="MRI Spine">MRI Spine</option>
            <option value="CT Head">CT Head</option>
          </select>
        </div>

        {/* Contrast Checkbox */}
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <input
            type="checkbox"
            checked={patientInfo.contrastAdministered}
            onChange={(e) => onChange('contrastAdministered', e.target.checked)}
            style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
          />
          Contrast agent administered
        </label>

        {/* Presenting Symptoms */}
        <div>
          <label className="field-label">PRESENTING SYMPTOMS</label>
          <textarea
            rows={2}
            placeholder="e.g. progressive headache x3 weeks, visual disturbances, nausea"
            value={patientInfo.presentingSymptoms}
            onChange={(e) => onChange('presentingSymptoms', e.target.value)}
            className="dark-input"
            style={{ resize: 'none' }}
          />
        </div>

        {/* Clinical Notes / History */}
        <div>
          <label className="field-label">CLINICAL NOTES / HISTORY</label>
          <textarea
            rows={2}
            placeholder="Relevant PMH, medications, allergies..."
            value={patientInfo.clinicalNotes}
            onChange={(e) => onChange('clinicalNotes', e.target.value)}
            className="dark-input"
            style={{ resize: 'none' }}
          />
        </div>
      </div>
    </div>
  );
};
