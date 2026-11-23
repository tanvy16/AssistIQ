import enum


class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    AGENT = "agent"
    ADMIN = "admin"


class AuthAuditEventType(str, enum.Enum):
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    REFRESH = "auth.refresh"
    ACCOUNT_LOCKED = "auth.account_locked"
    LOGIN_BLOCKED = "auth.login_blocked_locked"
    REFRESH_REUSE_DETECTED = "auth.refresh_reuse_detected"
    REFRESH_REJECTED_MFA = "auth.refresh_rejected_mfa"
    SESSIONS_REVOKED = "auth.sessions_revoked"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_CHANGE_FAILED = "auth.password_change_failed"


class SecurityAuditEventType(str, enum.Enum):
    PERMISSION_DENIED = "authz.denied"
    MFA_CHALLENGE_ISSUED = "mfa.challenge_issued"
    MFA_ENROLLMENT_STARTED = "mfa.enrollment_started"
    MFA_ENROLLMENT_FAILED = "mfa.enrollment_failed"
    MFA_ENABLED = "mfa.enabled"
    MFA_VERIFIED = "mfa.verified"
    MFA_VERIFY_FAILED = "mfa.verify_failed"
    MFA_LOCKED = "mfa.locked"
    MFA_RECOVERY_CODE_USED = "mfa.recovery_code_used"
    MFA_RECOVERY_CODES_REGENERATED = "mfa.recovery_codes_regenerated"
    MFA_DISABLED = "mfa.disabled"
    MFA_DISABLE_FAILED = "mfa.disable_failed"
    MFA_ADMIN_RESET = "mfa.admin_reset"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, enum.Enum):
    NETWORK = "network"
    ACCESS = "access"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    OTHER = "other"


class TicketEventType(str, enum.Enum):
    CREATED = "ticket.created"
    ASSIGNED = "ticket.assigned"
    UNASSIGNED = "ticket.unassigned"
    STATUS_CHANGED = "ticket.status_changed"
    PRIORITY_CHANGED = "ticket.priority_changed"
    COMMENT_ADDED = "ticket.comment_added"


class KnowledgeDocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
