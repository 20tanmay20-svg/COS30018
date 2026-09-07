const API_BASE = '/api/v1';

export interface Scan {
  id: number;
  patient_id: string;
  file_path: string;
  modality: string;
  status: string;
  wt_volume_cm3?: number;
  tc_volume_cm3?: number;
  et_volume_cm3?: number;
  created_at: string;
}

export interface Report {
  id: number;
  scan_id: number;
  findings: string;
  impression: string;
  recommendations?: string;
  created_at: string;
}

export interface AgentChatResponse {
  session_id: string;
  response: string;
  tools_used: string[];
}

export const api = {
  // Scans
  async getScans(): Promise<Scan[]> {
    const res = await fetch(`${API_BASE}/scans`);
    if (!res.ok) throw new Error('Failed to fetch scans');
    return res.json();
  },

  async createScan(patientId: string): Promise<Scan> {
    const res = await fetch(`${API_BASE}/scans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId, modality: 'BraTS-Multimodal' }),
    });
    if (!res.ok) throw new Error('Failed to create scan');
    return res.json();
  },

  // MONAI SegResNet Segmentation
  async runSegmentation(scanId: number): Promise<{ wt_volume_cm3: number; tc_volume_cm3: number; et_volume_cm3: number }> {
    const res = await fetch(`${API_BASE}/scans/${scanId}/segment`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run MONAI segmentation');
    return res.json();
  },

  // Gemini Report Generation
  async generateReport(scanId: number, clinicalHistory?: string): Promise<Report> {
    const res = await fetch(`${API_BASE}/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scan_id: scanId, clinical_history: clinicalHistory }),
    });
    if (!res.ok) throw new Error('Failed to generate report');
    return res.json();
  },

  // smolagents Chat
  async sendChatMessage(sessionId: string, message: string, scanId?: number): Promise<AgentChatResponse> {
    const res = await fetch(`${API_BASE}/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message, scan_id: scanId }),
    });
    if (!res.ok) throw new Error('Failed to contact agent');
    return res.json();
  },
};
