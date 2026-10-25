import json
import logging
import os
import re
import uuid
import hashlib
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_log import EvidenceLog
from app.services.personalized_scoring import PersonalizedScoringEngine, CATEGORY_REFERENCE_PRODUCTS
from app.services.tinyfish_scraper import tinyfish_scraper, validate_extracted_product

logger = logging.getLogger("labeltruth.recommendation")


def _find_config_path() -> str:
    """Find the path to config/recommendation.json."""
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "recommendation.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config_data", "recommendation.json")),
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
    Fails loudly if a required value is missing, threshold is outside scale,
    or startup invariants are violated. Never defaults silently.
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
        # New required tiered acquisition keys:
        "live_discovery_enabled",
        "min_stored_candidates",
        "live_detail_budget",
        "live_total_deadline_seconds",
        "live_call_timeout_seconds",
        "live_concurrency",
        "listing_cache_ttl_hours",
        "detail_cache_ttl_days",
        "availability_ttl_hours",
        "max_live_calls_per_user_per_day",
        "max_live_calls_global_per_day",
        "allow_cross_source_fallback",
    ]

    for k in required_keys:
        if k not in cfg or cfg[k] is None:
            raise ValueError(f"Missing required recommendation config key: '{k}' in {source}")

    scale_min = float(cfg["rating_scale_min"])
    scale_max = float(cfg["rating_scale_max"])
    if scale_min >= scale_max:
        raise ValueError(
            f"Invalid rating scale: rating_scale_min ({scale_min}) must be strictly less than rating_scale_max ({scale_max})"
        )

    trigger_thresh = float(cfg["rating_trigger_threshold"])
    if not (scale_min <= trigger_thresh <= scale_max):
        raise ValueError(
            f"rating_trigger_threshold ({trigger_thresh}) is outside the scale [{scale_min}, {scale_max}]"
        )

    allergen_max_r = float(cfg["allergen_trigger_max_rating"])
    if not (scale_min <= allergen_max_r <= scale_max):
        raise ValueError(
            f"allergen_trigger_max_rating ({allergen_max_r}) is outside the scale [{scale_min}, {scale_max}]"
        )

    improvement = float(cfg["min_rating_improvement"])
    if improvement <= 0:
        raise ValueError(f"min_rating_improvement ({improvement}) must be strictly positive")

    # Invariants specified in Section 1:
    # candidate_pool_size >= max_results
    # min_stored_candidates <= candidate_pool_size
    cand_pool = int(cfg["candidate_pool_size"])
    max_res = int(cfg["max_results"])
    min_stored = int(cfg["min_stored_candidates"])

    if cand_pool < max_res:
        raise ValueError(
            f"Invalid configuration: candidate_pool_size ({cand_pool}) must be >= max_results ({max_res})"
        )

    if min_stored > cand_pool:
        raise ValueError(
            f"Invalid configuration: min_stored_candidates ({min_stored}) must be <= candidate_pool_size ({cand_pool})"
        )

    if int(cfg["live_detail_budget"]) <= 0:
        raise ValueError("live_detail_budget must be positive integer")

    if float(cfg["live_total_deadline_seconds"]) <= 0 or float(cfg["live_call_timeout_seconds"]) <= 0:
        raise ValueError("Live timeouts and deadlines must be strictly positive")

    if int(cfg["live_concurrency"]) <= 0:
        raise ValueError("live_concurrency must be positive integer")

    return cfg


def load_recommendation_config(cfg_path: Optional[str] = None) -> Dict[str, Any]:
    """Load and strictly validate recommendation settings from file."""
    config_path = cfg_path or _find_config_path()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to read recommendation config from '{config_path}': {e}")

    return validate_config(cfg, source=config_path)


RECOMMENDATION_CONFIG = load_recommendation_config()


class ListingCache:
    """In-memory cache for Tier 1 listing results with TTL per (source, subcategory, location)."""

    def __init__(self, default_ttl_hours: float = 6.0):
        self.default_ttl = default_ttl_hours * 3600.0
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

    def _make_key(self, source: str, subcategory: str, location: Optional[str]) -> str:
        s = (source or "blinkit").strip().lower()
        sub = (subcategory or "").strip().lower()
        loc = (location or "").strip().lower()
        return f"{s}:{sub}:{loc}"

    def get(self, source: str, subcategory: str, location: Optional[str], ttl_hours: Optional[float] = None) -> Optional[List[Dict[str, Any]]]:
        key = self._make_key(source, subcategory, location)
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, data = entry
        ttl_sec = (ttl_hours * 3600.0) if ttl_hours is not None else self.default_ttl
        if time.time() - ts > ttl_sec:
            self._cache.pop(key, None)
            return None
        return [dict(d) for d in data]

    def set(self, source: str, subcategory: str, location: Optional[str], data: List[Dict[str, Any]]):
        key = self._make_key(source, subcategory, location)
        self._cache[key] = (time.time(), [dict(d) for d in data])

    def clear(self):
        self._cache.clear()


class CircuitBreaker:
    """Circuit breaker for TinyFish live discovery calls."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.threshold = failure_threshold
        self.cooldown_sec = cooldown_seconds
        self.failure_count: int = 0
        self.cooldown_until: float = 0.0

    def is_tripped(self) -> bool:
        return time.time() < self.cooldown_until

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self.cooldown_until = time.time() + self.cooldown_sec
            logger.warning(
                f"Circuit breaker TRIPPED! Consecutive failures: {self.failure_count}. "
                f"Cooling down until {datetime.fromtimestamp(self.cooldown_until, tz=timezone.utc).isoformat()}"
            )

    def record_success(self):
        self.failure_count = 0
        self.cooldown_until = 0.0

    def reset(self):
        self.failure_count = 0
        self.cooldown_until = 0.0


class DailyCallTracker:
    """Tracks per-user and global daily live discovery calls."""

    def __init__(self):
        self._current_date: str = self._get_today()
        self._user_counts: Dict[str, int] = {}
        self._global_count: int = 0

    def _get_today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _check_and_reset(self):
        today = self._get_today()
        if today != self._current_date:
            self._current_date = today
            self._user_counts.clear()
            self._global_count = 0

    def can_make_call(self, user_id: Optional[str], max_user_calls: int, max_global_calls: int) -> bool:
        self._check_and_reset()
        if self._global_count >= max_global_calls:
            return False
        if user_id:
            u_count = self._user_counts.get(user_id, 0)
            if u_count >= max_user_calls:
                return False
        return True

    def record_call(self, user_id: Optional[str]):
        self._check_and_reset()
        self._global_count += 1
        if user_id:
            self._user_counts[user_id] = self._user_counts.get(user_id, 0) + 1

    def reset_counts(self):
        self._user_counts.clear()
        self._global_count = 0


class SingleFlightLocks:
    """Ensures concurrent requests for same listing or detail share in-flight tasks."""

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}

    def get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]


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
        self.data_version += 1
        self._cache.clear()


listing_cache = ListingCache()
circuit_breaker = CircuitBreaker()
daily_call_tracker = DailyCallTracker()
single_flight_locks = SingleFlightLocks()
recommendation_cache = RecommendationCache()

# In-memory background job registry
job_registry: Dict[str, Dict[str, Any]] = {}


class RecommendationService:
    """
    Upgraded 'Better alternatives' Recommendation Service with Tiered Candidate Acquisition.
    Enforces strict trigger gates, source alignment, Tier 0 stored catalogue queries,
    Tier 1 listing discovery with TTL caching and single-flight, Tier 2 metadata pre-filtering,
    and Tier 3 parallel detail extraction with strict validation, deadlines, early stop, and persistence.
    """

    def __init__(
        self,
        scoring_engine: Optional[PersonalizedScoringEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.scoring_engine = scoring_engine or PersonalizedScoringEngine()
        self.config = validate_config(config, source="custom_config") if config else RECOMMENDATION_CONFIG

    def compute_data_completeness(self, product_dict: Dict[str, Any]) -> float:
        """Calculate data completeness score (0.0 to 1.0)."""
        if not product_dict:
            return 0.0

        required_nutrients = ["kcal", "carbs_g", "sugars_g", "protein_g", "fat_g", "saturated_fat_g", "sodium_mg"]
        nutrition = product_dict.get("nutrition", {})
        if not isinstance(nutrition, dict):
            return 0.0

        score = 0.0
        nutri_present = sum(1 for n in required_nutrients if nutrition.get(n) is not None)
        score += (nutri_present / len(required_nutrients)) * 0.7

        ingredients = product_dict.get("ingredients", [])
        if isinstance(ingredients, list) and len(ingredients) > 0:
            score += 0.2

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

    def _determine_source(self, product_dict: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Determines the source_name and whether it is a live retailer source.
        Returns (source_name, is_retailer).
        """
        src = str(product_dict.get("source_name") or "").strip().lower()
        if not src:
            p_name_item = product_dict.get("product_name", {})
            u = p_name_item.get("source_url", "") if isinstance(p_name_item, dict) else ""
            if not u and product_dict.get("source_urls"):
                u = product_dict["source_urls"][0]
            u_low = str(u).lower()
            if "blinkit" in u_low:
                src = "blinkit"
            elif "zepto" in u_low:
                src = "zepto"
            elif "bigbasket" in u_low:
                src = "bigbasket"
            elif "openfoodfacts" in u_low:
                src = "open_food_facts"
            elif "user_photo" in u_low or product_dict.get("is_user_photo"):
                src = "user_photo"
            else:
                src = "unknown"

        retailer_sources = ["blinkit", "zepto", "bigbasket", "amazon", "jiomart", "dmart", "flipkart", "freshtohome"]
        is_retailer = any(r in src for r in retailer_sources)
        return src, is_retailer

    def _generate_data_driven_reasons(
        self,
        candidate_prod: Dict[str, Any],
        searched_prod: Dict[str, Any],
        user_allergens: List[str],
    ) -> List[str]:
        """Generate 1 to 3 plain-language reasons computed strictly from DATA differences."""
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

        if not reasons:
            reasons.append("Significantly better nutrient and ingredient profile")

        return reasons[:3]

    # -------------------------------------------------------------
    # TIER 0: Stored Catalogue Query
    # -------------------------------------------------------------
    async def _acquire_tier_0_candidates(
        self,
        session: Optional[AsyncSession],
        searched_id: Optional[int],
        searched_name: str,
        source_name: str,
        is_retailer: bool,
        category: str,
        subcategory: str,
        user_allergens: List[str],
        detail_cache_ttl_days: int = 30,
        min_data_completeness: float = 0.8,
        allow_cross_source_fallback: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        TIER 0: Stored catalogue query (zero cost).
        Filters: same source (if retailer and cross-source false), same subcategory (fallback to category),
        allergens excluded, complete data, fetched_at within detail_cache_ttl_days, not searched product.
        """
        eligible_candidates: List[Dict[str, Any]] = []

        if session is not None:
            try:
                now_utc = datetime.now(timezone.utc)
                cutoff_dt = now_utc - timedelta(days=detail_cache_ttl_days)

                base_filters = [
                    func.coalesce(EvidenceLog.fetched_at, EvidenceLog.created_at) >= cutoff_dt,
                    EvidenceLog.data_completeness >= min_data_completeness,
                ]

                if searched_id is not None:
                    base_filters.append(EvidenceLog.id != searched_id)
                if searched_name:
                    base_filters.append(func.lower(EvidenceLog.product_name) != searched_name.lower())

                # Same source filter
                if is_retailer and not allow_cross_source_fallback:
                    base_filters.append(func.lower(EvidenceLog.source_name) == source_name.lower())

                # Subcategory match first
                subcat_filters = list(base_filters)
                if subcategory:
                    subcat_filters.append(func.lower(EvidenceLog.subcategory) == subcategory.lower())

                stmt = select(EvidenceLog).where(and_(*subcat_filters)).order_by(EvidenceLog.created_at.desc()).limit(50)
                res = await session.execute(stmt)
                logs = res.scalars().all()

                # Fallback to broader category match if subcategory returned too few
                if len(logs) < self.config["min_stored_candidates"] and category:
                    cat_filters = list(base_filters)
                    cat_filters.append(func.lower(EvidenceLog.category) == category.lower())
                    stmt_cat = select(EvidenceLog).where(and_(*cat_filters)).order_by(EvidenceLog.created_at.desc()).limit(50)
                    res_cat = await session.execute(stmt_cat)
                    cat_logs = res_cat.scalars().all()
                    
                    seen_ids = {l.id for l in logs}
                    for cl in cat_logs:
                        if cl.id not in seen_ids:
                            logs.append(cl)
                            seen_ids.add(cl.id)

                for entry in logs:
                    prod_dict = dict(entry.product_data or {})
                    prod_dict["id"] = entry.id
                    prod_dict["source_name"] = entry.source_name or source_name
                    prod_dict["source_url"] = entry.source_url or (entry.source_urls[0] if entry.source_urls else "")
                    prod_dict["product_id_at_source"] = entry.product_id_at_source
                    prod_dict["data_completeness"] = entry.data_completeness

                    # Exclude allergens check
                    c_ing = prod_dict.get("ingredients", [])
                    c_oil = prod_dict.get("oil_listed", {})
                    c_oil_str = c_oil.get("value", "") if isinstance(c_oil, dict) else str(c_oil or "")
                    c_name_val = prod_dict.get("product_name", {}).get("value", "") if isinstance(prod_dict.get("product_name"), dict) else str(prod_dict.get("product_name") or "")

                    allergy_check = self.scoring_engine.check_allergens(
                        ingredients=c_ing,
                        oil_declared=c_oil_str,
                        user_allergens=user_allergens,
                        product_name=c_name_val,
                    )
                    if allergy_check["allergy_status"] in ["NOT SAFE FOR YOU", "CANNOT CONFIRM"]:
                        continue

                    # May contain check
                    may_contain = prod_dict.get("may_contain_allergens", []) or []
                    if any(ua.lower() in [str(m).lower() for m in may_contain] for ua in user_allergens):
                        continue

                    eligible_candidates.append(prod_dict)
            except Exception as e:
                logger.warning(f"Error querying Tier 0 stored candidates from DB: {e}")

        # In-memory reference fallback if DB empty or session None (for standalone test isolation)
        if not eligible_candidates:
            for ref_prod in CATEGORY_REFERENCE_PRODUCTS:
                ref_dict = dict(ref_prod)
                r_cat, r_sub = self._extract_category_and_subcategory(ref_dict)
                r_name = ref_dict.get("product_name", {}).get("value", "").lower()
                if searched_name and r_name == searched_name.lower():
                    continue

                same_sub = bool(subcategory and r_sub and subcategory == r_sub)
                same_cat = bool(category and r_cat and (category in r_cat or r_cat in category))
                if not (same_sub or same_cat):
                    continue

                ref_dict["source_name"] = source_name if is_retailer else "mixed"
                # Exclude allergens
                allergy_res = self.scoring_engine.check_allergens(
                    ingredients=ref_dict.get("ingredients", []),
                    oil_declared="",
                    user_allergens=user_allergens,
                    product_name=r_name,
                )
                if allergy_res["allergy_status"] == "NOT SAFE FOR YOU":
                    continue

                eligible_candidates.append(ref_dict)

        return eligible_candidates

    # -------------------------------------------------------------
    # TIER 2: Free Listing Metadata Pre-filter
    # -------------------------------------------------------------
    def _prefilter_listing_metadata(
        self,
        listing_items: List[Dict[str, Any]],
        searched_name: str,
        searched_id_at_source: Optional[str],
        subcategory: str,
        user_allergens: List[str],
        stored_candidates: List[Dict[str, Any]],
        live_detail_budget: int = 8,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        TIER 2: Pre-filter listing metadata (zero network cost).
        Drops:
        - searched product
        - already stored with fresh complete data
        - wrong subcategory items
        - out-of-stock items
        - items whose name explicitly displays a user allergen (cheap early skip)
        Ranks remainder by similarity and brand diversity; keeps top live_detail_budget.
        """
        filtered = []
        removed_counts = {
            "searched_product": 0,
            "duplicate": 0,
            "wrong_subcategory": 0,
            "out_of_stock": 0,
            "allergen_name": 0,
            "stale": 0,
        }

        stored_names = {
            (c.get("product_name", {}).get("value") if isinstance(c.get("product_name"), dict) else str(c.get("product_name") or "")).strip().lower()
            for c in stored_candidates
        }
        stored_skus = {str(c.get("product_id_at_source") or "").strip().lower() for c in stored_candidates}

        # Build cheap name allergen regex patterns (matching singular and plural, e.g. peanut/peanuts)
        allergen_patterns = []
        for ua in user_allergens:
            stem = ua.strip().lower().rstrip("s")
            if stem:
                allergen_patterns.append(re.compile(rf"\b{re.escape(stem)}s?\b", re.IGNORECASE))

        for item in listing_items:
            name_val = str(item.get("name") or "").strip()
            name_low = name_val.lower()
            sku_val = str(item.get("product_id_at_source") or "").strip().lower()

            # 1. Drop searched product
            if (searched_name and name_low == searched_name.lower()) or (searched_id_at_source and sku_val == searched_id_at_source.lower()):
                removed_counts["searched_product"] += 1
                continue

            # 2. Drop already stored
            if name_low in stored_names or (sku_val and sku_val in stored_skus):
                removed_counts["duplicate"] += 1
                continue

            # 3. Drop out of stock
            if item.get("in_stock") is False:
                removed_counts["out_of_stock"] += 1
                continue

            # 4. Drop clearly wrong subcategory items if subcategory is known
            item_sub = str(item.get("subcategory") or "").strip().lower()
            if subcategory and item_sub and subcategory.lower() not in item_sub and item_sub not in subcategory.lower():
                removed_counts["wrong_subcategory"] += 1
                continue

            # 5. Name-level allergen skip (early skip only, never final safety check)
            has_name_allergen = False
            for pat in allergen_patterns:
                if pat.search(name_low):
                    has_name_allergen = True
                    break
            if has_name_allergen:
                removed_counts["allergen_name"] += 1
                continue

            filtered.append(item)

        # Rank remainder:
        # Prioritize same subcategory, different brands
        seen_brands: Set[str] = set()
        ranked = []
        brand_overflow = []

        for item in filtered:
            b_clean = str(item.get("brand") or "").strip().lower()
            if b_clean not in seen_brands:
                seen_brands.add(b_clean)
                ranked.append(item)
            else:
                brand_overflow.append(item)

        # Combine brand-diverse first, then remainder up to live_detail_budget
        shortlisted = (ranked + brand_overflow)[:live_detail_budget]
        return shortlisted, removed_counts

    # -------------------------------------------------------------
    # TIER 3: Parallel Detail Extraction with Strict Validation
    # -------------------------------------------------------------
    async def _extract_shortlisted_details(
        self,
        shortlisted: List[Dict[str, Any]],
        source_name: str,
        location: Optional[str],
        conditions: List[str],
        user_allergens: List[str],
        p_rating: Optional[float],
        triggers: List[str],
        session: Optional[AsyncSession],
        live_concurrency: int = 4,
        call_timeout_sec: float = 12.0,
        total_deadline_sec: float = 20.0,
        max_qualifying_needed: int = 3,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        TIER 3: Parallel detail extraction for shortlisted unknown candidates.
        Extracts ingredients, nutrition, allergens, availability.
        Validates strictly (numbers parse, non-empty ingredients, determinable allergens).
        Early stops when enough qualifying candidates are assured.
        Persists valid extractions to database immediately.
        """
        extracted_candidates: List[Dict[str, Any]] = []
        semaphore = asyncio.Semaphore(live_concurrency)
        deadline = time.time() + total_deadline_sec

        metrics = {
            "attempted": len(shortlisted),
            "succeeded": 0,
            "discarded": 0,
            "early_stop": False,
            "timeout_hit": False,
        }

        qualifying_count = 0
        brand_qualifying_counts: Dict[str, int] = {}
        max_per_brand = int(self.config["max_per_brand"])

        async def _fetch_and_validate(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            url = item.get("product_url", "")
            if not url:
                return None
            async with semaphore:
                now = time.time()
                remaining = deadline - now
                if remaining <= 0:
                    metrics["timeout_hit"] = True
                    return None
                per_call_timeout = min(call_timeout_sec, remaining)
                try:
                    res = await asyncio.wait_for(
                        asyncio.to_thread(
                            tinyfish_scraper.extract_product_detail,
                            product_url=url,
                            source_name=source_name,
                            location=location,
                        ),
                        timeout=per_call_timeout,
                    )
                    return res
                except asyncio.TimeoutError:
                    metrics["timeout_hit"] = True
                    return None
                except Exception as e:
                    logger.warning(f"Detail extraction error for {url}: {e}")
                    return None

        tasks = [asyncio.create_task(_fetch_and_validate(item)) for item in shortlisted]

        for future in asyncio.as_completed(tasks):
            if qualifying_count >= max_qualifying_needed:
                metrics["early_stop"] = True
                # Cancel pending
                for t in tasks:
                    if not t.done():
                        t.cancel()
                break

            try:
                cand_data = await future
            except asyncio.CancelledError:
                break
            except Exception:
                cand_data = None

            if not cand_data:
                metrics["discarded"] += 1
                continue

            # Validate strictly
            validated = validate_extracted_product(cand_data)
            if not validated:
                metrics["discarded"] += 1
                continue

            metrics["succeeded"] += 1

            # Persist to DB immediately so next request finds in Tier 0
            if session is not None:
                await self._persist_extracted_candidate(session, validated, source_name)

            # Evaluate candidate immediately for early stopping
            c_eval = self.scoring_engine.evaluate(validated, conditions, user_allergens)
            c_rating = c_eval.get("product_rating")
            c_allergy = c_eval.get("allergy_check", {})

            if c_allergy.get("allergy_status") == "NONE FOUND" and c_rating is not None:
                b_val = str(validated.get("brand", {}).get("value") if isinstance(validated.get("brand"), dict) else (validated.get("brand") or "")).strip().lower()
                is_qualifying = False
                if "high_rating" in triggers:
                    if p_rating is not None and c_rating <= (p_rating - self.config["min_rating_improvement"]):
                        is_qualifying = True
                else:
                    if c_rating <= self.config["allergen_trigger_max_rating"]:
                        is_qualifying = True

                if is_qualifying and brand_qualifying_counts.get(b_val, 0) < max_per_brand:
                    brand_qualifying_counts[b_val] = brand_qualifying_counts.get(b_val, 0) + 1
                    qualifying_count += 1

            extracted_candidates.append(validated)

        return extracted_candidates, metrics

    async def _persist_extracted_candidate(
        self,
        session: AsyncSession,
        cand: Dict[str, Any],
        source_name: str,
    ):
        """Immediately save valid extraction to EvidenceLog."""
        try:
            p_name = cand.get("product_name", {}).get("value") if isinstance(cand.get("product_name"), dict) else str(cand.get("product_name") or "")
            b_val = cand.get("brand", {}).get("value") if isinstance(cand.get("brand"), dict) else str(cand.get("brand") or "")
            cat_val = cand.get("category", {}).get("value") if isinstance(cand.get("category"), dict) else str(cand.get("category") or "")
            subcat_val = cand.get("subcategory", {}).get("value") if isinstance(cand.get("subcategory"), dict) else str(cand.get("subcategory") or "")
            s_url = cand.get("source_url") or (cand.get("product_name", {}).get("source_url") if isinstance(cand.get("product_name"), dict) else "")
            sku = cand.get("product_id_at_source") or ""

            stmt = select(EvidenceLog).where(
                or_(
                    EvidenceLog.source_url == s_url,
                    func.lower(EvidenceLog.product_name) == p_name.lower(),
                )
            ).limit(1)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            now_dt = datetime.now(timezone.utc)
            if existing:
                existing.product_data = cand
                existing.data_completeness = cand.get("data_completeness", 1.0)
                existing.source_name = source_name
                existing.source_url = s_url
                existing.product_id_at_source = sku
                existing.fetched_at = now_dt
                await session.commit()
            else:
                new_entry = EvidenceLog(
                    query=p_name,
                    product_name=p_name,
                    brand=b_val,
                    category=cat_val,
                    subcategory=subcat_val,
                    allergens=cand.get("allergens", []),
                    may_contain_allergens=cand.get("may_contain_allergens", []),
                    data_completeness=cand.get("data_completeness", 1.0),
                    product_data=cand,
                    source_urls=[s_url] if s_url else [],
                    source_name=source_name,
                    source_url=s_url,
                    product_id_at_source=sku,
                    fetched_at=now_dt,
                )
                session.add(new_entry)
                await session.commit()
        except Exception as e:
            logger.warning(f"Error persisting extracted candidate to EvidenceLog: {e}")
            await session.rollback()

    # -------------------------------------------------------------
    # SECTION 4: Rating and Selection on Combined Pool
    # -------------------------------------------------------------
    def _rate_and_select(
        self,
        candidate_pool: List[Dict[str, Any]],
        searched_product_data: Dict[str, Any],
        p_rating: Optional[float],
        is_rating_valid: bool,
        triggers: List[str],
        has_allergen_conflict: bool,
        conditions: List[str],
        user_allergens: List[str],
        source_name: str,
        is_retailer: bool,
        allow_cross_source_fallback: bool,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Ranks candidate pool with unchanged Personalised Rating rules.
        Excludes allergens, applies brand diversity cap (max_per_brand = 2),
        and limits to max_results (3).
        """
        cfg = self.config
        p_cat, p_subcat = self._extract_category_and_subcategory(searched_product_data)
        max_results = int(cfg["max_results"])
        max_per_brand = int(cfg["max_per_brand"])

        eligible: List[Dict[str, Any]] = []
        rating_calls_count = 0

        for cand in candidate_pool:
            # Completeness check
            completeness = self.compute_data_completeness(cand)
            if completeness < cfg["min_data_completeness"]:
                continue

            # Ingredients check
            c_ingredients = cand.get("ingredients", [])
            if not c_ingredients or not isinstance(c_ingredients, list):
                continue

            c_oil_item = cand.get("oil_listed", {})
            c_oil = c_oil_item.get("value", "") if isinstance(c_oil_item, dict) else str(c_oil_item or "")

            c_name_val = cand.get("product_name", {}).get("value", "") if isinstance(cand.get("product_name"), dict) else str(cand.get("product_name") or "")

            # Hard allergen safety check
            allergy_res = self.scoring_engine.check_allergens(
                c_ingredients, c_oil, user_allergens, product_name=c_name_val
            )
            if allergy_res["allergy_status"] in ["NOT SAFE FOR YOU", "CANNOT CONFIRM"]:
                continue

            may_contain = cand.get("may_contain_allergens", []) or []
            if any(ua.lower() in [str(m).lower() for m in may_contain] for ua in user_allergens):
                continue

            # Evaluate rating
            rating_calls_count += 1
            c_eval = self.scoring_engine.evaluate(cand, conditions, user_allergens)
            c_rating = c_eval.get("product_rating")

            if (
                c_rating is None
                or not isinstance(c_rating, (int, float))
                or not (cfg["rating_scale_min"] <= c_rating <= cfg["rating_scale_max"])
            ):
                continue

            # Trigger condition test
            is_better = False
            if "high_rating" in triggers:
                if is_rating_valid and p_rating is not None and c_rating <= (p_rating - cfg["min_rating_improvement"]):
                    is_better = True
            else:
                # Allergen conflict trigger only
                if c_rating <= cfg["allergen_trigger_max_rating"]:
                    is_better = True

            if not is_better:
                continue

            c_cat, c_subcat = self._extract_category_and_subcategory(cand)
            is_subcat_match = bool(p_subcat and c_subcat and p_subcat == c_subcat)

            c_claims = cand.get("front_pack_claims", []) or []
            flagged_claims = sum(
                1 for cl in c_claims
                if str(cl.get("audit_verdict", "")).upper() in ["CONTRADICTED", "MISLEADING"]
            )

            cand_brand = cand.get("brand", {})
            b_val = cand_brand.get("value", "") if isinstance(cand_brand, dict) else str(cand_brand or "")

            reasons = self._generate_data_driven_reasons(cand, searched_product_data, user_allergens)
            rating_delta = round(p_rating - c_rating, 2) if is_rating_valid and p_rating is not None else None

            allergen_statement = (
                f"No listed {', '.join(user_allergens)} in the ingredients. Always check the pack."
                if user_allergens
                else "No listed user allergens in the ingredients. Always check the pack."
            )
            data_conf = "high" if completeness >= 0.8 else ("medium" if completeness >= 0.5 else "low")

            c_src = cand.get("source_name") or source_name
            source_label = f"Source: {c_src}" if c_src and c_src != "mixed" else "Source: mixed"

            eligible.append({
                "product_id": cand.get("id") or cand.get("evidence_log_id"),
                "brand": b_val or "Unknown Brand",
                "name": c_name_val or "Product",
                "variant": cand.get("variant") or None,
                "pack_size": cand.get("pack_size") or "100g",
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
                "source_name": c_src,
                "source_url": cand.get("source_url") or (cand.get("product_name", {}).get("source_url", "") if isinstance(cand.get("product_name"), dict) else ""),
                "source_label": source_label,
                "disclaimer": allergen_statement if has_allergen_conflict else None,
                "data_as_of": cand.get("fetched_at") or cand.get("updated_at") or "2026-10-25",
                # Sort helpers
                "_subcat_match": is_subcat_match,
                "_flagged_claims": flagged_claims,
                "_data_confidence": completeness,
            })

        # Sort: rating ascending, subcategory match, fewer flagged claims, data confidence, product name
        eligible.sort(
            key=lambda x: (
                x["personalised_rating"],
                -int(x["_subcat_match"]),
                x["_flagged_claims"],
                -x["_data_confidence"],
                x["name"].lower(),
            )
        )

        selected: List[Dict[str, Any]] = []
        brand_counts: Dict[str, int] = {}
        for alt in eligible:
            b_clean = alt["brand"].strip().lower()
            if brand_counts.get(b_clean, 0) < max_per_brand:
                brand_counts[b_clean] = brand_counts.get(b_clean, 0) + 1
                clean_alt = {k: v for k, v in alt.items() if not k.startswith("_")}
                selected.append(clean_alt)
                if len(selected) == max_results:
                    break

        return selected, rating_calls_count

    # -------------------------------------------------------------
    # Main Alternatives Entrypoint (Async, Tiered)
    # -------------------------------------------------------------
    async def get_alternatives(
        self,
        searched_product_id: Optional[int],
        searched_product_data: Optional[Dict[str, Any]],
        conditions: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None,
        location: Optional[str] = None,
        user_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for 'Better alternatives' recommendation.
        - Evaluates trigger conditions. If 'not_needed', makes ZERO live calls.
        - Queries Tier 0 stored catalogue.
        - If stored count >= min_stored_candidates: returns stored candidates immediately (zero live calls).
        - If stored count < min_stored_candidates and live discovery enabled:
          returns immediately with stored candidates, job_id, and status 'refreshing',
          running live discovery in background.
        """
        start_time = time.time()
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

        # Lookup searched product if not provided
        if not searched_product_data and searched_product_id is not None and session is not None:
            stmt = select(EvidenceLog).where(EvidenceLog.id == searched_product_id)
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if entry and entry.product_data:
                searched_product_data = entry.product_data

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

        # Medical profile condition mapping: coeliac -> gluten, lactose -> milk
        active_allergens = list(user_allergens or [])
        for cond in conditions:
            c_lower = str(cond).lower().strip()
            if any(k in c_lower for k in ["coeliac", "celiac"]):
                if not any(a.lower() in ["gluten", "wheat"] for a in active_allergens):
                    active_allergens.append("gluten")
            elif any(k in c_lower for k in ["lactose"]):
                if not any(a.lower() in ["milk", "dairy", "lactose"] for a in active_allergens):
                    active_allergens.append("milk")

        # 1. EVALUATE TRIGGER GATE
        p_eval = self.scoring_engine.evaluate(
            product_data=searched_product_data,
            selected_conditions=conditions,
            user_allergens=active_allergens,
        )
        p_rating = p_eval.get("product_rating")
        allergy_check = p_eval.get("allergy_check", {})
        allergy_status = allergy_check.get("allergy_status", "NONE FOUND")
        conflicting_allergens = allergy_check.get("found_allergens", [])
        has_allergen_conflict = (allergy_status == "NOT SAFE FOR YOU")

        is_rating_valid = (
            p_rating is not None
            and isinstance(p_rating, (int, float))
            and cfg["rating_scale_min"] <= p_rating <= cfg["rating_scale_max"]
        )

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
        p_name_item = searched_product_data.get("product_name", {})
        p_name_val = str(p_name_item.get("value", "") if isinstance(p_name_item, dict) else (p_name_item or "")).strip()

        p_brand_item = searched_product_data.get("brand", {})
        p_brand_val = p_brand_item.get("value", "") if isinstance(p_brand_item, dict) else str(p_brand_item or "")

        source_name, is_retailer = self._determine_source(searched_product_data)
        source_label = f"Source: {source_name}" if is_retailer else "Source: mixed"

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
            "source_name": source_name,
            "source_label": source_label,
        }

        # Invariant: If neither trigger fired: return "not_needed" with ZERO live calls.
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
        # TIER 0: Query Stored Catalogue
        # -------------------------------------------------------------
        stored_candidates = await self._acquire_tier_0_candidates(
            session=session,
            searched_id=searched_product_id,
            searched_name=p_name_val,
            source_name=source_name,
            is_retailer=is_retailer,
            category=p_cat_val,
            subcategory=p_subcat_val,
            user_allergens=active_allergens,
            detail_cache_ttl_days=int(cfg["detail_cache_ttl_days"]),
            min_data_completeness=float(cfg["min_data_completeness"]),
            allow_cross_source_fallback=bool(cfg["allow_cross_source_fallback"]),
        )

        stored_eligible_count = len(stored_candidates)
        min_stored = int(cfg["min_stored_candidates"])

        # Rate stored candidates to see if we already qualify
        stored_selected, rating_calls = self._rate_and_select(
            candidate_pool=stored_candidates,
            searched_product_data=searched_product_data,
            p_rating=p_rating,
            is_rating_valid=is_rating_valid,
            triggers=triggers,
            has_allergen_conflict=has_allergen_conflict,
            conditions=conditions,
            user_allergens=active_allergens,
            source_name=source_name,
            is_retailer=is_retailer,
            allow_cross_source_fallback=bool(cfg["allow_cross_source_fallback"]),
        )

        disclaimer_text = (
            "Ratings are computed for your profile; lower is better. "
            "Always check physical packaging for current ingredients and allergen warnings."
        )

        # Invariant: If stored eligible count >= min_stored_candidates: STOP! Zero live calls.
        if stored_eligible_count >= min_stored or not cfg.get("live_discovery_enabled", True) or not is_retailer:
            status_val = "ok" if stored_selected else "none_found"
            msg = (
                f"Found {len(stored_selected)} better alternative(s) for your profile on {source_name}."
                if stored_selected
                else f"no allergen-safe products with a better rating found on {source_name} in this category"
            )
            res = {
                "status": status_val,
                "trigger": triggers,
                "trigger_reason": trigger_reason,
                "searched_product": searched_product_summary,
                "alternatives": stored_selected,
                "source_label": source_label,
                "message": msg,
                "disclaimer": disclaimer_text,
                "live_metrics": {
                    "source_name": source_name,
                    "location_used": location or "default",
                    "stored_eligible_count": stored_eligible_count,
                    "live_discovery_ran": False,
                    "reason_live_skipped": "stored_pool_sufficient" if stored_eligible_count >= min_stored else ("live_disabled" if not cfg.get("live_discovery_enabled") else "non_retailer_source"),
                    "listing_cache_hit": False,
                    "listing_size": 0,
                    "detail_calls_attempted": 0,
                    "detail_calls_succeeded": 0,
                    "detail_calls_discarded": 0,
                    "rating_calls_made": rating_calls,
                    "results_returned": len(stored_selected),
                    "early_stop_triggered": False,
                    "timeout_hit": False,
                    "elapsed_seconds": round(time.time() - start_time, 3),
                }
            }
            if searched_product_id is not None:
                recommendation_cache.set(searched_product_id, conditions, user_allergens, res)
            return res

        # -------------------------------------------------------------
        # LIVE TOP-UP NEEDED (stored_eligible_count < min_stored_candidates)
        # -------------------------------------------------------------
        # Check quota and circuit breaker
        can_call = daily_call_tracker.can_make_call(
            user_id=user_id,
            max_user_calls=int(cfg["max_live_calls_per_user_per_day"]),
            max_global_calls=int(cfg["max_live_calls_global_per_day"]),
        )
        is_breaker_open = circuit_breaker.is_tripped()

        if not can_call or is_breaker_open:
            reason_skipped = "live search limit reached" if not can_call else "circuit breaker active"
            status_val = "ok" if stored_selected else "none_found"
            msg = (
                f"Found {len(stored_selected)} stored alternative(s) ({reason_skipped})."
                if stored_selected
                else f"no allergen-safe products found ({reason_skipped})."
            )
            return {
                "status": status_val,
                "trigger": triggers,
                "trigger_reason": trigger_reason,
                "searched_product": searched_product_summary,
                "alternatives": stored_selected,
                "source_label": source_label,
                "message": msg,
                "disclaimer": disclaimer_text,
                "live_metrics": {
                    "source_name": source_name,
                    "location_used": location or "default",
                    "stored_eligible_count": stored_eligible_count,
                    "live_discovery_ran": False,
                    "reason_live_skipped": reason_skipped,
                    "rating_calls_made": rating_calls,
                    "results_returned": len(stored_selected),
                    "elapsed_seconds": round(time.time() - start_time, 3),
                }
            }

        # Section 5: Asynchronous delivery.
        # Main search result is never blocked. Return stored results immediately with job_id and status "refreshing".
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        initial_job_data = {
            "status": "refreshing",
            "job_id": job_id,
            "trigger": triggers,
            "trigger_reason": trigger_reason,
            "searched_product": searched_product_summary,
            "alternatives": list(stored_selected),
            "source_label": source_label,
            "message": "Checking live retailer options for better alternatives...",
            "disclaimer": disclaimer_text,
            "live_metrics": {
                "source_name": source_name,
                "location_used": location or "default",
                "stored_eligible_count": stored_eligible_count,
                "live_discovery_ran": True,
                "rating_calls_made": rating_calls,
                "results_returned": len(stored_selected),
                "elapsed_seconds": round(time.time() - start_time, 3),
            }
        }
        job_registry[job_id] = initial_job_data

        # Fire background task
        asyncio.create_task(
            self._execute_live_pool_acquisition(
                job_id=job_id,
                searched_product_data=searched_product_data,
                searched_product_summary=searched_product_summary,
                stored_candidates=stored_candidates,
                stored_selected=stored_selected,
                source_name=source_name,
                is_retailer=is_retailer,
                category=p_cat_val,
                subcategory=p_subcat_val,
                location=location,
                user_id=user_id,
                conditions=conditions,
                user_allergens=active_allergens,
                p_rating=p_rating,
                is_rating_valid=is_rating_valid,
                triggers=triggers,
                has_allergen_conflict=has_allergen_conflict,
                session=session,
            )
        )

        return initial_job_data

    # -------------------------------------------------------------
    # Background Live Acquisition Worker
    # -------------------------------------------------------------
    async def _execute_live_pool_acquisition(
        self,
        job_id: str,
        searched_product_data: Dict[str, Any],
        searched_product_summary: Dict[str, Any],
        stored_candidates: List[Dict[str, Any]],
        stored_selected: List[Dict[str, Any]],
        source_name: str,
        is_retailer: bool,
        category: str,
        subcategory: str,
        location: Optional[str],
        user_id: Optional[str],
        conditions: List[str],
        user_allergens: List[str],
        p_rating: Optional[float],
        is_rating_valid: bool,
        triggers: List[str],
        has_allergen_conflict: bool,
        session: Optional[AsyncSession],
    ):
        start_live = time.time()
        cfg = self.config
        initial_job_data = job_registry.get(job_id, {})
        subcat = subcategory or category or "Packaged Food"
        live_detail_budget = int(cfg["live_detail_budget"])

        # Track metrics
        metrics = {
            "source_name": source_name,
            "location_used": location or "default",
            "stored_eligible_count": len(stored_candidates),
            "live_discovery_ran": True,
            "listing_cache_hit": False,
            "listing_size": 0,
            "candidates_removed": {},
            "detail_calls_attempted": 0,
            "detail_calls_succeeded": 0,
            "detail_calls_discarded": 0,
            "live_time_seconds": 0.0,
            "credits_used": 0,
            "pool_size_used": 0,
            "rating_calls_made": 0,
            "results_returned": len(stored_selected),
            "early_stop_triggered": False,
            "timeout_hit": False,
        }

        try:
            # 1. TIER 1: Listing Discovery (Single-flight + TTL Cache)
            cached_listing = listing_cache.get(source_name, subcat, location, ttl_hours=float(cfg["listing_cache_ttl_hours"]))
            listing_items = []
            if cached_listing is not None:
                metrics["listing_cache_hit"] = True
                listing_items = cached_listing
            else:
                # Single-flight lock per (source, subcategory, location)
                lock_key = f"listing:{source_name}:{subcat}:{location or ''}"
                flight_lock = single_flight_locks.get_lock(lock_key)
                async with flight_lock:
                    # Double check cache
                    cached_listing2 = listing_cache.get(source_name, subcat, location, ttl_hours=float(cfg["listing_cache_ttl_hours"]))
                    if cached_listing2 is not None:
                        metrics["listing_cache_hit"] = True
                        listing_items = cached_listing2
                    else:
                        # Record live credit
                        daily_call_tracker.record_call(user_id)
                        metrics["credits_used"] += 1
                        try:
                            listing_items = await asyncio.to_thread(
                                tinyfish_scraper.discover_category_listings,
                                source=source_name,
                                subcategory=subcat,
                                location=location,
                                limit=int(cfg["candidate_pool_size"]),
                            )
                            listing_cache.set(source_name, subcat, location, listing_items)
                            circuit_breaker.record_success()
                        except Exception as e:
                            logger.warning(f"Error in Tier 1 discover_category_listings: {e}")
                            circuit_breaker.record_failure()
                            listing_items = []

            metrics["listing_size"] = len(listing_items)

            # 2. TIER 2: Free Listing Pre-filter
            p_name = searched_product_summary.get("name", "")
            p_sku = searched_product_data.get("product_id_at_source")
            shortlisted, removed_counts = self._prefilter_listing_metadata(
                listing_items=listing_items,
                searched_name=p_name,
                searched_id_at_source=p_sku,
                subcategory=subcat,
                user_allergens=user_allergens,
                stored_candidates=stored_candidates,
                live_detail_budget=live_detail_budget,
            )
            metrics["candidates_removed"] = removed_counts

            # 3. TIER 3: Parallel Detail Extraction
            metrics["detail_calls_attempted"] = len(shortlisted)
            extracted_items, extract_metrics = await self._extract_shortlisted_details(
                shortlisted=shortlisted,
                source_name=source_name,
                location=location,
                conditions=conditions,
                user_allergens=user_allergens,
                p_rating=p_rating,
                triggers=triggers,
                session=session,
                live_concurrency=int(cfg["live_concurrency"]),
                call_timeout_sec=float(cfg["live_call_timeout_seconds"]),
                total_deadline_sec=float(cfg["live_total_deadline_seconds"]),
                max_qualifying_needed=int(cfg["max_results"]),
            )

            metrics["detail_calls_succeeded"] = extract_metrics["succeeded"]
            metrics["detail_calls_discarded"] = extract_metrics["discarded"]
            metrics["early_stop_triggered"] = extract_metrics["early_stop"]
            metrics["timeout_hit"] = extract_metrics["timeout_hit"]
            metrics["credits_used"] += extract_metrics["succeeded"] + extract_metrics["discarded"]

            # Combined Pool = stored eligible candidates + newly extracted candidates
            # Ordered (same subcategory first, higher data confidence, product name), LIMIT candidate_pool_size
            combined_pool = list(stored_candidates) + list(extracted_items)
            p_sub_clean = (subcategory or "").strip().lower()

            def pool_sort_key(c):
                c_sub = str(c.get("subcategory", {}).get("value") if isinstance(c.get("subcategory"), dict) else (c.get("subcategory") or "")).strip().lower()
                is_sub = 1 if p_sub_clean and c_sub == p_sub_clean else 0
                conf = float(c.get("data_completeness") or 0.0)
                n = str(c.get("product_name", {}).get("value") if isinstance(c.get("product_name"), dict) else (c.get("product_name") or "")).strip().lower()
                return (-is_sub, -conf, n)

            combined_pool.sort(key=pool_sort_key)
            pool_trimmed = combined_pool[:int(cfg["candidate_pool_size"])]
            metrics["pool_size_used"] = len(pool_trimmed)

            # Section 4: Rating and selection on pool
            final_selected, r_calls = self._rate_and_select(
                candidate_pool=pool_trimmed,
                searched_product_data=searched_product_data,
                p_rating=p_rating,
                is_rating_valid=is_rating_valid,
                triggers=triggers,
                has_allergen_conflict=has_allergen_conflict,
                conditions=conditions,
                user_allergens=user_allergens,
                source_name=source_name,
                is_retailer=is_retailer,
                allow_cross_source_fallback=bool(cfg["allow_cross_source_fallback"]),
            )
            metrics["rating_calls_made"] = r_calls

            # Progressive delivery: preserve order of cards already shown!
            # Cards already shown in initial response are never removed or reordered.
            merged_selected: List[Dict[str, Any]] = list(stored_selected)
            shown_ids = {alt.get("product_id") or alt.get("name") for alt in stored_selected}
            for alt in final_selected:
                ident = alt.get("product_id") or alt.get("name")
                if ident not in shown_ids and len(merged_selected) < int(cfg["max_results"]):
                    merged_selected.append(alt)
                    shown_ids.add(ident)

            metrics["results_returned"] = len(merged_selected)
            metrics["live_time_seconds"] = round(time.time() - start_live, 3)

            # Structured logging of request counts
            logger.info(
                f"LIVE_POOL_REQUEST: source_name={source_name}, location={metrics['location_used']}, "
                f"stored_count={metrics['stored_eligible_count']}, listing_cache_hit={metrics['listing_cache_hit']}, "
                f"listing_size={metrics['listing_size']}, detail_attempted={metrics['detail_calls_attempted']}, "
                f"detail_succeeded={metrics['detail_calls_succeeded']}, detail_discarded={metrics['detail_calls_discarded']}, "
                f"pool_size={metrics['pool_size_used']}, rating_calls={metrics['rating_calls_made']}, "
                f"results_returned={metrics['results_returned']}, early_stop={metrics['early_stop_triggered']}, "
                f"timeout_hit={metrics['timeout_hit']}, elapsed_sec={metrics['live_time_seconds']}"
            )

            # Determine final status
            if extract_metrics["timeout_hit"]:
                final_status = "partial_timeout"
                msg = f"Live scan timed out after {cfg['live_total_deadline_seconds']}s; showing {len(merged_selected)} qualified alternative(s)."
            elif merged_selected:
                final_status = "ok"
                msg = f"Found {len(merged_selected)} better alternative(s) on {source_name}."
            else:
                final_status = "none_found"
                msg = f"no allergen-safe products with a better rating found on {source_name} in this category"

            # Update job state
            job_registry[job_id] = {
                "status": final_status,
                "job_id": job_id,
                "trigger": triggers,
                "trigger_reason": initial_job_data.get("trigger_reason"),
                "searched_product": searched_product_summary,
                "alternatives": merged_selected,
                "source_label": initial_job_data.get("source_label"),
                "message": msg,
                "disclaimer": initial_job_data.get("disclaimer"),
                "live_metrics": metrics,
            }

        except Exception as e:
            logger.exception(f"Unexpected error in _execute_live_pool_acquisition for job {job_id}: {e}")
            job_registry[job_id] = {
                "status": "ok" if stored_selected else "none_found",
                "job_id": job_id,
                "trigger": triggers,
                "trigger_reason": initial_job_data.get("trigger_reason"),
                "searched_product": searched_product_summary,
                "alternatives": stored_selected,
                "source_label": initial_job_data.get("source_label"),
                "message": "Live search encountered an error; showing stored alternatives.",
                "disclaimer": initial_job_data.get("disclaimer"),
                "live_metrics": metrics,
            }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve progress or final results of a live pool acquisition job."""
        return job_registry.get(job_id)


# Global recommendation service singleton
recommendation_service = RecommendationService()
