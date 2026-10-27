export type UserRole = 'institution_user' | 'reviewer' | 'approving_authority' | 'admin';

export type FDRStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'EXTRACTED'
  | 'VALIDATED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'ACTIVE'
  | 'RENEWAL_PENDING'
  | 'RELEASED'
  | 'REJECTED'
  | 'CORRECTION_REQUESTED';

export type VerificationStatus =
  | 'PENDING'
  | 'VERIFIED'
  | 'REJECTED'
  | 'AWAITING_BANK_VERIFICATION';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  institution?: Institution;
}

export interface Institution {
  id: string;
  name: string;
  code: string;
  city?: string;
  state?: string;
  is_active?: boolean;
}

export interface FDRInstrument {
  id: string;
  internal_reference: string;
  institution_id: string;
  institution_name?: string;
  institution_code?: string;
  institution?: Institution;
  application_number?: string;
  bank_name: string;
  branch_name?: string;
  fdr_number: string;
  deposit_amount: number;
  currency: string;
  issue_date: string;
  maturity_date: string;
  status: FDRStatus;
  verification_status: VerificationStatus;
  review_priority_score: number;
  review_priority_reasons?: Record<string, any>;
  has_potential_duplicate: boolean;
  compliance_reference?: string;
  notes?: string;
  submitted_by?: string;
  assigned_reviewer_id?: string;
  assigned_reviewer?: User;
  created_at: string;
  updated_at: string;
}

export interface DashboardData {
  total_fdrs: number;
  active_fdrs: number;
  awaiting_verification: number;
  potential_duplicates: number;
  needs_review: number;
  maturing_30_days: number;
  overdue_actions: number;
  renewal_requests: number;
  pending_releases: number;
  released_fdrs: number;
  status_distribution: { status: string; count: number }[];
  recent_updates: FDRInstrument[];
  upcoming_deadlines: {
    id: string;
    internal_reference: string;
    maturity_date: string;
    institution_name: string;
    days_until: number;
  }[];
  monthly_maturities: { month: string; count: number; total_amount: number }[];
  review_queue?: FDRInstrument[];
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  entity_type?: string;
  entity_id?: string;
  is_read: boolean;
  due_date?: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  user_id: string;
  user?: User;
  role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
  before_values?: Record<string, any>;
  after_values?: Record<string, any>;
  reason?: string;
}

export interface DuplicateCandidate {
  id: string;
  fdr_a: FDRInstrument;
  fdr_b: FDRInstrument;
  match_score: number;
  match_reasons: Record<string, any>;
  matching_fields: string[];
  differing_fields: Record<string, any>;
  file_hash_match: boolean;
  status: string;
  review_notes?: string;
}

export interface ValidationFinding {
  id: string;
  field_name: string;
  submitted_value?: string;
  extracted_value?: string;
  finding_type: string;
  severity: string;
  description: string;
}

export interface ExtractionResult {
  id: string;
  extraction_method: string;
  extracted_fields: Record<string, any>;
  confidence_scores: Record<string, number>;
  raw_text: string;
  ai_model_used?: string;
  processing_time_ms?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
