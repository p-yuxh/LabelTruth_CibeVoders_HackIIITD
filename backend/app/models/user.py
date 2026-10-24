from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from app.models.evidence_log import Base


class User(Base):
    """
    User Account Table.
    Stores core authentication credentials and verification flags.
    No health, allergy, or dietary data is stored on this record.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    terms_agreed = Column(Boolean, default=True, nullable=False)
    age_confirmed = Column(Boolean, default=True, nullable=False)
    reset_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_verified": self.is_verified,
            "terms_agreed": self.terms_agreed,
            "age_confirmed": self.age_confirmed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserProfile(Base):
    """
    User Profile Personalisation Table.
    Sections 01 (dietary_conditions) and 02 (allergies) are health data and
    strictly require health_data_consent = True before storage.
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    
    # Section 01: Dietary Conditions (ids from profile_options.json)
    dietary_conditions = Column(JSON, default=list, nullable=False)
    
    # Section 02: Allergies (ids from profile_options.json)
    allergies = Column(JSON, default=list, nullable=False)
    
    # Section 03: Nutrition Goals
    nutrition_goals = Column(JSON, default=list, nullable=False)
    
    # Section 04: Ingredients to Avoid
    avoid_ingredients = Column(JSON, default=list, nullable=False)
    
    # Section 05: Dietary Pattern (single select)
    dietary_pattern = Column(String(50), default="none", nullable=False)
    
    # Explicit consent for health data (Sections 01 and 02)
    health_data_consent = Column(Boolean, default=False, nullable=False)
    consent_version = Column(String(50), nullable=True)
    consent_timestamp = Column(DateTime, nullable=True)
    
    # Path taken: 'basic' (sections 03, 04, 05) or 'complete' (all five)
    path_taken = Column(String(20), default="basic", nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "dietary_conditions": self.dietary_conditions or [],
            "allergies": self.allergies or [],
            "nutrition_goals": self.nutrition_goals or [],
            "avoid_ingredients": self.avoid_ingredients or [],
            "dietary_pattern": self.dietary_pattern or "none",
            "health_data_consent": self.health_data_consent,
            "consent_version": self.consent_version,
            "consent_timestamp": self.consent_timestamp.isoformat() if self.consent_timestamp else None,
            "path_taken": self.path_taken,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SavedComparison(Base):
    """
    Saved Comparisons Table.
    HARD RULE: Stores product IDs, query strings, and timestamps ONLY.
    NEVER stores health data or personalized scores.
    When loaded, comparisons are dynamically re-rated against the user's CURRENT profile.
    """
    __tablename__ = "saved_comparisons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    query = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=True)
    product_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "product_name": self.product_name,
            "product_id": self.product_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuthSession(Base):
    """
    Active User Auth Sessions Table.
    """
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "token": self.token,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

