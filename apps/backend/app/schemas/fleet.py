from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleCreate(BaseModel):
    name: str
    vin: str | None = None
    model: str | None = None
    year: int | None = None
    fuel_type: str | None = None
    org_id: UUID | None = None


class VehicleResponse(BaseModel):
    id: UUID
    name: str
    vin: str | None = None
    model: str | None = None
    year: int | None = None
    fuel_type: str | None = None
    org_id: UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverCreate(BaseModel):
    name: str
    email: EmailStr
    license_number: str | None = None
    org_id: UUID | None = None


class DriverResponse(BaseModel):
    id: UUID
    name: str
    email: str
    license_number: str | None = None
    org_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
