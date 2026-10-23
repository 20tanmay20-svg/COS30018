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
  report?: {
    status?: string;
    content?: string | null;
    error?: string | null;
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
  const [promptInput, setPromptInput] = useState('make me a report for patient 7');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [pipelineMode, setPipelineMode] = useState<'multi' | 'single'>('multi');
  const [pipelineProgress, setPipelineProgress] = useState<{
    percent: number;
    stageIndex: number;
    stageName: string;
  }>({ percent: 0, stageIndex: 0, stageName: '' });
  const [sharedState, setSharedState] = useState<SharedState | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newPatientForm, setNewPatientForm] = useState<PatientInput>(DEFAULT_NEW_PATIENT);

  const executePipeline = async (query: string, customPatientData?: PatientInput | null) => {
    console.log(`[FRONTEND CONSOLE] >>> Running pipeline for query: "${query}"`);
    setLoading(true);
    setErrorMessage(null);
    setSharedState(null);
    setStatusMessage('Synthesizing clinical dossier via multi-agent pipeline...');
    setPipelineProgress({
      percent: 10,
      stageIndex: 1,
      stageName: 'Patient Information Agent: Locating and indexing patient record...',
    });

    try {
      console.log('[FRONTEND CONSOLE] Requesting POST /api/v1/agent/run-pipeline ...');
      const payload: Record<string, any> = {
        user_request: query,
      };
      if (customPatientData) {
        payload.patient_id = customPatientData.Patient_ID;
        payload.patient_data = customPatientData;
        payload.data_source = 'manual_intake_buffer';
        payload.request_type = 'new_patient_intake';
      }

      const response = await fetch('/api/v1/agent/run-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      console.log('[FRONTEND CONSOLE] Backend response HTTP code:', response.status);

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Backend error (${response.status}): ${errText || response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Pipeline response body is empty or stream unavailable.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let finalState: SharedState | null = null;
      let streamError: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const event = JSON.parse(trimmed);
            if (event.type === 'progress') {
              setPipelineProgress({
                percent: event.percent,
                stageIndex: event.stage_index,
                stageName: event.message,
              });
              setStatusMessage(event.message);
            } else if (event.type === 'complete') {
              setPipelineProgress({
                percent: 100,
                stageIndex: 5,
                stageName: event.message || 'Multi-Agent Pipeline Complete: Dossier Assembled & Verified',
              });
              if (event.state) {
                finalState = event.state;
              }
            } else if (event.type === 'error') {
              streamError = event.message || 'An error occurred during pipeline execution.';
            }
          } catch (pErr) {
            console.warn('[FRONTEND CONSOLE] Stream parse warning:', trimmed, pErr);
          }
        }
      }

      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer.trim());
          if (event.type === 'complete' && event.state) {
            finalState = event.state;
          } else if (event.type === 'error') {
            streamError = event.message || 'An error occurred during pipeline execution.';
          }
        } catch {
          // ignore
        }
      }

      if (streamError) {
        throw new Error(streamError);
      }

      if (finalState) {
        console.log('[FRONTEND CONSOLE] <<< Final pipeline state received:', finalState);
        setSharedState(finalState);
        setLoading(false);
        setStatusMessage('Pipeline completed successfully.');
        return;
      }

      throw new Error('Pipeline completed without returning report state.');
    } catch (err: any) {
      console.error('[FRONTEND CONSOLE] Pipeline error:', err);
      const msg = err?.message || 'Failed to execute multi-agent pipeline.';
      setErrorMessage(msg);
      setStatusMessage(`Error: ${msg}`);
      setPipelineProgress({
        percent: 0,
        stageIndex: 0,
        stageName: 'Pipeline failed',
      });
      setSharedState(null);
      setLoading(false);
    }
  };

  const handlePromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('[FRONTEND CONSOLE] handlePromptSubmit triggered');
    if (loading) return;
    try {
      const query = promptInput.trim() || 'make me a report for patient 7';
      if (!promptInput.trim()) {
        setPromptInput(query);
      }
      console.log('[FRONTEND CONSOLE] Submitting query to pipeline:', query);
      executePipeline(query);
    } catch (err: any) {
      console.error('[FRONTEND CONSOLE] Exception in handlePromptSubmit:', err);
      setErrorMessage(err?.message || String(err));
      setStatusMessage(`Error: ${err?.message || err}`);
    }
  };

  const handleCreatePatientSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const pid = newPatientForm.Patient_ID.trim() || `PatientID_${Math.floor(1000 + Math.random() * 9000)}`;
    const createdRecord: PatientInput = { ...newPatientForm, Patient_ID: pid };

    setIsModalOpen(false);
    const query = `generate report for ${pid}`;
    setPromptInput(query);
    executePipeline(query, createdRecord);
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
          <span style={{ fontWeight: 700, letterSpacing: '0.04em', fontSize: '14px', color: '#f8fafc' }}>
            CLINICAL DECISION SUPPORT PLATFORM
          </span>
        </div>

        <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
          {/* Agent Pipeline Mode Switch */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#090e1f', border: '1px solid #1e293b', borderRadius: '20px', padding: '3px', gap: '3px' }}>
            <button
              type="button"
              onClick={() => setPipelineMode('single')}
              style={{
                padding: '5px 12px',
                borderRadius: '16px',
                fontSize: '11px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: pipelineMode === 'single' ? '#1e293b' : 'transparent',
                color: pipelineMode === 'single' ? '#f8fafc' : '#64748b',
                transition: 'all 0.2s',
              }}
            >
              Single Agent
            </button>
            <button
              type="button"
              onClick={() => setPipelineMode('multi')}
              style={{
                padding: '5px 12px',
                borderRadius: '16px',
                fontSize: '11px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: pipelineMode === 'multi' ? '#0284c7' : 'transparent',
                color: pipelineMode === 'multi' ? '#ffffff' : '#64748b',
                boxShadow: pipelineMode === 'multi' ? '0 0 10px rgba(2, 132, 199, 0.4)' : 'none',
                transition: 'all 0.2s',
              }}
            >
              Multi-Agent
            </button>
          </div>

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
              Issue prompt instructions to generate a multi-agent evidence synthesis and treatment report.
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>QUICK RUNS:</span>
            {[
              'make me a report for patient 7',
              'make me a report for patient 3',
              'evaluate PatientID_0005 with prior progression',
              'generate clinical report for PatientID_0004',
            ].map((suggested, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setPromptInput(suggested);
                  executePipeline(suggested);
                }}
                style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  color: '#94a3b8',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = '#38bdf8';
                  (e.currentTarget as HTMLElement).style.color = '#f8fafc';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = '#1e293b';
                  (e.currentTarget as HTMLElement).style.color = '#94a3b8';
                }}
              >
                {suggested}
              </button>
            ))}
          </div>

          {/* Error Banner when pipeline fails */}
          {errorMessage && (
            <div
              style={{
                marginTop: '18px',
                background: '#2d1215',
                border: '1px solid #ef4444',
                borderRadius: '8px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <span style={{ fontSize: '20px' }}>⚠️</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '13px', color: '#fecaca' }}>
                  Pipeline Execution Failed
                </div>
                <div style={{ fontSize: '12px', color: '#fca5a5', marginTop: '2px' }}>
                  {errorMessage}
                </div>
              </div>
            </div>
          )}

          {/* Live Multi-Agent Pipeline Progress Bar */}
          {(loading || pipelineProgress.percent > 0) && (
            <div style={{ marginTop: '18px', background: '#0b1329', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase',
                      color: loading ? '#38bdf8' : '#4ade80',
                    }}
                  >
                    {loading ? '⟳ Processing Multi-Agent Pipeline' : '✓ Pipeline Synthesis Complete'}
                  </span>
                  <span style={{ fontSize: '11px', color: '#475569' }}>•</span>
                  <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                    {pipelineProgress.stageName || statusMessage}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: '14px',
                    fontWeight: 700,
                    color: loading ? '#38bdf8' : '#4ade80',
                    fontFamily: 'monospace',
                  }}
                >
                  {pipelineProgress.percent}%
                </span>
              </div>

              {/* Progress Track */}
              <div style={{ width: '100%', height: '8px', background: '#070d1d', borderRadius: '4px', overflow: 'hidden', border: '1px solid #1e293b' }}>
                <div
                  style={{
                    width: `${pipelineProgress.percent}%`,
                    height: '100%',
                    background: loading
                      ? 'linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)'
                      : '#10b981',
                    borderRadius: '4px',
                    transition: 'width 0.4s ease-in-out',
                    boxShadow: loading ? '0 0 10px rgba(56, 189, 248, 0.5)' : '0 0 10px rgba(16, 185, 129, 0.4)',
                  }}
                />
              </div>

              {/* Stage Indicator Pills */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginTop: '12px' }}>
                {[
                  { id: 1, label: '1. Patient Profile' },
                  { id: 2, label: '2. PubMed Evidence' },
                  { id: 3, label: '3. Decision Support' },
                  { id: 4, label: '4. Verification' },
                  { id: 5, label: '5. Report Agent' },
                ].map((stg) => {
                  const isDone = pipelineProgress.stageIndex > stg.id || (!loading && pipelineProgress.percent === 100);
                  const isCurrent = loading && pipelineProgress.stageIndex === stg.id;
                  return (
                    <div
                      key={stg.id}
                      style={{
                        fontSize: '11px',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        textAlign: 'center',
                        fontWeight: 600,
                        background: isDone ? '#064e3b' : isCurrent ? '#0c4a6e' : '#0f172a',
                        color: isDone ? '#6ee7b7' : isCurrent ? '#38bdf8' : '#64748b',
                        border: isDone ? '1px solid #059669' : isCurrent ? '1px solid #0284c7' : '1px solid #1e293b',
                        boxShadow: isCurrent ? '0 0 8px rgba(56, 189, 248, 0.25)' : 'none',
                        transition: 'all 0.3s',
                      }}
                    >
                      {stg.label}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* Example Report (Ai generated for example) (This is hard coded but needs to become fluid with the backend) */}
        {sharedState && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Generated Clinical Report Card */}
            {sharedState.final_report && (
              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', background: '#111c38', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em', color: '#94a3b8', textTransform: 'uppercase' }}>
                    Structured Draft Radiology & Decision Report
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
                        "{sharedState.user_request}"
                      </div>
                    </div>
                  </div>

                  {/* Findings */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#38bdf8', margin: '0 0 6px 0' }}>
                      Clinical Findings
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
                      {sharedState.final_report.findings}
                    </p>
                  </div>

                  {/* Impression */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#38bdf8', margin: '0 0 6px 0' }}>
                      Clinical Impression
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
                      {sharedState.final_report.impression}
                    </p>
                  </div>

                  {/* Verified Treatment Strategy */}
                  <div style={{ background: '#071226', border: '1px solid #1e3a8a', padding: '16px', borderRadius: '6px' }}>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#60a5fa', margin: '0 0 8px 0' }}>
                      Verified Treatment Plan
                    </h4>
                    <div style={{ fontSize: '13px', lineHeight: '1.7', color: '#e2e8f0', whiteSpace: 'pre-line' }}>
                      {sharedState.final_report.treatment_plan}
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div>
                    <h4 style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', margin: '0 0 6px 0' }}>
                      Recommendations
                    </h4>
                    <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.6', color: '#94a3b8' }}>
                      {sharedState.final_report.recommendations}
                    </p>
                  </div>

                </div>
              </div>
            )}

            {/* Comprehensive Multi-Agent Assembled Report */}
            {sharedState.report?.content && (
              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', background: '#111c38', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
                    <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em', color: '#f8fafc', textTransform: 'uppercase' }}>
                      Report Generation Agent — Json Output
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', background: '#0f291e', color: '#34d399', border: '1px solid #059669', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    {sharedState.report.status?.toUpperCase() || 'VERIFIED'}
                  </span>
                </div>
                <div style={{ padding: '24px', background: '#090e1f' }}>
                  <div style={{ fontSize: '13px', lineHeight: '1.7', color: '#cbd5e1', whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>
                    {sharedState.report.content}
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
                  <label style={labelStyle}>Patient Identifier</label>
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
                    <label style={labelStyle}>Diagnosis</label>
                    <input
                      type="text"
                      value={newPatientForm['Primary Diagnosis']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Primary Diagnosis': e.target.value })}
                      style={inputStyle}
                      required
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>WHO Grade</label>
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
                    <label style={labelStyle}>Age at Diagnosis</label>
                    <input
                      type="number"
                      value={newPatientForm['Age at diagnosis']}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, 'Age at diagnosis': e.target.value })}
                      style={inputStyle}
                      required
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Sex at Birth</label>
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
                  <label style={labelStyle}>Progression Status</label>
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