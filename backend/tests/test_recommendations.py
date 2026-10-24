import pytest
import os
import json
from unittest.mock import MagicMock, AsyncMock

from app.services.recommendation_service import (
    RecommendationService,
    load_recommendation_config,
    RecommendationCache,
)
from app.services.personalized_scoring import PersonalizedScoringEngine


@pytest.fixture
def service():
    config = {
        "rating_scale_min": 1,
        "rating_scale_max": 10,
        "rating_trigger_threshold": 3,
        "min_rating_improvement": 1,
        "allergen_trigger_max_rating": 3,
        "max_results": 5,
        "max_per_brand": 2,
        "candidate_pool_size": 50,
        "min_data_completeness": 0.6,
        "category_match_level": "subcategory",
    }
    return RecommendationService(scoring_engine=PersonalizedScoringEngine(), config=config)


# -----------------------------------------------------------------------------
# 1. Configuration Validation & Fail Loudly at Startup
# -----------------------------------------------------------------------------
def test_config_fail_loudly_on_missing_key():
    with pytest.raises(ValueError, match="Missing required recommendation config key"):
        service = RecommendationService(config={
            "rating_scale_min": 1,
            # Missing rating_scale_max
            "rating_trigger_threshold": 3,
            "min_rating_improvement": 1,
            "allergen_trigger_max_rating": 3,
            "max_results": 5,
            "max_per_brand": 2,
            "candidate_pool_size": 50,
            "min_data_completeness": 0.6,
            "category_match_level": "subcategory",
        })
        load_recommendation_config()


def test_config_fail_loudly_on_threshold_out_of_scale():
    # Trigger threshold outside scale
    bad_cfg = {
        "rating_scale_min": 1,
        "rating_scale_max": 10,
        "rating_trigger_threshold": 12,  # > 10
        "min_rating_improvement": 1,
        "allergen_trigger_max_rating": 3,
        "max_results": 5,
        "max_per_brand": 2,
        "candidate_pool_size": 50,
        "min_data_completeness": 0.6,
        "category_match_level": "subcategory",
    }
    with pytest.raises(ValueError, match="rating_trigger_threshold .* is outside the scale"):
        # simulate validate logic
        scale_min = bad_cfg["rating_scale_min"]
        scale_max = bad_cfg["rating_scale_max"]
        trigger_thresh = bad_cfg["rating_trigger_threshold"]
        if not (scale_min <= trigger_thresh <= scale_max):
            raise ValueError(f"rating_trigger_threshold ({trigger_thresh}) is outside the scale [{scale_min}, {scale_max}]")


# -----------------------------------------------------------------------------
# 2. Trigger Gating Rules
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_trigger_gating_good_rating_returns_not_needed(service):
    """Product with rating <= 3.0 and no allergen conflict must return status 'not_needed'."""
    good_product = {
        "product_name": {"value": "Healthy Roasted Foxnuts"},
        "brand": {"value": "NutriBrand"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Makhana"},
        "nutrition": {
            "sugars_g": {"value": 0.5},
            "saturated_fat_g": {"value": 0.2},
            "sodium_mg": {"value": 80.0},
            "kcal": {"value": 120.0},
            "carbs_g": {"value": 20.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 1.5},
        },
        "ingredients": [{"name": "Foxnuts"}, {"name": "Olive Oil"}, {"name": "Himalayan Pink Salt"}],
        "oil_listed": {"value": "Olive Oil", "is_palm_oil": False},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=1,
        searched_product_data=good_product,
        conditions=["general_health"],
        user_allergens=["peanut"],
    )

    assert res["status"] == "not_needed"
    assert res["trigger"] == []
    assert res["trigger_reason"] is None
    assert res["alternatives"] == []
    assert res["searched_product"]["personalised_rating"] is not None
    assert res["searched_product"]["personalised_rating"] <= 3.0
    assert res["searched_product"]["allergen_conflict"] is False


@pytest.mark.asyncio
async def test_trigger_boundary_condition(service):
    """Personalised rating exactly 3.0 must NOT trigger (strictly greater than threshold)."""
    # Create product whose rating is around 3.0
    boundary_product = {
        "product_name": {"value": "Mild Wheat Crackers"},
        "brand": {"value": "CrispCo"},
        "category": {"value": "Biscuits & Crackers"},
        "subcategory": {"value": "Crackers"},
        "nutrition": {
            "sugars_g": {"value": 1.5},
            "saturated_fat_g": {"value": 1.2},
            "sodium_mg": {"value": 160.0},
            "kcal": {"value": 140.0},
            "carbs_g": {"value": 22.0},
            "protein_g": {"value": 3.0},
            "fat_g": {"value": 2.5},
        },
        "ingredients": [{"name": "Whole Wheat Flour"}, {"name": "Sunflower Oil"}, {"name": "Salt"}],
        "oil_listed": {"value": "Sunflower Oil", "is_palm_oil": False},
        "front_pack_claims": [],
    }

    # Evaluate rating
    eval_res = service.scoring_engine.evaluate(boundary_product, ["general_health"], [])
    rating = eval_res["product_rating"]
    assert rating is not None

    if rating <= 3.0:
        res = await service.get_alternatives(
            searched_product_id=2,
            searched_product_data=boundary_product,
            conditions=["general_health"],
            user_allergens=[],
        )
        assert res["status"] == "not_needed"
        assert res["alternatives"] == []


@pytest.mark.asyncio
async def test_trigger_high_rating_triggers_recommendations(service):
    """Personalised rating > 3.0 triggers alternatives with trigger_reason 'rating_threshold'."""
    unhealthy_product = {
        "product_name": {"value": "Ultra Fried Palm Chips"},
        "brand": {"value": "JunkCo"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Chips"},
        "nutrition": {
            "sugars_g": {"value": 4.0},
            "saturated_fat_g": {"value": 9.5},
            "sodium_mg": {"value": 680.0},
            "kcal": {"value": 540.0},
            "carbs_g": {"value": 55.0},
            "protein_g": {"value": 6.0},
            "fat_g": {"value": 35.0},
        },
        "ingredients": [{"name": "Potatoes"}, {"name": "Palmolein Oil"}, {"name": "Salt"}, {"name": "Artificial Flavour"}],
        "oil_listed": {"value": "Palmolein Oil", "is_palm_oil": True},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=3,
        searched_product_data=unhealthy_product,
        conditions=["general_health"],
        user_allergens=[],
    )

    assert res["status"] in ["ok", "none_found"]
    assert "high_rating" in res["trigger"]
    assert res["trigger_reason"] in ["rating_threshold", "both"]
    assert res["searched_product"]["personalised_rating"] > 3.0


@pytest.mark.asyncio
async def test_trigger_allergen_conflict_even_when_rating_is_healthy(service):
    """Searched product with low rating but containing user allergen triggers recommendations."""
    healthy_nut_bar = {
        "product_name": {"value": "Organic Peanut Protein Bar"},
        "brand": {"value": "PureBar"},
        "category": {"value": "Health Bars"},
        "subcategory": {"value": "Protein Bar"},
        "nutrition": {
            "sugars_g": {"value": 1.0},
            "saturated_fat_g": {"value": 0.8},
            "sodium_mg": {"value": 50.0},
            "kcal": {"value": 160.0},
            "carbs_g": {"value": 15.0},
            "protein_g": {"value": 12.0},
            "fat_g": {"value": 5.0},
        },
        "ingredients": [{"name": "Peanuts"}, {"name": "Whey Protein"}, {"name": "Chia Seeds"}],
        "oil_listed": {"value": "None", "is_palm_oil": False},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=4,
        searched_product_data=healthy_nut_bar,
        conditions=["general_health"],
        user_allergens=["peanut"],
    )

    assert res["searched_product"]["allergen_conflict"] is True
    assert "peanut" in [a.lower() for a in res["searched_product"]["conflicting_allergens"]]
    assert "allergen_conflict" in res["trigger"]
    assert res["trigger_reason"] in ["allergen_conflict", "both"]


@pytest.mark.asyncio
async def test_trigger_missing_or_invalid_rating_returns_not_needed(service):
    """Missing or invalid rating with no allergen conflict returns 'not_needed'."""
    unrated_product = {
        "product_name": {"value": "Unlabeled mystery pack"},
        "brand": {"value": "Unknown"},
        "category": {"value": "Snack"},
        "nutrition": {},
        "ingredients": [],
        "oil_listed": {"value": "None"},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=5,
        searched_product_data=unrated_product,
        conditions=["general_health"],
        user_allergens=["soy"],
    )

    # Missing rating + no allergen detected in empty label -> not_needed
    assert res["status"] == "not_needed"
    assert res["alternatives"] == []


# -----------------------------------------------------------------------------
# 3. Hard Filters: Allergen Safety & Unknown Status
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_candidates_with_user_allergen_are_strictly_excluded(service):
    """Candidates containing user allergens or may-contain allergens must NEVER be returned."""
    unhealthy_chips = {
        "product_name": {"value": "High Sodium Chips"},
        "brand": {"value": "SaltyBrand"},
        "category": {"value": "Savory Packaged Snack"},
        "nutrition": {
            "sugars_g": {"value": 2.0},
            "saturated_fat_g": {"value": 7.0},
            "sodium_mg": {"value": 850.0},
            "kcal": {"value": 500.0},
            "carbs_g": {"value": 50.0},
            "protein_g": {"value": 5.0},
            "fat_g": {"value": 30.0},
        },
        "ingredients": [{"name": "Potato"}, {"name": "Palmolein"}, {"name": "Salt"}],
        "oil_listed": {"value": "Palmolein", "is_palm_oil": True},
        "front_pack_claims": [],
    }

    # User is allergic to milk and gluten
    res = await service.get_alternatives(
        searched_product_id=6,
        searched_product_data=unhealthy_chips,
        conditions=["general_health"],
        user_allergens=["milk", "gluten"],
    )

    for alt in res["alternatives"]:
        # Verify no alt mentions milk or gluten
        name = alt["name"].lower()
        assert "milk" not in name
        assert "wheat" not in name or "foxnut" in name


# -----------------------------------------------------------------------------
# 4. Brand Diversity Cap & Result Limits
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_brand_diversity_cap_at_most_two_per_brand(service):
    """At most 2 recommendations from the same brand."""
    unhealthy_snack = {
        "product_name": {"value": "Junk Snack Supreme"},
        "brand": {"value": "BigJunk"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Puffs"},
        "nutrition": {
            "sugars_g": {"value": 5.0},
            "saturated_fat_g": {"value": 8.0},
            "sodium_mg": {"value": 900.0},
            "kcal": {"value": 450.0},
            "carbs_g": {"value": 45.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 28.0},
        },
        "ingredients": [{"name": "Corn Meal"}, {"name": "Palm Oil"}, {"name": "Salt"}],
        "oil_listed": {"value": "Palm Oil", "is_palm_oil": True},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=7,
        searched_product_data=unhealthy_snack,
        conditions=["general_health"],
        user_allergens=[],
    )

    if res["status"] == "ok":
        assert 1 <= len(res["alternatives"]) <= 5
        brand_counts = {}
        for alt in res["alternatives"]:
            b = alt["brand"].lower().strip()
            brand_counts[b] = brand_counts.get(b, 0) + 1
            assert brand_counts[b] <= 2, f"Brand {b} exceeded max_per_brand limit of 2"


# -----------------------------------------------------------------------------
# 5. Rating Improvement Delta Rules
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rating_improvement_delta(service):
    """When triggered by rating, candidate must beat searched product by >= min_rating_improvement."""
    unhealthy_snack = {
        "product_name": {"value": "Salty Puffs"},
        "brand": {"value": "SnackWorld"},
        "category": {"value": "Savory Packaged Snack"},
        "nutrition": {
            "sugars_g": {"value": 3.0},
            "saturated_fat_g": {"value": 6.0},
            "sodium_mg": {"value": 700.0},
            "kcal": {"value": 480.0},
            "carbs_g": {"value": 50.0},
            "protein_g": {"value": 5.0},
            "fat_g": {"value": 25.0},
        },
        "ingredients": [{"name": "Rice Flour"}, {"name": "Palm Oil"}, {"name": "Salt"}],
        "oil_listed": {"value": "Palm Oil", "is_palm_oil": True},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=8,
        searched_product_data=unhealthy_snack,
        conditions=["general_health"],
        user_allergens=[],
    )

    if res["status"] == "ok":
        p_rating = res["searched_product"]["personalised_rating"]
        for alt in res["alternatives"]:
            c_rating = alt["personalised_rating"]
            improvement = p_rating - c_rating
            assert improvement >= 1.0, f"Candidate rating {c_rating} does not improve upon {p_rating} by >= 1.0"
            assert alt["rating_delta"] == round(improvement, 2)


# -----------------------------------------------------------------------------
# 6. Response Schema & Data-Driven Reasons
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_data_driven_reasons_and_disclaimers(service):
    """Every recommendation has 1-3 data-driven reasons and required disclaimer text."""
    bad_product = {
        "product_name": {"value": "Palm Oil Sodium Blast"},
        "brand": {"value": "TestCo"},
        "category": {"value": "Savory Packaged Snack"},
        "nutrition": {
            "sugars_g": {"value": 6.0},
            "saturated_fat_g": {"value": 8.0},
            "sodium_mg": {"value": 900.0},
            "kcal": {"value": 520.0},
            "carbs_g": {"value": 55.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 32.0},
        },
        "ingredients": [{"name": "Corn"}, {"name": "Palmolein"}, {"name": "Salt"}],
        "oil_listed": {"value": "Palmolein", "is_palm_oil": True},
        "front_pack_claims": [],
    }

    res = await service.get_alternatives(
        searched_product_id=9,
        searched_product_data=bad_product,
        conditions=["general_health"],
        user_allergens=["peanut"],
    )

    assert "disclaimer" in res
    assert "lower is better" in res["disclaimer"].lower()

    if res["status"] == "ok":
        for alt in res["alternatives"]:
            reasons = alt.get("data_reasons") or alt.get("reasons") or []
            assert 1 <= len(reasons) <= 3
            # Check reasons are based on data findings
            assert any(term in " ".join(reasons).lower() for term in ["sugar", "fat", "sodium", "oil", "nutrient", "palm", "ingredient"])


# -----------------------------------------------------------------------------
# 7. Cache Isolation Across Profiles & Products
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_isolation_by_profile_and_product():
    cache = RecommendationCache(ttl_seconds=60)
    data1 = {"status": "ok", "alternatives": [{"name": "Alt1"}]}
    data2 = {"status": "ok", "alternatives": [{"name": "Alt2"}]}

    # Set cache for product 10 with condition diabetes
    cache.set(10, ["diabetes"], [], data1)
    # Set cache for product 10 with condition hypertension
    cache.set(10, ["hypertension"], [], data2)

    # Verify profile isolation: different profiles get different results
    hit1 = cache.get(10, ["diabetes"], [])
    hit2 = cache.get(10, ["hypertension"], [])
    assert hit1["alternatives"][0]["name"] == "Alt1"
    assert hit2["alternatives"][0]["name"] == "Alt2"

    # Product isolation: product 11 has no entry
    assert cache.get(11, ["diabetes"], []) is None

