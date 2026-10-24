from typing import List, Optional
from pydantic import BaseModel, Field


class SignUpRequest(BaseModel):
    full_name: str = Field(..., min_length=1, description="User's full name")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Password (at least 8 characters)")
    terms_agreed: bool = Field(..., description="Must agree to Terms & Privacy Policy")
    age_confirmed: bool = Field(..., description="Must confirm age is 18 or older")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Your password")


class ProfileSaveRequest(BaseModel):
    dietary_conditions: List[str] = Field(default_factory=list, description="Section 01 chip IDs")
    allergies: List[str] = Field(default_factory=list, description="Section 02 chip IDs")
    nutrition_goals: List[str] = Field(default_factory=list, description="Section 03 chip IDs")
    avoid_ingredients: List[str] = Field(default_factory=list, description="Section 04 chip IDs")
    dietary_pattern: str = Field("none", description="Section 05 single select pattern ID")
    health_data_consent: bool = Field(False, description="Explicit consent to store conditions & allergies")
    consent_version: Optional[str] = Field("1.0", description="Version of consent notice acknowledged")
    path_taken: str = Field("basic", description="'basic' (Path A) or 'complete' (Path B)")


class EditProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    email: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Account email address")


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="Account email address")
    reset_token: str = Field(..., description="Verification reset code")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., description="Account password to confirm deletion")


class SavedComparisonCreate(BaseModel):
    query: str = Field(..., description="Product query or title")
    product_name: Optional[str] = None
    product_id: Optional[int] = None

