export interface PatientInfo {
  fullName: string;
  dateOfBirth: string;
  biologicalSex: string;
  weightKg: string;
  scanType: string;
  contrastAdministered: boolean;
  presentingSymptoms: string;
  clinicalNotes: string;
}

export interface ImagingFinding {
  id: string; // e.g. "01", "02"
  text: string;
}

export interface DifferentialDiagnosis {
  name: string;
  probability: number; // e.g. 87 for 87%
  isPrimary?: boolean;
}

export interface PrimaryDiagnosis {
  title: string;
  icdCode: string;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  confidence: number;
  patientName: string;
  dateOfBirth: string;
  scanType: string;
  processedTime: string;
}

export interface TreatmentProtocolSection {
  title: string;
  details: string[];
}

export interface DiagnosticResult {
  primaryDiagnosis: PrimaryDiagnosis;
  imagingFindings: ImagingFinding[];
  differentialDiagnoses: DifferentialDiagnosis[];
  clinicalNotes: string;
  treatmentProtocol: TreatmentProtocolSection[];
}
