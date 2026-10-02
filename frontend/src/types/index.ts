export type UserRole = 'ADMIN' | 'TEACHER' | 'STUDENT' | 'GUARDIAN';
export type AssignmentState = 'DRAFT' | 'PENDING_APPROVAL' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
export type AssignmentTargetType = 'CLASS' | 'GROUP' | 'INDIVIDUAL';
export type SubmissionState = 'NOT_STARTED' | 'IN_PROGRESS' | 'BLOCKED' | 'SUBMITTED' | 'REVISION_REQUESTED' | 'RESUBMITTED' | 'COMPLETED';
export type DocumentType = 'ASSIGNMENT_BRIEF' | 'ROSTER' | 'POLICY' | 'SUBMISSION_ATTACHMENT' | 'CLASS_MATERIAL';
export type ParseApprovalState = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NEEDS_CLARIFICATION';
export type FeedbackAction = 'COMMENT' | 'REVISION_REQUEST' | 'APPROVAL';
export type ReminderType = 'UPCOMING' | 'OVERDUE' | 'ESCALATION';
export type ReminderState = 'SCHEDULED' | 'SENT' | 'SKIPPED_QUIET' | 'SKIPPED_SUBMITTED' | 'FAILED';
export type PolicyType = 'QUIET_HOURS' | 'ESCALATION' | 'APPROVAL_REQUIRED' | 'CHANNEL_RULES';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  school_id: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
}

export interface School {
  id: string;
  name: string;
  code: string;
  address: string | null;
  timezone: string;
  created_at: string;
}

export interface GradeClass {
  id: string;
  school_id: string;
  name: string;
  grade_level: string | null;
  created_at: string;
  teacher_count: number;
  student_count: number;
}

export interface Assignment {
  id: string;
  school_id: string;
  title: string;
  subject: string | null;
  instructions: string | null;
  due_date: string | null;
  target_type: AssignmentTargetType;
  target_class_id: string | null;
  state: AssignmentState;
  created_by: string;
  creator_name?: string;
  created_at: string;
  submission_summary?: {
    NOT_STARTED?: number;
    IN_PROGRESS?: number;
    BLOCKED?: number;
    SUBMITTED?: number;
    REVISION_REQUESTED?: number;
    RESUBMITTED?: number;
    COMPLETED?: number;
    [key: string]: number | undefined;
  };
}

export interface Submission {
  id: string;
  assignment_id: string;
  student_id: string;
  student_name: string;
  state: SubmissionState;
  content_text: string | null;
  blocked_reason: string | null;
  submitted_at: string | null;
  created_at: string;
  feedback: Feedback[];
}

export interface Feedback {
  id: string;
  submission_id: string;
  teacher_id: string;
  teacher_name: string;
  content: string;
  action: FeedbackAction;
  created_at: string;
}

export interface Document {
  id: string;
  document_type: DocumentType;
  original_filename: string;
  mime_type: string | null;
  file_size: number | null;
  uploaded_by: string;
  created_at: string;
}

export interface ParseResult {
  id: string;
  document_id: string;
  parsed_data: Record<string, any>;
  ambiguity_flags: string[];
  confidence_notes: Record<string, any>;
  approval_state: ParseApprovalState;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  correlation_id: string;
  event_type: string;
  actor_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface InviteToken {
  id: string;
  token: string;
  role: UserRole;
  target_class_id: string | null;
  expires_at: string;
  created_at: string;
  invite_url: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}
