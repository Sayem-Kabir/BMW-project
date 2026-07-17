from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class TokenPayload(BaseModel):
    sub: str
    exp: int | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    org_name: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str
    org_id: UUID | None = None

    model_config = {"from_attributes": True}
