import React, { useState } from 'react';

interface PatientInput {
  Patient_ID: string;
  'Sex at Birth': string;
  'Age at diagnosis': string;
  'Primary Diagnosis': string;
  'Grade of Primary Brain Tumor': string;
  Progression: string;
  'Time to First Progression (Days)': string | null;
  'Overall Survival (Death)': string;
}

interface SharedState {
  user_request?: string;
  patient_information?: {
    request_type: string;
    requested_task: string;
    data_source: string;
    status: string;
    error: string | null;
    patient_data: PatientInput[];
  };
  medical_evidence?: {
    status: string;
    search_attempts: number;
    search_queries: string[];
    retrieved_evidence: string[];
    evidence_relevance: string[];
    error: string | null;
  };
  clinical_decision_support?: {
    status: string;
    clinical_considerations: string[];
    treatment_pathways: string[];
    verification_status?: string;
  };
  final_report?: {
    patient_summary: string;
    findings: string;
    impression: string;
    treatment_plan: string;
    recommendations: string;
  };
}

const DEFAULT_NEW_PATIENT: PatientInput = {
  Patient_ID: '',
  'Sex at Birth': 'Male',
  'Age at diagnosis': '65',
  'Primary Diagnosis': 'GBM',
  'Grade of Primary Brain Tumor': '4',
  Progression: '0',
  'Time to First Progression (Days)': null,
  'Overall Survival (Death)': '0',
};

export default function App() {
  const [promptInput, setPromptInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sharedState, setSharedState] = useState<SharedState | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newPatientForm, setNewPatientForm] = useState<PatientInput>(DEFAULT_NEW_PATIENT);

  const resolvePatientRecord = (queryText: string): PatientInput => {
    const numMatch = queryText.match(/patient\s*#?(\d+)/i);
    const idMatch = queryText.match(/patientid[_-]?(\d+)/i);
    let resolvedId = 'PatientID_0007';

    if (numMatch) {
      resolvedId = `PatientID_${numMatch[1].padStart(4, '0')}`;
    } else if (idMatch) {
      resolvedId = `PatientID_${idMatch[1].padStart(4, '0')}`;
    }

    return {
      Patient_ID: resolvedId,
      'Sex at Birth': 'Male',
      'Age at diagnosis': '79',
      'Primary Diagnosis': 'GBM',
      'Grade of Primary Brain Tumor': '4',
      Progression: '0',
      'Time to First Progression (Days)': null,
      'Overall Survival (Death)': '1',
    };
  };

  const executePipeline = (query: string, patientData: PatientInput, source: string, reqType: string) => {
    setLoading(true);

    setTimeout(() => {
      const mockResult: SharedState = {
        user_request: query,
        patient_information: {
          request_type: reqType,
          requested_task: 'generate_report',
          data_source: source,
          status: 'success',
          error: null,
          patient_data: [patientData],
        },
        medical_evidence: {
          status: 'verified',
          search_attempts: 2,
          search_queries: [
            `${patientData['Primary Diagnosis']} Grade ${patientData['Grade of Primary Brain Tumor']} elderly protocol`,
            `Hypofractionated radiation and temozolomide tolerance at age ${patientData['Age at diagnosis']}`,
          ],
          retrieved_evidence: [
            'Hypofractionated radiotherapy (40 Gy in 15 fractions) combined with temozolomide demonstrates improved survival in elderly GBM patients over 70 years.',
            'Molecular biomarker profiling (MGMT promoter methylation) is critical to determine alkylating chemotherapy efficacy.',
          ],
          evidence_relevance: ['97%', '94%'],
          error: null,
        },
        clinical_decision_support: {
          status: 'verified',
          verification_status: 'Approved by Verification Agent',
          clinical_considerations: [
            `Patient age (${patientData['Age at diagnosis']}) warrants hypofractionated dosing to mitigate neurological toxicity.`,
            patientData.Progression === '1'
              ? 'Documented recurrence requires salvage or secondary line evaluation.'
              : 'Primary baseline intervention indicated.',
          ],
          treatment_pathways: [
            'Primary: Target-dosed hypofractionated radiotherapy (40 Gy / 15 fx) with adjuvant Temozolomide.',
            'Supportive: Early integration of palliative oncology and functional assessment.',
          ],
        },
        final_report: {
          patient_summary: `${patientData.Patient_ID} • ${patientData['Sex at Birth']} • Age ${patientData['Age at diagnosis']}`,
          findings: `Clinical records confirm a high-grade primary glial neoplasm (${patientData['Primary Diagnosis']}, Grade ${patientData['Grade of Primary Brain Tumor']}). Prior clinical progression: ${
            patientData.Progression === '0' ? 'None documented' : 'Confirmed progression'
          }.`,
          impression: `High-grade primary neoplasm requiring evidence-grounded dosing adjustments to preserve performance status.`,
          treatment_plan: `1. Multidisciplinary Neuro-Oncology formal review.\n2. Initiate targeted hypofractionated radiotherapy (40 Gy over 15 fractions).\n3. Concurrent Temozolomide therapy conditional upon MGMT promoter methylation profiling.`,
          recommendations: 'Order MGMT promoter methylation sequencing and IDH mutation screening to establish chemotherapeutic responsiveness.',
        },
      };

      setSharedState(mockResult);
      setLoading(false);
    }, 650);
  };

  const handlePromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptInput.trim() || loading) return;
    const targetPatient = resolvePatientRecord(promptInput);
    executePipeline(promptInput, targetPatient, 'gbm_patient_profiles.json', 'individual_patient');
  };

  const handleCreatePatientSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const pid = newPatientForm.Patient_ID.trim() || `PatientID_${Math.floor(1000 + Math.random() * 9000)}`;
    const createdRecord: PatientInput = { ...newPatientForm, Patient_ID: pid };

    setIsModalOpen(false);
    setPromptInput(`generate report for ${pid}`);
    executePipeline(`generate report for ${pid}`, createdRecord, 'manual_intake_buffer', 'new_patient_intake');
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    boxSizing: 'border-box',
    background: '#090e1f',
    border: '1px solid #334155',
    color: '#f8fafc',
    padding: '9px 12px',
    borderRadius: '6px',
    fontSize: '13px',
    outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.04em',
    color: '#94a3b8',
    textTransform: 'uppercase',
    marginBottom: '6px',
  };

  return (
    <div style={{ minHeight: '100vh', background: '#080d1a', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Enterprise Header */}
      <header style={{ borderBottom: '1px solid #1e293b', background: '#0b1329', padding: '14px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#38bdf8', boxShadow: '0 0 10px #38bdf8' }} />
          <span style={{ fontWeight: 700, letterSpacing: '0.04em', fontSize: '14px', color: '#f8fafc' }}>
            CLINICAL DECISION SUPPORT PLATFORM
          </span>
          <span style={{ fontSize: '11px', background: '#1e293b', color: '#94a3b8', padding: '2px 8px', borderRadius: '4px', border: '1px solid #334155' }}>
            PROMPT PIPELINE
          </span>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              background: '#0284c7',
              border: 'none',
              color: '#ffffff',
              padding: '7px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>+</span> Add New Patient
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main style={{ maxWidth: '1180px', margin: '0 auto', padding: '32px 24px' }}>
        
        {/* Headings */}
        <section style={{ maxWidth: '820px', margin: '0 auto 36px auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '22px' }}>
            <h1 style={{ fontSize: '26px', fontWeight: 700, color: '#f8fafc', margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
              Multi-Agent Clinical Diagnostic Console
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
              Issue prompt instructions to generate an example report.
            </p>
          </div>

          <form onSubmit={handlePromptSubmit}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '6px 8px 6px 16px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
              }}
            >
              <input
                type="text"
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                placeholder="e.g. make me a report for patient 7"
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  color: '#f8fafc',
                  fontSize: '14px',
                  outline: 'none',
                }}
              />
              <button
                type="submit"
                disabled={loading}
                style={{
                  background: loading ? '#0369a1' : '#0284c7',
                  border: 'none',
                  color: '#ffffff',
                  fontWeight: 600,
                  padding: '10px 20px',
                  borderRadius: '6px',
                  cursor: loading ? 'default' : 'pointer',
                  fontSize: '13px',
                }}
              >
                {loading ? 'Executing Pipeline...' : 'Generate Report'}
              </button>
            </div>
          </form>

          {/* List of example prompts */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', justifyContent: 'center' }}>
            <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>QUICK RUNS:</span>
            {[
              'make me a report for patient 7',
              'evaluate PatientID_0012 for treatment plan',
              'generate clinical report for PatientID_0007',
            ].map((suggested, idx) => (
              <button
                key={idx}
                onClick={() => setPromptInput(suggested)}
                style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  color: '#94a3b8',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                {suggested}
              </button>
            ))}
          </div>
        </section>

        {/* Example Report (Ai generated for example) (This is hard coded but needs to become fluid with the backend) */}
        {sharedState && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Multi-Agent Node Status Trackers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
              
              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 600, color: '#64748b' }}>NODE 01</span>
                  <span style={{ fontSize: '10px', color: '#4ade80', fontWeight: 600 }}>SYNCHRONIZED</span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>Patient Profile Intake</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                  {sharedState.patient_information?.patient_data[0].Patient_ID} &bull; {sharedState.patient_information?.data_source}[cite: 7]
                </div>
              </div>

              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 600, color: '#64748b' }}>NODE 02</span>
                  <span style={{ fontSize: '10px', color: '#4ade80', fontWeight: 600 }}>SYNCHRONIZED</span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>Evidence Synthesis</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                  {sharedState.medical_evidence?.search_attempts} Queries Evaluated &bull; PubMed Indexed[cite: 7, 8]
                </div>
              </div>

              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 600, color: '#64748b' }}>NODE 03 & 04</span>
                  <span style={{ fontSize: '10px', color: '#4ade80', fontWeight: 600 }}>VERIFIED</span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>Clinical Protocol & Verification</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                  Protocol Approved[cite: 8]
                </div>
              </div>

            </div>

            {/* Generated Clinical Report Card */}
            {sharedState.final_report && (
              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', background: '#111c38', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em', color: '#94a3b8', textTransform: 'uppercase' }}>
                    Structured Draft Radiology & Decision Report[cite: 8]
                  </span>
                  <span style={{ fontSize: '11px', background: '#064e3b', color: '#6ee7b7', border: '1px solid #059669', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    VERIFIED DRAFT
                  </span>
                </div>

                <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  
                  {/* Summary Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '14px', borderBottom: '1px solid #1e293b' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase' }}>Active Patient Record</div>
                      <div style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>
                        {sharedState.final_report.patient_summary}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase' }}>Prompt Origin</div>
                      <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px' }}>
                        "{sharedState.user_request}"[cite: 7]
                      </div>
                    </div>
                  </div>

                  {/* Findings */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#38bdf8', margin: '0 0 6px 0' }}>
                      Clinical Findings[cite: 8]
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
                      {sharedState.final_report.findings}
                    </p>
                  </div>

                  {/* Impression */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#38bdf8', margin: '0 0 6px 0' }}>
                      Clinical Impression[cite: 8]
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
                      {sharedState.final_report.impression}
                    </p>
                  </div>

                  {/* Verified Treatment Strategy */}
                  <div style={{ background: '#071226', border: '1px solid #1e3a8a', padding: '16px', borderRadius: '6px' }}>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#60a5fa', margin: '0 0 8px 0' }}>
                      Verified Treatment Plan[cite: 8]
                    </h4>
                    <div style={{ fontSize: '13px', lineHeight: '1.7', color: '#e2e8f0', whiteSpace: 'pre-line' }}>
                      {sharedState.final_report.treatment_plan}
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', margin: '0 0 6px 0' }}>
                      Recommendations[cite: 8]
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#94a3b8' }}>
                      {sharedState.final_report.recommendations}
                    </p>
                  </div>

                </div>
              </div>
            )}

          </section>
        )}

      </main>

      {/* Form to add new patient*/}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(3, 7, 18, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '16px',
          }}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              width: '100%',
              maxWidth: '520px',
              overflow: 'hidden',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid #1e293b',
                background: '#111c38',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>
                Register New Patient Record
              </h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '16px' }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreatePatientSubmit} style={{ padding: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={labelStyle}>Patient Identifier[cite: 7]</label>
                  <input
                    type="text"
                    placeholder="e.g. PatientID_0099"
                    value={newPatientForm.Patient_ID}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, Patient_ID: e.target.value })}
                    style={inputStyle}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={labelStyle}>Diagnosis[cite: 7]</label>
                    <input
                      type="text"
                      value={newPatientForm['Primary Diagnosis']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Primary Diagnosis': e.target.value })}
                      style={inputStyle}
                      required
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>WHO Grade[cite: 7]</label>
                    <input
                      type="text"
                      value={newPatientForm['Grade of Primary Brain Tumor']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Grade of Primary Brain Tumor': e.target.value })}
                      style={inputStyle}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={labelStyle}>Age at Diagnosis[cite: 7]</label>
                    <input
                      type="number"
                      value={newPatientForm['Age at diagnosis']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Age at diagnosis': e.target.value })}
                      style={inputStyle}
                      required
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Sex at Birth[cite: 7]</label>
                    <select
                      value={newPatientForm['Sex at Birth']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Sex at Birth': e.target.value })}
                      style={inputStyle}
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={labelStyle}>Progression Status[cite: 7]</label>
                  <select
                    value={newPatientForm.Progression}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, Progression: e.target.value })}
                    style={inputStyle}
                  >
                    <option value="0">0 (No Prior Progression)</option>
                    <option value="1">1 (Documented Progression)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    style={{
                      background: '#1e293b',
                      border: '1px solid #334155',
                      color: '#cbd5e1',
                      padding: '8px 14px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '13px',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{
                      background: '#0284c7',
                      border: 'none',
                      color: '#ffffff',
                      fontWeight: 600,
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '13px',
                    }}
                  >
                    Save & Run Analysis
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}