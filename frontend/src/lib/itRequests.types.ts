export type ITRequestType = "software" | "access" | "permission";
export type ITRequestStatus =
  | "submitted"
  | "parsed"
  | "policy_review"
  | "approval_required"
  | "approved"
  | "rejected"
  | "planned"
  | "executing"
  | "validating"
  | "completed"
  | "failed"
  | "rolled_back"
  | "escalated"
  | "cancelled";

export type ITRequestListItem = {
  id: string;
  request_type: ITRequestType;
  status: ITRequestStatus;
  requested_resource: string;
  risk_level: string;
  policy_decision: string | null;
  approval_required: boolean;
  created_at: string;
};

export type ITRequestEntity = {
  id: string;
  entity_type: string;
  entity_name: string;
  entity_value: string;
  confidence: number;
  source: string;
};

export type ITRequestEvent = {
  id: string;
  event_type: string;
  actor_id: string | null;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
};

export type ITRequestExecution = {
  id: string;
  runbook_id: string;
  status: string;
  adapter_name: string;
  started_at: string | null;
  completed_at: string | null;
  execution_result: Record<string, unknown> | null;
  validation_result: Record<string, unknown> | null;
  rollback_status: string | null;
};

export type ITRequestDetail = ITRequestListItem & {
  requester_id: string;
  justification: string | null;
  selected_runbook_id: string | null;
  user_message: string;
  plan: Record<string, unknown> | null;
  entities: ITRequestEntity[];
  executions: ITRequestExecution[];
  completed_at: string | null;
};

export type SoftwareCatalogItem = {
  id: string;
  name: string;
  vendor: string | null;
  risk_level: string;
  approval_required: boolean;
  enabled: boolean;
  runbook_id: string;
};

export type AccessCatalogItem = {
  id: string;
  resource_name: string;
  resource_type: string;
  environment: string;
  risk_level: string;
  approval_required: boolean;
  enabled: boolean;
  runbook_id: string;
};

export type RunbookItem = {
  id: string;
  name: string;
  action_type: string;
  enabled: boolean;
  risk_level: string;
  rollback_supported: boolean;
};
