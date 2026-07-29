from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    mfa_required: bool = False
    mfa_token: str | None = None


class TokenPayload(BaseModel):
    sub: str
    exp: int | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    org_name: str | None = None
    role: str | None = Field(
        default=None,
        description="Ignored for public register; org creator becomes org_admin",
    )


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class OnboardingOrgRequest(BaseModel):
    org_name: str = Field(min_length=2, max_length=100)


class LinkDriverRequest(BaseModel):
    driver_id: UUID | None = None
    create_driver_name: str | None = None


class MfaEnableResponse(BaseModel):
    secret: str
    otpauth_url: str
    phase: str = "8F"


class MfaConfirmRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=8)


class MfaLoginRequest(BaseModel):
    mfa_token: str
    totp_code: str = Field(min_length=6, max_length=8)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str
    org_id: UUID | None = None
    driver_id: UUID | None = None
    is_email_verified: bool = False
    mfa_enabled: bool = False
    is_active: bool = True

    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = "driver"
    full_name: str | None = None


class RoleChangeRequest(BaseModel):
    role: str
