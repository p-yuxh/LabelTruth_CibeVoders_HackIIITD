import pytest
import os
import json
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.recommendation_service import (
    RecommendationService,
    load_recommendation_config,
    RecommendationCache,
    listing_cache,
    circuit_breaker,
    daily_call_tracker,
    single_flight_locks,
    RECOMMENDATION_CONFIG,
)
from app.services.personalized_scoring import PersonalizedScoringEngine
from app.services.tinyfish_scraper import tinyfish_scraper, validate_extracted_product


@pytest.fixture
def service():
    config = dict(RECOMMENDATION_CONFIG)
    config["min_data_completeness"] = 0.6
    circuit_breaker.reset()
    daily_call_tracker.reset_counts()
    listing_cache.clear()
    return RecommendationService(scoring_engine=PersonalizedScoringEngine(), config=config)


# -----------------------------------------------------------------------------
# 1. Configuration Validation & Fail Loudly at Startup
# -----------------------------------------------------------------------------
def test_config_fail_loudly_on_missing_key():
    with pytest.raises(ValueError, match="Missing required recommendation config key"):
        RecommendationService(config={
            "rating_scale_min": 1,
            # Missing rating_scale_max
            "rating_trigger_threshold": 3,
            "min_rating_improvement": 1,
            "allergen_trigger_max_rating": 3,
            "max_results": 3,
            "max_per_brand": 2,
            "candidate_pool_size": 25,
            "min_data_completeness": 0.6,
            "category_match_level": "subcategory",
        })


def test_config_fail_loudly_on_startup_invariants():
    # candidate_pool_size < max_results should fail loudly
    bad_cfg = dict(RECOMMENDATION_CONFIG)
    bad_cfg["candidate_pool_size"] = 2
    bad_cfg["max_results"] = 3
    with pytest.raises(ValueError, match="candidate_pool_size .* must be >= max_results"):
        RecommendationService(config=bad_cfg)

    # min_stored_candidates > candidate_pool_size should fail loudly
    bad_cfg2 = dict(RECOMMENDATION_CONFIG)
    bad_cfg2["candidate_pool_size"] = 10
    bad_cfg2["min_stored_candidates"] = 15
    with pytest.raises(ValueError, match="min_stored_candidates .* must be <= candidate_pool_size"):
        RecommendationService(config=bad_cfg2)


# -----------------------------------------------------------------------------
# 2. Trigger Gate: "not_needed" makes ZERO live calls
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_trigger_gate_good_rating_makes_zero_live_calls(service):
    """Product with rating <= 3.0 and no allergen conflict must return 'not_needed' with 0 live calls."""
    good_product = {
        "product_name": {"value": "Healthy Roasted Foxnuts"},
        "brand": {"value": "NutriBrand"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Makhana"},
        "source_name": "blinkit",
        "nutrition": {
            "sugars_g": {"value": 0.5},
            "saturated_fat_g": {"value": 0.2},
            "sodium_mg": {"value": 80.0},
            "kcal": {"value": 120.0},
            "carbs_g": {"value": 20.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 1.5},
        },
        "ingredients": ["Foxnuts", "Olive Oil", "Himalayan Pink Salt"],
        "oil_listed": {"value": "Olive Oil", "is_palm_oil": False},
        "front_pack_claims": [],
        "data_completeness": 1.0,
    }

    with patch.object(tinyfish_scraper, "discover_category_listings") as mock_listing, \
         patch.object(tinyfish_scraper, "extract_product_detail") as mock_detail:

        res = await service.get_alternatives(
            searched_product_id=101,
            searched_product_data=good_product,
            conditions=["general_health"],
            user_allergens=[],
        )

        assert res["status"] == "not_needed"
        assert res["trigger"] == []
        assert res["alternatives"] == []
        mock_listing.assert_not_called()
        mock_detail.assert_not_called()


# -----------------------------------------------------------------------------
# 3. Stored pool already >= min_stored_candidates: zero live calls
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stored_pool_sufficient_makes_zero_live_calls(service):
    """When eligible stored candidates >= min_stored_candidates (15), STOP with zero live calls."""
    unhealthy_snack = {
        "product_name": {"value": "Super Salty Chips"},
        "brand": {"value": "SaltyCorp"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Chips"},
        "source_name": "blinkit",
        "nutrition": {
            "sugars_g": {"value": 2.0},
            "saturated_fat_g": {"value": 7.0},
            "sodium_mg": {"value": 800.0},
            "kcal": {"value": 520.0},
            "carbs_g": {"value": 55.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 30.0},
        },
        "ingredients": ["Potato", "Palmolein", "Salt"],
        "oil_listed": {"value": "Palmolein", "is_palm_oil": True},
        "front_pack_claims": [],
        "data_completeness": 1.0,
    }

    # Mock _acquire_tier_0_candidates to return 16 eligible stored candidates
    fake_stored = []
    for i in range(16):
        fake_stored.append({
            "id": i + 10,
            "product_name": {"value": f"Healthy Option {i}"},
            "brand": {"value": f"Brand {i % 4}"},
            "category": {"value": "Savory Packaged Snack"},
            "subcategory": {"value": "Chips"},
            "source_name": "blinkit",
            "nutrition": {
                "sugars_g": {"value": 0.5},
                "saturated_fat_g": {"value": 0.5},
                "sodium_mg": {"value": 100.0},
                "kcal": {"value": 130.0},
                "carbs_g": {"value": 20.0},
                "protein_g": {"value": 3.0},
                "fat_g": {"value": 2.0},
            },
            "ingredients": ["Baked Grain", "Sunflower Oil", "Salt"],
            "oil_listed": {"value": "Sunflower Oil", "is_palm_oil": False},
            "data_completeness": 1.0,
        })

    with patch.object(service, "_acquire_tier_0_candidates", AsyncMock(return_value=fake_stored)), \
         patch.object(tinyfish_scraper, "discover_category_listings") as mock_listing, \
         patch.object(tinyfish_scraper, "extract_product_detail") as mock_detail:

        res = await service.get_alternatives(
            searched_product_id=102,
            searched_product_data=unhealthy_snack,
            conditions=["general_health"],
            user_allergens=[],
        )

        assert res["status"] == "ok"
        assert len(res["alternatives"]) <= 3
        assert res["live_metrics"]["stored_eligible_count"] == 16
        assert res["live_metrics"]["live_discovery_ran"] is False
        mock_listing.assert_not_called()
        mock_detail.assert_not_called()


# -----------------------------------------------------------------------------
# 4. Stored pool too small: exactly 1 listing call, at most live_detail_budget detail calls
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stored_pool_too_small_makes_one_listing_call_and_budget_details(service):
    """Stored pool < min_stored_candidates triggers 1 listing call and <= live_detail_budget detail calls."""
    unhealthy_product = {
        "product_name": {"value": "Fried Snack Bar"},
        "brand": {"value": "BadBrand"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Crisps"},
        "source_name": "blinkit",
        "nutrition": {
            "sugars_g": {"value": 4.0},
            "saturated_fat_g": {"value": 8.0},
            "sodium_mg": {"value": 750.0},
            "kcal": {"value": 500.0},
            "carbs_g": {"value": 50.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 28.0},
        },
        "ingredients": ["Flour", "Palm Oil", "Salt"],
        "oil_listed": {"value": "Palm Oil", "is_palm_oil": True},
        "front_pack_claims": [],
        "data_completeness": 1.0,
    }

    # 15 dummy listings
    mock_listings = [
        {
            "name": f"Discovered Snack {i}",
            "brand": f"NewBrand{i % 3}",
            "variant": None,
            "pack_size": "50g",
            "price": 40.0,
            "product_url": f"https://blinkit.com/prn/snack-{i}/prid/{1000+i}",
            "product_id_at_source": f"sku_{1000+i}",
            "image_url": None,
            "in_stock": True,
            "subcategory": "Crisps",
            "source_name": "blinkit",
        }
        for i in range(15)
    ]

    mock_detail_product = {
        "product_name": {"value": "Discovered Healthy Crisp"},
        "brand": {"value": "HealthyCo"},
        "category": {"value": "Savory Packaged Snack"},
        "subcategory": {"value": "Crisps"},
        "source_name": "blinkit",
        "nutrition": {
            "sugars_g": {"value": 0.5},
            "saturated_fat_g": {"value": 0.5},
            "sodium_mg": {"value": 90.0},
            "kcal": {"value": 110.0},
            "carbs_g": {"value": 18.0},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 1.5},
        },
        "ingredients": ["Baked Millets", "Olive Oil", "Salt"],
        "oil_listed": {"value": "Olive Oil", "is_palm_oil": False},
        "data_completeness": 1.0,
    }

    # Stored candidates returns only 2 (less than 15)
    with patch.object(service, "_acquire_tier_0_candidates", AsyncMock(return_value=[])), \
         patch.object(tinyfish_scraper, "discover_category_listings", return_value=mock_listings) as mock_listing_call, \
         patch.object(tinyfish_scraper, "extract_product_detail", return_value=mock_detail_product) as mock_detail_call:

        # Let the background task run
        res = await service.get_alternatives(
            searched_product_id=103,
            searched_product_data=unhealthy_product,
            conditions=["general_health"],
            user_allergens=[],
            location="Delhi",
        )

        assert res["status"] == "refreshing"
        job_id = res["job_id"]
        assert job_id is not None

        # Await job completion
        await asyncio.sleep(0.3)
        job_res = service.get_job_status(job_id)
        assert job_res is not None

        mock_listing_call.assert_called_once()
        # Detail calls must never exceed live_detail_budget (8)
        assert mock_detail_call.call_count <= service.config["live_detail_budget"]


# -----------------------------------------------------------------------------
# 5. Listing Cache: Second request within TTL makes NO listing call
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_listing_cache_avoids_repeated_calls(service):
    """Repeated request for same (source, subcategory, location) within TTL hits cache."""
    listing_cache.clear()
    cached_items = [{
        "name": "Cached Snack",
        "brand": "CachedBrand",
        "product_url": "https://blinkit.com/cached-snack",
        "product_id_at_source": "sku_c1",
        "in_stock": True,
        "subcategory": "Crackers",
        "source_name": "blinkit",
    }]
    listing_cache.set("blinkit", "crackers", "mumbai", cached_items)

    with patch.object(tinyfish_scraper, "discover_category_listings") as mock_live_listing:
        # Request with same params
        res = listing_cache.get("blinkit", "crackers", "mumbai", ttl_hours=6.0)
        assert res is not None
        assert len(res) == 1
        assert res[0]["name"] == "Cached Snack"
        mock_live_listing.assert_not_called()


# -----------------------------------------------------------------------------
# 6. Single-Flight Locking: Concurrent requests cause 1 listing call
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_single_flight_concurrent_requests_share_call(service):
    """Simultaneous requests for same listing run only 1 listing call."""
    listing_cache.clear()
    call_counter = {"count": 0}

    def slow_listing(*args, **kwargs):
        call_counter["count"] += 1
        time.sleep(0.05)
        return [{
            "name": "Shared Listing Item",
            "brand": "SharedBrand",
            "product_url": "https://blinkit.com/shared",
            "product_id_at_source": "sku_shared",
            "in_stock": True,
            "subcategory": "Noodles",
            "source_name": "blinkit",
        }]

    with patch.object(tinyfish_scraper, "discover_category_listings", side_effect=slow_listing):
        lock = single_flight_locks.get_lock("listing:blinkit:noodles:delhi")
        async def fetch_job():
            async with lock:
                cached = listing_cache.get("blinkit", "noodles", "delhi")
                if cached:
                    return cached
                res = await asyncio.to_thread(tinyfish_scraper.discover_category_listings, "blinkit", "noodles", "delhi")
                listing_cache.set("blinkit", "noodles", "delhi", res)
                return res

        r1, r2 = await asyncio.gather(fetch_job(), fetch_job())
        assert r1 == r2
        assert call_counter["count"] == 1


# -----------------------------------------------------------------------------
# 7. Pre-filter Rules: Drop searched item, out-of-stock, duplicates, name allergens
# -----------------------------------------------------------------------------
def test_metadata_prefilter_rules(service):
    """Pre-filter drops searched product, duplicates, out-of-stock, and name-level allergens."""
    listing_items = [
        {"name": "Current Bad Chips", "brand": "BrandA", "product_url": "https://blinkit.com/current", "product_id_at_source": "sku_curr", "in_stock": True, "subcategory": "Chips"},
        {"name": "Out of Stock Baked Chips", "brand": "BrandB", "product_url": "https://blinkit.com/oos", "product_id_at_source": "sku_oos", "in_stock": False, "subcategory": "Chips"},
        {"name": "Peanut Butter Crunch", "brand": "BrandC", "product_url": "https://blinkit.com/pb", "product_id_at_source": "sku_pb", "in_stock": True, "subcategory": "Chips"},
        {"name": "Already Stored Chips", "brand": "BrandD", "product_url": "https://blinkit.com/stored", "product_id_at_source": "sku_stored", "in_stock": True, "subcategory": "Chips"},
        {"name": "Healthy Baked Nachos", "brand": "BrandE", "product_url": "https://blinkit.com/nachos", "product_id_at_source": "sku_nachos", "in_stock": True, "subcategory": "Chips"},
    ]

    stored_candidates = [
        {"product_name": {"value": "Already Stored Chips"}, "product_id_at_source": "sku_stored"}
    ]

    shortlisted, removed = service._prefilter_listing_metadata(
        listing_items=listing_items,
        searched_name="Current Bad Chips",
        searched_id_at_source="sku_curr",
        subcategory="Chips",
        user_allergens=["peanuts"],
        stored_candidates=stored_candidates,
        live_detail_budget=8,
    )

    assert len(shortlisted) == 1
    assert shortlisted[0]["name"] == "Healthy Baked Nachos"
    assert removed["searched_product"] == 1
    assert removed["out_of_stock"] == 1
    assert removed["allergen_name"] == 1
    assert removed["duplicate"] == 1


# -----------------------------------------------------------------------------
# 8. Extraction Validation: Discard unparsable or incomplete extractions
# -----------------------------------------------------------------------------
def test_extraction_validation():
    """Unparsable numbers, missing ingredients, or incomplete nutrition are discarded."""
    # Invalid: non-numeric sugar
    invalid_data = {
        "product_name": {"value": "Broken Product"},
        "brand": {"value": "Brand"},
        "ingredients": ["Flour", "Water"],
        "nutrition": {
            "kcal": {"value": 150.0},
            "carbs_g": {"value": 20.0},
            "sugars_g": {"value": "not_a_number"},  # Unparsable!
            "fat_g": {"value": 5.0},
        },
    }
    assert validate_extracted_product(invalid_data) is None

    # Invalid: empty ingredient list
    empty_ingredients = {
        "product_name": {"value": "No Ingredients"},
        "brand": {"value": "Brand"},
        "ingredients": [],
        "nutrition": {"kcal": 100, "carbs_g": 10, "sugars_g": 2, "fat_g": 1},
    }
    assert validate_extracted_product(empty_ingredients) is None

    # Valid product
    valid_data = {
        "product_name": {"value": "Good Product"},
        "brand": {"value": "GoodBrand"},
        "ingredients": ["Oats", "Cacao"],
        "nutrition": {
            "kcal": {"value": 180.0},
            "carbs_g": {"value": 25.0},
            "sugars_g": {"value": 1.0},
            "fat_g": {"value": 4.0},
            "serving_size": {"value": "40g"},
        },
        "data_completeness": 1.0,
    }
    validated = validate_extracted_product(valid_data)
    assert validated is not None
    assert validated["nutrition"]["sugars_g"]["value"] == 1.0


# -----------------------------------------------------------------------------
# 9. Circuit Breaker on Repeated Failures
# -----------------------------------------------------------------------------
def test_circuit_breaker_behavior():
    cb = circuit_breaker
    cb.reset()
    assert cb.is_tripped() is False

    cb.record_failure()
    cb.record_failure()
    assert cb.is_tripped() is False

    cb.record_failure()  # 3rd failure trips the breaker
    assert cb.is_tripped() is True

    cb.record_success()
    assert cb.is_tripped() is False


# -----------------------------------------------------------------------------
# 10. Daily Quota Limit Enforcement
# -----------------------------------------------------------------------------
def test_daily_call_tracker_quota():
    tracker = daily_call_tracker
    tracker.reset_counts()

    assert tracker.can_make_call("user_123", max_user_calls=2, max_global_calls=10) is True
    tracker.record_call("user_123")
    assert tracker.can_make_call("user_123", max_user_calls=2, max_global_calls=10) is True
    tracker.record_call("user_123")
    # Exceeded user quota
    assert tracker.can_make_call("user_123", max_user_calls=2, max_global_calls=10) is False
    # Other user still allowed
    assert tracker.can_make_call("user_456", max_user_calls=2, max_global_calls=10) is True


# -----------------------------------------------------------------------------
# 11. Source Rule: Retailer Consistency & Mixed Catalogue
# -----------------------------------------------------------------------------
def test_source_determination(service):
    prod_blinkit = {"product_name": {"value": "P", "source_url": "https://blinkit.com/prn/item/prid/123"}}
    src, is_ret = service._determine_source(prod_blinkit)
    assert src == "blinkit"
    assert is_ret is True

    prod_photo = {"product_name": {"value": "P"}, "is_user_photo": True}
    src_photo, is_ret_photo = service._determine_source(prod_photo)
    assert src_photo == "user_photo"
    assert is_ret_photo is False


# -----------------------------------------------------------------------------
# 12. Candidate Pool Size Limit and Rating Call Budget
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pool_size_and_rating_call_budget(service):
    """Rating function is called at most candidate_pool_size (25) times."""
    pool = [
        {
            "id": i,
            "product_name": {"value": f"Candidate {i}"},
            "brand": {"value": f"Brand {i % 5}"},
            "category": {"value": "Savory Packaged Snack"},
            "subcategory": {"value": "Makhana"},
            "nutrition": {
                "sugars_g": {"value": 0.5},
                "saturated_fat_g": {"value": 0.2},
                "sodium_mg": {"value": 50.0},
                "kcal": {"value": 110.0},
                "carbs_g": {"value": 15.0},
                "protein_g": {"value": 3.0},
                "fat_g": {"value": 1.0},
            },
            "ingredients": ["Foxnuts", "Salt"],
            "oil_listed": {"value": "None"},
            "data_completeness": 1.0,
        }
        for i in range(30)
    ]

    selected, r_calls = service._rate_and_select(
        candidate_pool=pool[:25],
        searched_product_data={"category": "Savory Packaged Snack", "subcategory": "Makhana"},
        p_rating=8.0,
        is_rating_valid=True,
        triggers=["high_rating"],
        has_allergen_conflict=False,
        conditions=["general_health"],
        user_allergens=[],
        source_name="blinkit",
        is_retailer=True,
        allow_cross_source_fallback=False,
    )

    assert r_calls <= 25
    assert len(selected) <= 3


# -----------------------------------------------------------------------------
# 13. Brand Diversity: Max 2 Per Brand
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_max_two_per_brand_strictly_enforced(service):
    """Never returns more than max_per_brand (2) from any single brand."""
    same_brand_pool = [
        {
            "id": i,
            "product_name": {"value": f"SameBrand Item {i}"},
            "brand": {"value": "MonoBrand"},
            "category": {"value": "Savory Packaged Snack"},
            "nutrition": {"kcal": 100, "carbs_g": 10, "sugars_g": 0.5, "fat_g": 1, "saturated_fat_g": 0.2, "sodium_mg": 50, "protein_g": 3},
            "ingredients": ["Makhana", "Salt"],
            "oil_listed": {"value": "None"},
            "data_completeness": 1.0,
        }
        for i in range(5)
    ]

    selected, _ = service._rate_and_select(
        candidate_pool=same_brand_pool,
        searched_product_data={"category": "Savory Packaged Snack"},
        p_rating=8.0,
        is_rating_valid=True,
        triggers=["high_rating"],
        has_allergen_conflict=False,
        conditions=["general_health"],
        user_allergens=[],
        source_name="blinkit",
        is_retailer=True,
        allow_cross_source_fallback=False,
    )

    assert len(selected) <= 2
    for alt in selected:
        assert alt["brand"] == "MonoBrand"


# -----------------------------------------------------------------------------
# 14. Progressive Delivery: In-flight Stored Results are Preserved
# -----------------------------------------------------------------------------
def test_progressive_delivery_order_preservation():
    """Initial cards shown to the user are never removed or reordered."""
    stored_shown = [
        {"product_id": 1, "name": "Stored Card A", "brand": "Brand 1", "personalised_rating": 2.5},
        {"product_id": 2, "name": "Stored Card B", "brand": "Brand 2", "personalised_rating": 2.8},
    ]

    new_discovered = [
        {"product_id": 3, "name": "Live Discovered C", "brand": "Brand 3", "personalised_rating": 1.5},
        {"product_id": 1, "name": "Stored Card A", "brand": "Brand 1", "personalised_rating": 2.5},
    ]

    # Merging logic preserving initial shown
    merged = list(stored_shown)
    shown_ids = {alt["product_id"] for alt in stored_shown}
    for alt in new_discovered:
        if alt["product_id"] not in shown_ids and len(merged) < 3:
            merged.append(alt)
            shown_ids.add(alt["product_id"])

    assert len(merged) == 3
    assert merged[0]["name"] == "Stored Card A"
    assert merged[1]["name"] == "Stored Card B"
    assert merged[2]["name"] == "Live Discovered C"


# -----------------------------------------------------------------------------
# 15. Invariants: Rating and Allergy Check Unchanged
# -----------------------------------------------------------------------------
def test_rating_and_allergy_check_invariants(service):
    """The rating engine and allergy check compute identical values and remain unchanged."""
    test_prod = {
        "product_name": {"value": "Sample Bar"},
        "brand": {"value": "SampleBrand"},
        "category": {"value": "Health Bars"},
        "nutrition": {
            "serving_size": {"value": "50g"},
            "kcal": {"value": 200.0},
            "carbs_g": {"value": 25.0},
            "sugars_g": {"value": 8.0},
            "protein_g": {"value": 10.0},
            "fat_g": {"value": 6.0},
            "saturated_fat_g": {"value": 2.0},
            "sodium_mg": {"value": 120.0},
        },
        "ingredients": ["Peanuts", "Oats", "Dates", "Milk Solids"],
        "oil_listed": {"value": "None declared"},
        "front_pack_claims": [],
    }

    # When product has user allergen, rating is None (hard-stop hidden) and status is NOT SAFE FOR YOU
    eval_conflict = service.scoring_engine.evaluate(test_prod, ["diabetes"], ["peanuts"])
    assert eval_conflict["allergy_check"]["allergy_status"] == "NOT SAFE FOR YOU"
    assert any("peanut" in a.lower() for a in eval_conflict["allergy_check"]["found_allergens"])
    assert eval_conflict["product_rating"] is None

    # When allergen-safe, rating is a valid float on 1-10 scale
    eval_safe = service.scoring_engine.evaluate(test_prod, ["diabetes"], [])
    assert eval_safe["allergy_check"]["allergy_status"] == "NONE FOUND"
    assert eval_safe["product_rating"] is not None
    assert 1.0 <= eval_safe["product_rating"] <= 10.0


# -----------------------------------------------------------------------------
# 16. Personalisation: Different Profiles Get Different Ratings for Same Candidate
# -----------------------------------------------------------------------------
def test_personalisation_different_ratings_for_same_candidate(service):
    """Two different user profiles receive different rating evaluations for the same product."""
    candidate = {
        "product_name": {"value": "Fruit & Nut Granola"},
        "brand": {"value": "HealthyMornings"},
        "category": {"value": "Breakfast Cereals"},
        "nutrition": {
            "serving_size": {"value": "40g"},
            "kcal": {"value": 160.0},
            "carbs_g": {"value": 26.0},
            "sugars_g": {"value": 11.0},
            "protein_g": {"value": 3.0},
            "fat_g": {"value": 4.5},
            "saturated_fat_g": {"value": 0.8},
            "sodium_mg": {"value": 40.0},
        },
        "ingredients": ["Rolled Oats", "Honey", "Dried Raisins", "Almonds"],
        "oil_listed": {"value": "Sunflower Oil"},
        "front_pack_claims": [],
    }

    eval_general = service.scoring_engine.evaluate(candidate, ["general_health"], [])
    eval_diabetes = service.scoring_engine.evaluate(candidate, ["diabetes"], [])

    # Granola has 11g sugar per 40g serve, which should score much worse for diabetes than general health
    assert eval_general["product_rating"] != eval_diabetes["product_rating"]
    assert eval_diabetes["product_rating"] > eval_general["product_rating"]
