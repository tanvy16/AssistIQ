export type PasswordResetStatus =
  | "submitted"
  | "verification_required"
  | "verification_failed"
  | "risk_review"
  | "confirmation_required"
  | "approved"
  | "executing"
  | "completed"
  | "rejected"
  | "escalated"
  | "failed";

export type PasswordResetListItem = {
  id: string;
  requester_id: string;
  target_user_id: string;
  status: PasswordResetStatus;
  verification_status: string;
  risk_level: string;
  policy_decision: string | null;
  created_at: string;
};

export type PasswordResetEvent = {
  id: string;
  event_type: string;
  actor_id: string | null;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
};

export type PasswordResetDetail = PasswordResetListItem & {
  conversation_id: string | null;
  reason: string | null;
  adapter_name: string | null;
  execution_result: Record<string, unknown> | null;
  validation_result: Record<string, unknown> | null;
  expires_at: string;
  completed_at: string | null;
  requires_confirmation?: boolean;
  events: PasswordResetEvent[];
};
