import json
import logging
import os
import hashlib
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_log import EvidenceLog
from app.services.personalized_scoring import PersonalizedScoringEngine, CATEGORY_REFERENCE_PRODUCTS
from app.services.tinyfish_scraper import tinyfish_scraper

logger = logging.getLogger("labeltruth.recommendation")


def _find_config_path() -> str:
    """Find the path to config/recommendation.json."""
    possible_paths = [
        # Root workspace config
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "recommendation.json")),
        # Backend config_data
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config_data", "recommendation.json")),
        # Current working dir config
        os.path.abspath(os.path.join(os.getcwd(), "config", "recommendation.json")),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        f"Required configuration file 'config/recommendation.json' not found. "
        f"Searched locations: {possible_paths}"
    )


def validate_config(cfg: Dict[str, Any], source: str = "config") -> Dict[str, Any]:
    """
    Strictly validate recommendation settings dictionary.
    Fails loudly if a required value is missing or threshold is outside the scale.
    Never defaults silently.
    """
    required_keys = [
        "rating_scale_min",
        "rating_scale_max",
        "rating_trigger_threshold",
        "min_rating_improvement",
        "allergen_trigger_max_rating",
        "max_results",
        "max_per_brand",
        "candidate_pool_size",
        "min_data_completeness",
        "category_match_level",
    ]

    for k in required_keys:
        if k not in cfg or cfg[k] is None:
            raise ValueError(f"Missing required recommendation config key: '{k}' in {source}")

    # Validate scale bounds
    scale_min = float(cfg["rating_scale_min"])
    scale_max = float(cfg["rating_scale_max"])
    if scale_min >= scale_max:
        raise ValueError(
            f"Invalid rating scale: rating_scale_min ({scale_min}) must be strictly less than rating_scale_max ({scale_max})"
        )

    # Validate trigger threshold within scale
    trigger_thresh = float(cfg["rating_trigger_threshold"])
    if not (scale_min <= trigger_thresh <= scale_max):
        raise ValueError(
            f"rating_trigger_threshold ({trigger_thresh}) is outside the scale [{scale_min}, {scale_max}]"
        )

    # Validate allergen trigger max rating within scale
    allergen_max_r = float(cfg["allergen_trigger_max_rating"])
    if not (scale_min <= allergen_max_r <= scale_max):
        raise ValueError(
            f"allergen_trigger_max_rating ({allergen_max_r}) is outside the scale [{scale_min}, {scale_max}]"
        )

    # Validate improvement delta
    improvement = float(cfg["min_rating_improvement"])
    if improvement <= 0:
        raise ValueError(f"min_rating_improvement ({improvement}) must be strictly positive")

    return cfg


def load_recommendation_config(cfg_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and strictly validate recommendation settings from file.
    Fails loudly at startup if a required value is missing or threshold is outside the scale.
    """
    config_path = cfg_path or _find_config_path()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to read recommendation config from '{config_path}': {e}")

    return validate_config(cfg, source=config_path)


# Module-level validated config
RECOMMENDATION_CONFIG = load_recommendation_config()


class RecommendationCache:
    """In-memory cache with TTL per (product_id, profile_hash, data_version)."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.data_version: int = 1

    def _make_key(self, product_id: Any, conditions: List[str], user_allergens: List[str]) -> str:
        profile_repr = f"cond:{sorted(conditions or [])}|allg:{sorted(user_allergens or [])}"
        p_hash = hashlib.sha256(profile_repr.encode("utf-8")).hexdigest()[:16]
        return f"{product_id}:{p_hash}:v{self.data_version}"

    def get(self, product_id: Any, conditions: List[str], user_allergens: List[str]) -> Optional[Dict[str, Any]]:
        key = self._make_key(product_id, conditions, user_allergens)
        entry = self._cache.get(key)
        if not entry:
            return None
        timestamp, data = entry
        if time.time() - timestamp > self.ttl:
            self._cache.pop(key, None)
            return None
        return data

    def set(self, product_id: Any, conditions: List[str], user_allergens: List[str], data: Dict[str, Any]):
        key = self._make_key(product_id, conditions, user_allergens)
        self._cache[key] = (time.time(), data)

    def invalidate_all(self):
        """Invalidate when product database or user profile changes."""
        self.data_version += 1
        self._cache.clear()


recommendation_cache = RecommendationCache()


class RecommendationService:
    """
    Better Alternatives Recommendation Service.
    Gates recommendations strictly on trigger conditions, enforces hard allergen and rating filters,
    ranks with tie-breakers, applies brand diversity caps, and computes data-driven explanations.
    """

    def __init__(
        self,
        scoring_engine: Optional[PersonalizedScoringEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.scoring_engine = scoring_engine or PersonalizedScoringEngine()
        self.config = validate_config(config, source="custom_config") if config else RECOMMENDATION_CONFIG

    def compute_data_completeness(self, product_dict: Dict[str, Any]) -> float:
        """
        Calculate data completeness score (0.0 to 1.0) based on required fields for evaluation.
        Needs ingredients, nutrition fields (serving, calories, carbs, sugars, sat fat, sodium).
        """
        if not product_dict:
            return 0.0

        required_nutrients = ["kcal", "carbs_g", "sugars_g", "protein_g", "fat_g", "saturated_fat_g", "sodium_mg"]
        nutrition = product_dict.get("nutrition", {})
        if not isinstance(nutrition, dict):
            return 0.0

        score = 0.0
        # Check nutrients present (70% weight)
        nutri_present = sum(1 for n in required_nutrients if nutrition.get(n) is not None)
        score += (nutri_present / len(required_nutrients)) * 0.7

        # Check ingredients list present and non-empty (20% weight)
        ingredients = product_dict.get("ingredients", [])
        if isinstance(ingredients, list) and len(ingredients) > 0:
            score += 0.2

        # Check category present (10% weight)
        cat = product_dict.get("category")
        if cat:
            score += 0.1

        return round(score, 2)

    def _extract_category_and_subcategory(self, product_dict: Dict[str, Any]) -> Tuple[str, str]:
        """Extract clean lowercased category and subcategory strings."""
        cat_item = product_dict.get("category", "")
        if isinstance(cat_item, dict):
            cat_val = str(cat_item.get("value", "")).strip().lower()
        else:
            cat_val = str(cat_item or "").strip().lower()

        subcat_item = product_dict.get("subcategory", "")
        if isinstance(subcat_item, dict):
            subcat_val = str(subcat_item.get("value", "")).strip().lower()
        else:
            subcat_val = str(subcat_item or "").strip().lower()

        return cat_val, subcat_val

    def _generate_data_driven_reasons(
        self,
        candidate_prod: Dict[str, Any],
        searched_prod: Dict[str, Any],
        user_allergens: List[str],
    ) -> List[str]:
        """
        Generate 1 to 3 plain-language reasons computed strictly from DATA differences.
        Never invented by an LLM.
        """
        reasons: List[str] = []
        c_nutri = candidate_prod.get("nutrition", {})
        p_nutri = searched_prod.get("nutrition", {})

        def get_val(nutri_dict, key):
            item = nutri_dict.get(key, {})
            if isinstance(item, dict):
                return item.get("value")
            try:
                return float(item) if item is not None else None
            except (ValueError, TypeError):
                return None

        # 1. Sugar difference
        c_sug = get_val(c_nutri, "sugars_g")
        p_sug = get_val(p_nutri, "sugars_g")
        if c_sug is not None and p_sug is not None and c_sug < p_sug:
            reasons.append(f"Sugar {c_sug} g vs {p_sug} g per serving")
        elif c_sug is not None and c_sug <= 2.0:
            reasons.append(f"Low sugar ({c_sug} g per serving)")

        # 2. Saturated fat difference
        c_sat = get_val(c_nutri, "saturated_fat_g")
        p_sat = get_val(p_nutri, "saturated_fat_g")
        if c_sat is not None and p_sat is not None and c_sat < p_sat:
            reasons.append(f"Saturated fat {c_sat} g vs {p_sat} g per serving")
        elif c_sat is not None and c_sat <= 1.0:
            reasons.append(f"Low saturated fat ({c_sat} g per serving)")

        # 3. Sodium difference
        c_sod = get_val(c_nutri, "sodium_mg")
        p_sod = get_val(p_nutri, "sodium_mg")
        if c_sod is not None and p_sod is not None and c_sod < p_sod:
            reasons.append(f"Sodium {c_sod} mg vs {p_sod} mg per serving")

        # 4. Oil difference (palm oil vs healthier oil)
        c_oil_item = candidate_prod.get("oil_listed", {})
        c_oil = c_oil_item.get("value", "") if isinstance(c_oil_item, dict) else str(c_oil_item or "")
        p_oil_item = searched_prod.get("oil_listed", {})
        p_oil = p_oil_item.get("value", "") if isinstance(p_oil_item, dict) else str(p_oil_item or "")

        p_uses_palm = "palm" in p_oil.lower() or (isinstance(p_oil_item, dict) and p_oil_item.get("is_palm_oil"))
        c_uses_palm = "palm" in c_oil.lower() or (isinstance(c_oil_item, dict) and c_oil_item.get("is_palm_oil"))

        if p_uses_palm and not c_uses_palm:
            if c_oil and c_oil.lower() not in ["none declared", "no cooking oil declared"]:
                reasons.append(f"Uses {c_oil} instead of palmolein")
            else:
                reasons.append("No palm oil or palmolein used")

        # 5. Allergen clearance statement
        if user_allergens and len(reasons) < 3:
            allergen_names = ", ".join(user_allergens)
            reasons.append(f"No listed {allergen_names} in the ingredients")

        # Fallback if no direct comparative wins found yet
        if not reasons:
            reasons.append("Significantly better nutrient and ingredient profile")

        return reasons[:3]

    async def get_alternatives(
        self,
        searched_product_id: Optional[int],
        searched_product_data: Optional[Dict[str, Any]],
        conditions: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for 'Better alternatives' recommendation.
        Returns:
        {
            status: "ok" | "none_found" | "not_needed" | "product_not_in_database",
            trigger: ["high_rating" | "allergen_conflict"],
            searched_product: {
                product_id,
                personalised_rating,
                rating_scale,
                allergen_conflict,
                conflicting_allergens
            },
            alternatives: [...],
            message: str
        }
        """
        conditions = conditions or ["general_health"]
        user_allergens = user_allergens or []
        cfg = self.config

        scale_str = f"{int(cfg['rating_scale_min'])}-{int(cfg['rating_scale_max'])}, higher is worse"

        # Check Cache first
        if searched_product_id is not None:
            cached_res = recommendation_cache.get(searched_product_id, conditions, user_allergens)
            if cached_res:
                logger.debug(f"CACHE HIT for alternatives: product_id={searched_product_id}")
                return cached_res

        # If product data is not provided, look it up by ID in EvidenceLog
        if not searched_product_data and searched_product_id is not None and session is not None:
            stmt = select(EvidenceLog).where(EvidenceLog.id == searched_product_id)
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if entry and entry.product_data:
                searched_product_data = entry.product_data

        # If still not found, return "product_not_in_database"
        if not searched_product_data:
            return {
                "status": "product_not_in_database",
                "trigger": [],
                "trigger_reason": None,
                "searched_product": {
                    "product_id": searched_product_id,
                    "name": None,
                    "brand": None,
                    "category": None,
                    "subcategory": None,
                    "personalised_rating": None,
                    "rating_scale": scale_str,
                    "allergen_conflict": False,
                    "conflicting_allergens": [],
                },
                "alternatives": [],
                "message": "The searched product is not available in our product database.",
                "disclaimer": "Ratings are computed for your profile; lower is better. Always check physical packaging for current ingredients and allergen warnings.",
            }

        # Gate conditions integration: coeliac_disease -> gluten, lactose_intolerance -> milk
        active_allergens = list(user_allergens or [])
        for cond in conditions:
            c_lower = str(cond).lower().strip()
            if any(k in c_lower for k in ["coeliac", "celiac"]):
                if not any(a.lower() in ["gluten", "wheat"] for a in active_allergens):
                    active_allergens.append("gluten")
            elif any(k in c_lower for k in ["lactose"]):
                if not any(a.lower() in ["milk", "dairy", "lactose"] for a in active_allergens):
                    active_allergens.append("milk")

        # -------------------------------------------------------------
        # 1. EVALUATE SEARCHED PRODUCT FOR TRIGGER CONDITIONS
        # -------------------------------------------------------------
        p_eval = self.scoring_engine.evaluate(
            product_data=searched_product_data,
            selected_conditions=conditions,
            user_allergens=active_allergens,
        )

        p_rating = p_eval.get("product_rating")
        allergy_check = p_eval.get("allergy_check", {})
        allergy_status = allergy_check.get("allergy_status", "NONE FOUND")
        conflicting_allergens = allergy_check.get("found_allergens", [])

        # Allergen conflict definition: existing allergy check reports product contains a user allergen
        has_allergen_conflict = (allergy_status == "NOT SAFE FOR YOU")

        # Rating validity check on scale
        is_rating_valid = (
            p_rating is not None
            and isinstance(p_rating, (int, float))
            and cfg["rating_scale_min"] <= p_rating <= cfg["rating_scale_max"]
        )

        # Trigger determination:
        # Trigger (a): personalised_rating > rating_trigger_threshold (strictly greater)
        # Trigger (b): allergen conflict is true
        triggers: List[str] = []
        if is_rating_valid and p_rating > cfg["rating_trigger_threshold"]:
            triggers.append("high_rating")
        if has_allergen_conflict:
            triggers.append("allergen_conflict")

        trigger_reason: Optional[str] = None
        if "high_rating" in triggers and "allergen_conflict" in triggers:
            trigger_reason = "both"
        elif "high_rating" in triggers:
            trigger_reason = "rating_threshold"
        elif "allergen_conflict" in triggers:
            trigger_reason = "allergen_conflict"

        p_cat_val, p_subcat_val = self._extract_category_and_subcategory(searched_product_data)
        p_name_val = ""
        p_name_item = searched_product_data.get("product_name", {})
        if isinstance(p_name_item, dict):
            p_name_val = str(p_name_item.get("value", "")).strip()
        else:
            p_name_val = str(p_name_item or "").strip()

        p_brand_item = searched_product_data.get("brand", {})
        p_brand_val = p_brand_item.get("value", "") if isinstance(p_brand_item, dict) else str(p_brand_item or "")

        searched_product_summary = {
            "product_id": searched_product_id,
            "name": p_name_val,
            "brand": p_brand_val,
            "category": p_cat_val,
            "subcategory": p_subcat_val,
            "personalised_rating": p_rating if is_rating_valid else None,
            "rating_scale": scale_str,
            "allergen_conflict": has_allergen_conflict,
            "conflicting_allergens": conflicting_allergens,
        }

        # If neither trigger fired: return status "not_needed"
        # Rule: "Invalid or missing rating for the searched product with no allergen conflict: return 'not_needed'."
        # Rule: "An unknown allergen status on the searched product does not trigger by itself."
        if not triggers:
            result = {
                "status": "not_needed",
                "trigger": [],
                "trigger_reason": None,
                "searched_product": searched_product_summary,
                "alternatives": [],
                "message": "Product performs adequately for your profile; no alternatives needed.",
                "disclaimer": "Ratings are computed for your profile; lower is better. Always check physical packaging for current ingredients and allergen warnings.",
            }
            if searched_product_id is not None:
                recommendation_cache.set(searched_product_id, conditions, user_allergens, result)
            return result

        # -------------------------------------------------------------
        # 2. CANDIDATE RETRIEVAL (SQL + Reference Pool)
        # -------------------------------------------------------------
        p_cat, p_subcat = self._extract_category_and_subcategory(searched_product_data)
        p_name = ""
        p_name_item = searched_product_data.get("product_name", {})
        if isinstance(p_name_item, dict):
            p_name = str(p_name_item.get("value", "")).strip().lower()
        else:
            p_name = str(p_name_item or "").strip().lower()

        # TinyFish live category scraping - candidates are discovered strictly from internet scraping
        # and NEVER retrieved from previous search logs in EvidenceLog
        candidate_pool: List[Dict[str, Any]] = []
        try:
            candidate_pool = await asyncio.to_thread(
                tinyfish_scraper.scrape_category_alternatives,
                product_name=p_name or "",
                category=p_cat or p_subcat or "Packaged Food",
                subcategory=p_subcat,
                limit=cfg.get("candidate_pool_size", 50),
            )
        except Exception as err:
            logger.warning(f"Error fetching live alternatives via TinyFish: {err}")
            candidate_pool = []

        # Use discovered category candidate pool, or reference pool if candidate pool is empty
        combined_candidates = candidate_pool if candidate_pool else CATEGORY_REFERENCE_PRODUCTS
        seen_names = set()
        unique_candidates = []
        for c in combined_candidates:
            c_name = ""
            c_n_item = c.get("product_name", {})
            if isinstance(c_n_item, dict):
                c_name = str(c_n_item.get("value", "")).strip().lower()
            else:
                c_name = str(c_n_item or "").strip().lower()

            if not c_name or c_name == p_name or c_name in seen_names:
                continue
            seen_names.add(c_name)
            unique_candidates.append(c)

        # -------------------------------------------------------------
        # 3. APPLY HARD FILTERS TO CANDIDATES
        # -------------------------------------------------------------
        eligible_candidates: List[Dict[str, Any]] = []

        # Debug filter rejection counts
        filter_rejection_counts = {
            "category_mismatch": 0,
            "allergen_unsafe": 0,
            "allergen_unknown": 0,
            "incomplete_data": 0,
            "insufficient_rating_improvement": 0,
            "invalid_rating": 0,
        }

        for cand in unique_candidates:
            # Hard Filter 1: Not searched product (already handled by name and ID)

            # Hard Filter 2: Same category (never cross categories)
            c_cat, c_subcat = self._extract_category_and_subcategory(cand)
            same_category = False
            if p_cat and c_cat:
                if p_cat in c_cat or c_cat in p_cat:
                    same_category = True
                elif any(k in p_cat and k in c_cat for k in ["snack", "noodle", "drink", "beverage", "biscuit", "chip", "cereal", "oats", "makhana"]):
                    same_category = True
            elif not p_cat and not c_cat:
                same_category = True

            if not same_category:
                filter_rejection_counts["category_mismatch"] += 1
                continue

            # Hard Filter 5: Data Completeness
            completeness = self.compute_data_completeness(cand)
            if completeness < cfg["min_data_completeness"]:
                filter_rejection_counts["incomplete_data"] += 1
                continue

            # Hard Filter 4: Allergen status must be KNOWN
            c_ingredients = cand.get("ingredients", [])
            if not c_ingredients or not isinstance(c_ingredients, list) or len(c_ingredients) == 0:
                filter_rejection_counts["allergen_unknown"] += 1
                continue

            c_oil_item = cand.get("oil_listed", {})
            c_oil = c_oil_item.get("value", "") if isinstance(c_oil_item, dict) else str(c_oil_item or "")

            # Run existing allergy check
            c_name_val = ""
            c_n_item = cand.get("product_name", {})
            if isinstance(c_n_item, dict):
                c_name_val = str(c_n_item.get("value", ""))
            else:
                c_name_val = str(c_n_item or "")

            allergy_res = self.scoring_engine.check_allergens(
                c_ingredients, c_oil, active_allergens, product_name=c_name_val
            )

            if allergy_res["allergy_status"] == "CANNOT CONFIRM":
                filter_rejection_counts["allergen_unknown"] += 1
                continue

            # Hard Filter 3: ALLERGEN SAFE for user (contains or may-contain check)
            if allergy_res["allergy_status"] == "NOT SAFE FOR YOU":
                filter_rejection_counts["allergen_unsafe"] += 1
                continue

            # Also check may_contain_allergens field if present
            may_contain = cand.get("may_contain_allergens", []) or []
            if any(ua.lower() in [m.lower() for m in may_contain] for ua in active_allergens):
                filter_rejection_counts["allergen_unsafe"] += 1
                continue

            # Hard Filter 6: Rating must be better on 1-10 scale
            c_eval = self.scoring_engine.evaluate(cand, conditions, user_allergens)
            c_rating = c_eval.get("product_rating")

            if (
                c_rating is None
                or not isinstance(c_rating, (int, float))
                or not (cfg["rating_scale_min"] <= c_rating <= cfg["rating_scale_max"])
            ):
                filter_rejection_counts["invalid_rating"] += 1
                continue

            # Check rating rule based on trigger:
            # - Trigger (a) (high rating, or both): candidate_rating <= P_rating - min_rating_improvement
            # - Trigger (b) only (allergen conflict, but P_rating not high): candidate_rating <= allergen_trigger_max_rating
            is_better = False
            if "high_rating" in triggers:
                if is_rating_valid and c_rating <= (p_rating - cfg["min_rating_improvement"]):
                    is_better = True
            else:
                # Allergen conflict only
                if c_rating <= cfg["allergen_trigger_max_rating"]:
                    is_better = True

            if not is_better:
                filter_rejection_counts["insufficient_rating_improvement"] += 1
                continue

            # Subcategory match flag for tie-breaker
            is_subcat_match = bool(p_subcat and c_subcat and p_subcat == c_subcat)

            # Count contradicted / misleading claims for tie-breaking
            c_claims = cand.get("front_pack_claims", []) or []
            flagged_claims = sum(
                1 for cl in c_claims
                if str(cl.get("audit_verdict", "")).upper() in ["CONTRADICTED", "MISLEADING"]
            )

            cand_brand = cand.get("brand", {})
            b_val = cand_brand.get("value", "") if isinstance(cand_brand, dict) else str(cand_brand or "")

            cand_name_val = cand.get("product_name", {})
            n_val = cand_name_val.get("value", "") if isinstance(cand_name_val, dict) else str(cand_name_val or "")

            reasons = self._generate_data_driven_reasons(cand, searched_product_data, user_allergens)

            rating_delta = round(p_rating - c_rating, 2) if is_rating_valid else None

            allergen_statement = (
                f"No listed {', '.join(user_allergens)} in the ingredients. Always check the pack."
                if user_allergens
                else "No listed user allergens in the ingredients. Always check the pack."
            )

            data_conf = "high" if completeness >= 0.8 else ("medium" if completeness >= 0.5 else "low")

            eligible_candidates.append({
                "product_id": cand.get("id") or cand.get("evidence_log_id"),
                "brand": b_val or "Unknown Brand",
                "name": n_val or "Product",
                "variant": cand.get("variant") or None,
                "pack_size": cand.get("pack_size") or (cand.get("nutrition", {}).get("serving_size", {}).get("value") if isinstance(cand.get("nutrition", {}).get("serving_size"), dict) else None),
                "category": c_cat or None,
                "subcategory": c_subcat or None,
                "personalised_rating": c_rating,
                "rating_delta": rating_delta,
                "rating_improvement": rating_delta,
                "data_reasons": reasons,
                "reasons": reasons,
                "data_confidence": data_conf,
                "allergen_status": "no_listed_user_allergen",
                "allergen_statement": allergen_statement,
                "source_url": cand.get("product_name", {}).get("source_url", "") if isinstance(cand.get("product_name"), dict) else (cand.get("source_urls", [""])[0] if cand.get("source_urls") else ""),
                "disclaimer": allergen_statement if has_allergen_conflict else None,
                "data_as_of": cand.get("updated_at") or cand.get("created_at") or "2026-10-25",
                # Sorting helper keys:
                "_subcat_match": is_subcat_match,
                "_flagged_claims": flagged_claims,
                "_data_confidence": completeness,
            })

        logger.debug(f"Candidate rejection stats: {filter_rejection_counts}")

        # -------------------------------------------------------------
        # 4. RANKING, BRAND DIVERSITY CAP & LIMITS
        # -------------------------------------------------------------
        # Sort keys:
        # 1. personalised_rating ascending (lowest = best)
        # 2. category similarity (same subcategory first: False < True so -int(subcat))
        # 3. fewer contradicted / misleading claims
        # 4. higher data confidence (completeness descending)
        # 5. product name ascending (stable tie-break)
        eligible_candidates.sort(
            key=lambda x: (
                x["personalised_rating"],
                -int(x["_subcat_match"]),
                x["_flagged_claims"],
                -x["_data_confidence"],
                x["name"].lower(),
            )
        )

        # Apply Brand Diversity: At most max_per_brand from the same brand
        max_per_brand = int(cfg["max_per_brand"])
        max_results = int(cfg["max_results"])

        selected_alternatives: List[Dict[str, Any]] = []
        brand_counts: Dict[str, int] = {}

        for alt in eligible_candidates:
            b_clean = alt["brand"].strip().lower()
            if brand_counts.get(b_clean, 0) < max_per_brand:
                brand_counts[b_clean] = brand_counts.get(b_clean, 0) + 1
                # Clean up internal sort keys
                clean_alt = {k: v for k, v in alt.items() if not k.startswith("_")}
                selected_alternatives.append(clean_alt)
                if len(selected_alternatives) == max_results:
                    break

        # Response construction
        disclaimer_text = (
            "Ratings are computed for your profile; lower is better. "
            "Always check physical packaging for current ingredients and allergen warnings."
        )

        if not selected_alternatives:
            result = {
                "status": "none_found",
                "trigger": triggers,
                "trigger_reason": trigger_reason,
                "searched_product": searched_product_summary,
                "alternatives": [],
                "message": "no allergen-safe products with a better rating in this category in our database",
                "disclaimer": disclaimer_text,
            }
        else:
            result = {
                "status": "ok",
                "trigger": triggers,
                "trigger_reason": trigger_reason,
                "searched_product": searched_product_summary,
                "alternatives": selected_alternatives,
                "message": f"Found {len(selected_alternatives)} better alternative(s) for your profile.",
                "disclaimer": disclaimer_text,
            }

        if searched_product_id is not None:
            recommendation_cache.set(searched_product_id, conditions, user_allergens, result)

        return result


# Global recommendation service singleton
recommendation_service = RecommendationService()
