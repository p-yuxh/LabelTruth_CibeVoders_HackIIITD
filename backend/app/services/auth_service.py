import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("labeltruth.auth")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_data", "profile_options.json")
if not os.path.exists(CONFIG_PATH):
    # Fallback to repo root config/profile_options.json
    ROOT_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "profile_options.json")
    if os.path.exists(ROOT_CONFIG):
        CONFIG_PATH = ROOT_CONFIG


def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt
    and 100,000 iterations.
    Format: pbkdf2:sha256:100000$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifies a plain password against the stored pbkdf2 hash.
    Constant-time comparison prevents timing attacks.
    """
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        algo, salt_hex, key_hex = parts
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        computed_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(computed_key, expected_key)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str, int]:
    """
    Validates minimum length (>= 8 chars) and evaluates strength score.
    Returns: (is_valid: bool, feedback: str, score: 1 | 2 | 3)
    1 = Weak, 2 = Medium, 3 = Strong
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long.", 1

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    checks_passed = sum([has_upper, has_lower, has_digit, has_special])
    if len(password) >= 12 and checks_passed >= 3:
        return True, "Strong password.", 3
    if len(password) >= 8 and checks_passed >= 2:
        return True, "Good password strength.", 2
    return True, "Weak password: consider adding uppercase letters, numbers, or symbols.", 1


def generate_token() -> str:
    """
    Generates a cryptographically secure random session token.
    """
    return secrets.token_urlsafe(32)


def load_profile_options() -> Dict[str, Any]:
    """
    Loads config/profile_options.json.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load profile options from {CONFIG_PATH}: {e}")
        return {"sections": []}


def get_allowed_chip_ids() -> Dict[str, List[str]]:
    """
    Extracts allowed chip IDs per section from profile_options.json.
    """
    data = load_profile_options()
    allowed = {}
    for sec in data.get("sections", []):
        sec_id = sec.get("id")
        chips = [c.get("id") for c in sec.get("chips", [])]
        allowed[sec_id] = chips
    return allowed


def validate_profile_chips(
    dietary_conditions: List[str],
    allergies: List[str],
    nutrition_goals: List[str],
    avoid_ingredients: List[str],
    dietary_pattern: str,
) -> Tuple[bool, Optional[str]]:
    """
    Validates that all submitted chip IDs exist in profile_options.json.
    Strictly rejects unknown IDs as per specification.
    """
    allowed = get_allowed_chip_ids()

    # Section 01
    valid_conds = allowed.get("dietary_conditions", [])
    for c in dietary_conditions:
        if c not in valid_conds:
            return False, f"Unknown dietary condition ID: '{c}'"

    # Section 02
    valid_allergies = allowed.get("allergies", [])
    for a in allergies:
        if a not in valid_allergies:
            return False, f"Unknown allergy ID: '{a}'"

    # Section 03
    valid_goals = allowed.get("nutrition_goals", [])
    for g in nutrition_goals:
        if g not in valid_goals:
            return False, f"Unknown nutrition goal ID: '{g}'"

    # Section 04
    valid_avoids = allowed.get("avoid_ingredients", [])
    for av in avoid_ingredients:
        if av not in valid_avoids:
            return False, f"Unknown avoid ingredient ID: '{av}'"

    # Section 05
    valid_patterns = allowed.get("dietary_pattern", ["none"])
    if dietary_pattern not in valid_patterns:
        return False, f"Unknown dietary pattern ID: '{dietary_pattern}'"

    return True, None


def export_user_data(user: Any, profile: Any, saved_comparisons: List[Any]) -> Dict[str, Any]:
    """
    Exports all personal account data in structured JSON format.
    Ensures complete transparency for GDPR/data privacy compliance.
    """
    return {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format_version": "1.0",
            "service": "LabelTruth Transparency Engine",
        },
        "account_information": {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "terms_agreed": user.terms_agreed,
            "age_confirmed": user.age_confirmed,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "personalization_profile": profile.to_dict() if profile else None,
        "saved_comparisons": [
            {
                "id": sc.id,
                "query": sc.query,
                "product_name": sc.product_name,
                "saved_at": sc.created_at.isoformat() if sc.created_at else None,
            }
            for sc in saved_comparisons
        ],
    }

