from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    display_name: str | None
    is_active: bool
    mfa_enabled: bool = False
    # True when the role requires MFA and the user has not enrolled yet.
    mfa_enrollment_required: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Login result.

    Exactly one of these shapes is returned:
    - signed in: access_token + user (refresh cookie set)
    - mfa_required: mfa_token only (no access token, no cookie)
    - mfa_enrollment_required with enrollment_token (strict enforcement only)
    """

    access_token: str | None = None
    token_type: str = "bearer"
    user: UserPublic | None = None
    mfa_required: bool = False
    mfa_token: str | None = None
    enrollment_token: str | None = None
    mfa_enrollment_required: bool = False


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LogoutResponse(BaseModel):
    status: str = "ok"


class TokenPayload(BaseModel):
    sub: UUID
    role: UserRole
    exp: datetime


OTP_FIELD = Field(default=None, min_length=6, max_length=12)
RECOVERY_FIELD = Field(default=None, min_length=8, max_length=24)


class MFAVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mfa_token: str = Field(min_length=20, max_length=2048)
    code: str | None = OTP_FIELD
    recovery_code: str | None = RECOVERY_FIELD

    @model_validator(mode="after")
    def one_factor(self):
        if bool(self.code) == bool(self.recovery_code):
            raise ValueError("Provide exactly one of code or recovery_code")
        return self


class PasswordReauthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


class MFAEnrollStartResponse(BaseModel):
    # Shown once, only while enrollment is pending, so the user can add the
    # account to an authenticator app. Never returned again after enabling.
    secret: str
    otpauth_uri: str
    qr_svg_data_uri: str


class MFAEnrollVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=12)


class MFARecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]
    # Present when enrollment also signed the user in (strict-mode enrollment).
    access_token: str | None = None
    user: UserPublic | None = None


class MFARegenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=12)


class MFADisableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
    code: str | None = OTP_FIELD
    recovery_code: str | None = RECOVERY_FIELD

    @model_validator(mode="after")
    def one_factor(self):
        if bool(self.code) == bool(self.recovery_code):
            raise ValueError("Provide exactly one of code or recovery_code")
        return self


class MFAStatusResponse(BaseModel):
    enabled: bool
    enabled_at: datetime | None
    pending_enrollment: bool
    recovery_codes_remaining: int
    required_for_role: bool
    enforcement_mode: str
    locked_until: datetime | None


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)
    code: str | None = OTP_FIELD


class SessionInfo(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    mfa_verified: bool
    current: bool


class SessionListResponse(BaseModel):
    items: list[SessionInfo]


class SessionsRevokedResponse(BaseModel):
    revoked: int


class AdminMFAResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_password: str = Field(min_length=1, max_length=128)
