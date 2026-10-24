import logging
import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserProfile, SavedComparison, AuthSession
from app.schemas.user import (
    SignUpRequest,
    LoginRequest,
    ProfileSaveRequest,
    EditProfileRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    DeleteAccountRequest,
    SavedComparisonCreate,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    generate_token,
    load_profile_options,
    validate_profile_chips,
    export_user_data,
)

logger = logging.getLogger("labeltruth.auth_api")
router = APIRouter()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Extracts current authenticated user from Bearer authorization header.
    Returns None if no token or invalid session.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()
    stmt = select(AuthSession).where(AuthSession.token == token)
    res = await db.execute(stmt)
    session_rec = res.scalar_one_or_none()
    if not session_rec:
        return None

    user_stmt = select(User).where(User.id == session_rec.user_id)
    u_res = await db.execute(user_stmt)
    return u_res.scalar_one_or_none()


async def require_current_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Dependency that enforces authentication.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )
    return current_user


# -----------------------------------------------------------------------------
# 1. Profile Options Config (Single Source of Truth)
# -----------------------------------------------------------------------------
@router.get("/profile-options", summary="Get Personalisation Chip Options")
async def get_profile_options():
    """
    Returns config/profile_options.json for UI rendering.
    Enforces shared schema between backend validation and frontend chips.
    """
    return load_profile_options()


# -----------------------------------------------------------------------------
# 2. Authentication: Sign Up, Log In, Me
# -----------------------------------------------------------------------------
@router.post("/auth/signup", summary="Create User Account")
async def sign_up(req: SignUpRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validate age confirmation
    if not req.age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm you are 18 or older to create an account.",
        )

    # 2. Validate terms agreement
    if not req.terms_agreed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must agree to the Terms of Service and Privacy Policy.",
        )

    # 3. Email validation
    email_clean = req.email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide a valid email address.",
        )

    # 4. Check duplicate email
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # 5. Password strength
    is_valid, reason, _ = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason,
        )

    # 6. Create user
    new_user = User(
        email=email_clean,
        full_name=req.full_name.strip(),
        hashed_password=hash_password(req.password),
        is_verified=False,
        terms_agreed=True,
        age_confirmed=True,
    )
    db.add(new_user)
    await db.flush()

    # 7. Create empty user profile
    new_profile = UserProfile(
        user_id=new_user.id,
        dietary_conditions=[],
        allergies=[],
        nutrition_goals=[],
        avoid_ingredients=[],
        dietary_pattern="none",
        health_data_consent=False,
        path_taken="basic",
    )
    db.add(new_profile)

    # 8. Create session token
    token = generate_token()
    session_rec = AuthSession(token=token, user_id=new_user.id)
    db.add(session_rec)

    await db.commit()
    logger.info("New user account created successfully.")

    return {
        "user": new_user.to_dict(),
        "token": token,
        "profile": new_profile.to_dict(),
    }


@router.post("/auth/login", summary="Log In User")
async def log_in(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    email_clean = req.email.strip().lower()
    generic_error = "Invalid email or password."

    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=generic_error)

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=generic_error)

    # Load or initialize profile
    p_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    p_res = await db.execute(p_stmt)
    profile = p_res.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    # Issue session token
    token = generate_token()
    session_rec = AuthSession(token=token, user_id=user.id)
    db.add(session_rec)
    await db.commit()

    logger.info("User logged in successfully.")
    return {
        "user": user.to_dict(),
        "token": token,
        "profile": profile.to_dict(),
    }


@router.get("/auth/me", summary="Get Current Authenticated User & Profile")
async def get_me(user: User = Depends(require_current_user), db: AsyncSession = Depends(get_db)):
    p_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    p_res = await db.execute(p_stmt)
    profile = p_res.scalar_one_or_none()
    return {
        "user": user.to_dict(),
        "profile": profile.to_dict() if profile else None,
    }


@router.put("/auth/profile", summary="Update User Name or Email")
async def update_user(
    req: EditProfileRequest,
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.full_name:
        user.full_name = req.full_name.strip()
    if req.email:
        email_clean = req.email.strip().lower()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
            raise HTTPException(status_code=422, detail="Invalid email format.")
        # Check duplicate
        if email_clean != user.email:
            dup_stmt = select(User).where(User.email == email_clean)
            dup_res = await db.execute(dup_stmt)
            if dup_res.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="This email is already in use.")
            user.email = email_clean
            user.is_verified = False  # requires re-verification

    await db.commit()
    return {"user": user.to_dict(), "message": "Account profile updated successfully."}


@router.post("/auth/verify-email", summary="Simulate / Mark Email as Verified")
async def verify_email(user: User = Depends(require_current_user), db: AsyncSession = Depends(get_db)):
    user.is_verified = True
    await db.commit()
    return {"is_verified": True, "message": "Email address successfully verified."}


@router.post("/auth/forgot-password", summary="Initiate Password Reset")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    email_clean = req.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    reset_code = "DEMO-RESET-CODE"
    if user:
        reset_code = generate_token()[:8].upper()
        user.reset_token = reset_code
        await db.commit()

    return {
        "message": "If an account with that email exists, password reset instructions have been generated.",
        "reset_code": reset_code,
    }


@router.post("/auth/reset-password", summary="Complete Password Reset")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    email_clean = req.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.reset_token or user.reset_token.upper() != req.reset_token.strip().upper():
        raise HTTPException(status_code=400, detail="Invalid or expired reset code.")

    is_valid, reason, _ = validate_password_strength(req.new_password)
    if not is_valid:
        raise HTTPException(status_code=422, detail=reason)

    user.hashed_password = hash_password(req.new_password)
    user.reset_token = None
    await db.commit()

    return {"message": "Password reset successfully. You may now log in with your new password."}


# -----------------------------------------------------------------------------
# 3. Personalise Profile Save (Authenticated & Guest Modes)
# -----------------------------------------------------------------------------
@router.post("/profile/save", summary="Save Personalisation Profile")
async def save_profile(
    req: ProfileSaveRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Saves user personalisation profile.
    HARD RULES:
    1. Reject unknown chip IDs against profile_options.json.
    2. Sections 01 (dietary_conditions) and 02 (allergies) are health data:
       saving them requires explicit health_data_consent = True.
    3. Works for authenticated users (persisted in DB) and guest users (returned for session storage).
    """
    # 1. Validate chip IDs
    is_valid, error_msg = validate_profile_chips(
        dietary_conditions=req.dietary_conditions,
        allergies=req.allergies,
        nutrition_goals=req.nutrition_goals,
        avoid_ingredients=req.avoid_ingredients,
        dietary_pattern=req.dietary_pattern,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid profile selection: {error_msg}",
        )

    # 2. Enforce consent gate for health data (Sections 01 and 02)
    has_health_data = bool(req.dietary_conditions or req.allergies)
    if has_health_data and not req.health_data_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Saving health data (Sections 01 Dietary Conditions and 02 Allergies) requires explicit user consent: "
                "'We store your conditions and allergies only to personalise ratings and safety checks. You can delete them anytime.'"
            ),
        )

    consent_ts = datetime.now(timezone.utc) if req.health_data_consent else None

    # 3. If authenticated, persist to database
    if current_user:
        p_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
        p_res = await db.execute(p_stmt)
        profile = p_res.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.add(profile)

        profile.dietary_conditions = req.dietary_conditions
        profile.allergies = req.allergies
        profile.nutrition_goals = req.nutrition_goals
        profile.avoid_ingredients = req.avoid_ingredients
        profile.dietary_pattern = req.dietary_pattern
        profile.health_data_consent = req.health_data_consent
        profile.consent_version = req.consent_version or "1.0"
        profile.consent_timestamp = consent_ts
        profile.path_taken = req.path_taken
        await db.commit()

        logger.info("User profile persisted successfully.")
        return {
            "status": "saved",
            "is_guest": False,
            "profile": profile.to_dict(),
            "message": "Personalisation profile saved successfully.",
        }

    # 4. Guest session response
    guest_profile = {
        "user_id": None,
        "dietary_conditions": req.dietary_conditions,
        "allergies": req.allergies,
        "nutrition_goals": req.nutrition_goals,
        "avoid_ingredients": req.avoid_ingredients,
        "dietary_pattern": req.dietary_pattern,
        "health_data_consent": req.health_data_consent,
        "consent_version": req.consent_version or "1.0",
        "consent_timestamp": consent_ts.isoformat() if consent_ts else None,
        "path_taken": req.path_taken,
    }
    return {
        "status": "guest_session",
        "is_guest": True,
        "profile": guest_profile,
        "message": "Profile applied for this guest session. Create an account to save it permanently.",
    }


# -----------------------------------------------------------------------------
# 4. Data Privacy: Export & Hard Delete Account
# -----------------------------------------------------------------------------
@router.get("/auth/export-data", summary="Export All My Personal Data (JSON)")
async def export_my_data(
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports full user account info, profile, and saved comparisons as a JSON download.
    """
    p_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    p_res = await db.execute(p_stmt)
    profile = p_res.scalar_one_or_none()

    sc_stmt = select(SavedComparison).where(SavedComparison.user_id == user.id)
    sc_res = await db.execute(sc_stmt)
    saved_comparisons = sc_res.scalars().all()

    return export_user_data(user, profile, saved_comparisons)


@router.delete("/auth/account", summary="Hard Delete Account & Personal Data")
async def delete_account(
    req: DeleteAccountRequest,
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hard deletes the user's account, profile, sessions, and saved comparisons.
    Irreversible action requiring password confirmation.
    """
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Account deletion aborted.",
        )

    # 1. Delete user profile
    await db.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
    # 2. Delete saved comparisons
    await db.execute(delete(SavedComparison).where(SavedComparison.user_id == user.id))
    # 3. Delete auth sessions
    await db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    # 4. Delete user record
    await db.execute(delete(User).where(User.id == user.id))

    await db.commit()
    logger.info("User account and all associated personal data hard deleted.")
    return {"message": "Account and all associated personal data have been permanently deleted."}


# -----------------------------------------------------------------------------
# 5. Saved Comparisons (Stores product identifiers & timestamps only, NEVER health data)
# -----------------------------------------------------------------------------
@router.get("/saved-comparisons", summary="List Saved Comparisons")
async def list_saved_comparisons(
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SavedComparison)
        .where(SavedComparison.user_id == user.id)
        .order_by(SavedComparison.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [item.to_dict() for item in items]


@router.post("/saved-comparisons", summary="Save Comparison Item")
async def create_saved_comparison(
    req: SavedComparisonCreate,
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_sc = SavedComparison(
        user_id=user.id,
        query=req.query.strip(),
        product_name=req.product_name,
        product_id=req.product_id,
    )
    db.add(new_sc)
    await db.commit()
    return new_sc.to_dict()


@router.delete("/saved-comparisons/{comparison_id}", summary="Delete Saved Comparison")
async def delete_saved_comparison(
    comparison_id: int,
    user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = delete(SavedComparison).where(
        SavedComparison.id == comparison_id,
        SavedComparison.user_id == user.id,
    )
    await db.execute(stmt)
    await db.commit()
    return {"message": f"Saved comparison #{comparison_id} deleted."}

