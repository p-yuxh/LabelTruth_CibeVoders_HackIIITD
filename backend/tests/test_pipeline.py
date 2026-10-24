import os
os.environ["TESTING"] = "1"
os.environ["TINYFISH_API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["FALLBACK_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.FALLBACK_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.TINYFISH_API_KEY = ""

from app.main import app
import app.database
app.database._engine = None
app.database._sessionmaker = None
from app.database import get_db, Base
from app.models.evidence_log import EvidenceLog
from app.services.tinyfish_scraper import TinyFishScraperService
from app.services.claims_auditor import LabelTruthClaimsAuditor
from app.services.orchestrator import AuditOrchestrator
from app.services.image_detector import ProductImageDetector
from app.services.personalized_scoring import PersonalizedScoringEngine, excess_rating
from PIL import Image, ImageDraw
import io

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_tinyfish_scraper():
    scraper = TinyFishScraperService()
    result = scraper.run_full_pipeline("Cadbury Bournvita")
    
    assert "query" in result
    assert "search_results" in result
    assert len(result["search_results"]) > 0
    assert "agent_data" in result
    assert "serving_size" in result["agent_data"]
    assert "sugars_g" in result["agent_data"]
    assert "ingredients" in result["agent_data"]
    assert len(result["source_urls"]) > 0


@pytest.mark.asyncio
async def test_claims_auditor_attaches_source_url():
    scraper = TinyFishScraperService()
    auditor = LabelTruthClaimsAuditor()
    
    scraped = scraper.run_full_pipeline("Cadbury Bournvita")
    normalized = auditor.normalize_and_audit("Cadbury Bournvita", scraped)
    
    # Verify every major field attaches an exact source URL
    assert "product_name" in normalized and "source_url" in normalized["product_name"]
    assert "brand" in normalized and "source_url" in normalized["brand"]
    assert "nutrition" in normalized
    assert "serving_size" in normalized["nutrition"] and "source_url" in normalized["nutrition"]["serving_size"]
    assert "sugars_g" in normalized["nutrition"] and "source_url" in normalized["nutrition"]["sugars_g"]
    assert "oil_listed" in normalized and "source_url" in normalized["oil_listed"]
    
    # Verify ingredients list with source URLs and flags
    assert len(normalized["ingredients"]) > 0
    for ing in normalized["ingredients"]:
        assert "name" in ing
        assert "source_url" in ing
        assert "is_palm_oil_or_derivative" in ing

    # Verify front-of-pack claims
    assert len(normalized["front_pack_claims"]) > 0
    for claim in normalized["front_pack_claims"]:
        assert "claim" in claim
        assert "audit_verdict" in claim
        # Must only be one of the four allowed verdicts
        assert claim["audit_verdict"] in {"VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"}
        assert "source_url" in claim

    # Verify personalized scoring is attached
    assert "personalized_scoring" in normalized
    assert normalized["personalized_scoring"]["product_rating"] is not None


@pytest.mark.asyncio
async def test_orchestrator_cache_hit_and_miss(async_db):
    orchestrator = AuditOrchestrator()
    
    # 1. First run should be a CACHE MISS
    res1 = await orchestrator.audit_product(async_db, "Cadbury Bournvita")
    assert res1["is_cached"] is False
    assert res1["evidence_log_id"] > 0
    assert "Cadbury" in res1["data"]["product_name"]["value"]
    
    # 2. Second run should be a CACHE HIT
    res2 = await orchestrator.audit_product(async_db, "Cadbury Bournvita")
    assert res2["is_cached"] is True
    assert res2["evidence_log_id"] == res1["evidence_log_id"]
    
    # 3. Force refresh should bypass cache
    res3 = await orchestrator.audit_product(async_db, "Cadbury Bournvita", force_refresh=True)
    assert res3["is_cached"] is False
    assert res3["evidence_log_id"] != res1["evidence_log_id"]


@pytest.mark.asyncio
async def test_api_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tinyfish_api_configured"] is True


def test_image_detector_service():
    detector = ProductImageDetector()
    img = Image.new('RGB', (450, 120), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((25, 40), "Cadbury Bournvita 500g", fill='black')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    result = detector.detect_product_from_bytes(buf.getvalue())
    assert "detected_product" in result
    assert result["detected_product"] != ""


@pytest.mark.asyncio
async def test_detect_image_endpoint():
    img = Image.new('RGB', (300, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Nestle Maggi 2-Minute", fill='black')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/detect-image",
            files={"file": ("maggi_test.jpg", buf.getvalue(), "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "detected_product" in data


@pytest.mark.asyncio
async def test_audit_image_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    img = Image.new('RGB', (350, 100), color='yellow')
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Maggi 2-Minute Noodles", fill='black')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/audit-image",
            files={"file": ("maggi_noodles.jpg", buf.getvalue(), "image/jpeg")},
            data={"force_refresh": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Maggi" in data["data"]["product_name"]["value"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_audit_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/audit",
            json={"query": "Cadbury Bournvita", "force_refresh": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Cadbury Bournvita"
        assert "Cadbury" in data["data"]["product_name"]["value"]
        assert len(data["data"]["ingredients"]) > 0
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lays_chips_audit_and_palm_oil():
    scraper = TinyFishScraperService()
    auditor = LabelTruthClaimsAuditor()
    
    scraped = scraper.run_full_pipeline("Lays Potato Chips India")
    normalized = auditor.normalize_and_audit("Lays Potato Chips India", scraped)
    
    # 1. Product & Brand
    assert "Lay's" in normalized["brand"]["value"] or "PepsiCo" in normalized["brand"]["value"]
    assert "Savory" in normalized["category"]["value"] or "Snack" in normalized["category"]["value"]
    
    # 2. Palm oil (Palmolein) MUST be flagged
    assert normalized["oil_listed"]["is_palm_oil"] is True
    assert "palmolein" in normalized["oil_listed"]["value"].lower() or "palm" in normalized["oil_listed"]["value"].lower()
    
    # 3. Nutrition check
    nutrition = normalized["nutrition"]
    assert nutrition["fat_g"]["value"] >= 10.0
    assert nutrition["saturated_fat_g"]["value"] >= 4.0
    
    # 4. Claims audit: MUST NOT contain Maggi's "Taste Bhi, Health Bhi"
    claims = normalized["front_pack_claims"]
    claim_texts = [c["claim"].lower() for c in claims]
    assert "taste bhi, health bhi" not in claim_texts
    
    # 5. Verified verdict set: Only VERIFIED, MISLEADING, CONTRADICTED, NO EVIDENCE
    for c in claims:
        assert c["audit_verdict"] in {"VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"}
    
    # Trans fat claims with high saturated fat are MISLEADING
    trans_fat_claims = [c for c in claims if "trans" in c["claim"].lower()]
    if trans_fat_claims:
        assert trans_fat_claims[0]["audit_verdict"] == "MISLEADING"
        assert "saturated fat" in trans_fat_claims[0]["verdict_reason"].lower()


def test_image_detector_lays_filename():
    detector = ProductImageDetector()
    img = Image.new('RGB', (100, 100), color='yellow')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    
    filename = "gripping-pack-lays-chips-lyon-france-may-persons-hand-grasps-bright-bag-against-empty-gray-background-delicious-salt-279584423.webp"
    result = detector.detect_product_from_bytes(buf.getvalue(), filename=filename)
    
    assert "Lays" in result["detected_product"]
    assert result["detection_source"] == "filename_metadata"


@pytest.mark.asyncio
async def test_audit_endpoint_rejects_generic_queries(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/audit", json={"query": "Packaged Food Product"})
        assert response.status_code == 422
        assert "specific" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


# =========================================================================
# WORKED EXAMPLES AND SPECIFICATION TESTS (REQUIREMENT 6)
# =========================================================================

def test_excess_rating_worked_examples():
    """
    Worked examples:
    excess_rating(17, 15) = 3
    excess_rating(30, 15) = 10
    """
    assert excess_rating(17, 15) == 3
    assert excess_rating(30, 15) == 10
    # Boundary: at or below limit is 1
    assert excess_rating(15, 15) == 1
    assert excess_rating(10, 15) == 1


def test_sugar_limit_general_vs_diabetic():
    """
    Worked example:
    8 g sugar: general limit 15 -> 1, diabetic limit 5 -> 7
    """
    engine = PersonalizedScoringEngine()
    gen_limit = engine.profiles_config["general_health"]["nutrients"]["sugars_g"]["limit"]
    diab_limit = engine.profiles_config["diabetes"]["nutrients"]["sugars_g"]["limit"]
    
    assert gen_limit == 15.0
    assert diab_limit == 5.0
    
    assert excess_rating(8.0, gen_limit) == 1
    assert excess_rating(8.0, diab_limit) == 7


def test_ingredient_override_worked_example():
    """
    Worked example:
    ingredient override example (nine 1s plus one flagged 10 in last position) -> 7.35
    """
    engine = PersonalizedScoringEngine()
    # 9 safe ingredients (risk 1) + 1 flagged with risk 10 in position 10 (last)
    # The config has hydrogenated vegetable oil with risk 10
    mock_ingredients = [
        {"name": "Whole Wheat Flour"},
        {"name": "Water"},
        {"name": "Salt"},
        {"name": "Yeast"},
        {"name": "Barley Malt"},
        {"name": "Oat Flakes"},
        {"name": "Wheat Bran"},
        {"name": "Sunflower Seeds"},
        {"name": "Honey"},
        {"name": "Hydrogenated Vegetable Oil"}  # Position 10 (last) -> risk 10
    ]
    rating, top_3, worst_flagged = engine.calculate_ingredient_rating(mock_ingredients)
    assert rating == 7.35
    assert worst_flagged["risk_score"] == 10


def test_multi_condition_strictest_limit_and_highest_weight():
    """
    Multiple conditions: strictest (lowest) limit, highest weight per nutrient.
    """
    engine = PersonalizedScoringEngine()
    merged, title, _ = engine.merge_conditions(["diabetes", "hypertension"])
    
    # Sodium: diabetes limit 300, weight 2.0; hypertension limit 200, weight 4.5
    # Strictest limit = 200, highest weight = 4.5
    assert merged["sodium_mg"]["limit"] == 200.0
    assert merged["sodium_mg"]["weight"] == 4.5
    
    # Sugars: diabetes limit 5.0, weight 4.0; hypertension limit 10.0, weight 2.0
    # Strictest limit = 5.0, highest weight = 4.0
    assert merged["sugars_g"]["limit"] == 5.0
    assert merged["sugars_g"]["weight"] == 4.0



def test_allergy_check_not_safe_hides_scores():
    """
    ALLERGY CHECK: NOT SAFE FOR YOU / CANNOT CONFIRM / NONE FOUND.
    If NOT SAFE, show no scores.
    """
    engine = PersonalizedScoringEngine()
    product_data = {
        "nutrition": {
            "sugars_g": {"value": 2.0},
            "sodium_mg": {"value": 100.0},
            "saturated_fat_g": {"value": 1.0}
        },
        "ingredients": [{"name": "Wheat Flour"}, {"name": "Peanut Butter"}],
        "oil_listed": {"value": "Sunflower Oil"},
        "front_pack_claims": []
    }
    
    # User is allergic to peanut
    eval_res = engine.evaluate(
        product_data=product_data,
        selected_conditions=["general_health"],
        user_allergens=["peanut"]
    )
    
    assert eval_res["allergy_check"]["allergy_status"] == "NOT SAFE FOR YOU"
    assert eval_res["show_scores"] is False
    # All scores must be suppressed
    assert eval_res["product_rating"] is None
    assert eval_res["nutrient_rating"] is None
    assert eval_res["ingredient_rating"] is None
    assert "personal_match_score" not in eval_res


def test_claim_verdicts_only_allowed_and_non_nutrient_check():
    """
    CLAIM VERDICTS use only: VERIFIED, MISLEADING, CONTRADICTED, NO EVIDENCE.
    Non-nutrient claims (Vegetarian) checked against ingredient list.
    """
    auditor = LabelTruthClaimsAuditor()
    nutrition = {
        "sugars_g": {"value": 12.0},
        "protein_g": {"value": 2.0},
        "fat_g": {"value": 8.0},
        "saturated_fat_g": {"value": 4.5},
        "sodium_mg": {"value": 600.0}
    }
    
    # 1. Product with non-vegetarian gelatin
    claims = [
        {"claim": "100% Vegetarian"},
        {"claim": "Zero Sugar"},
        {"claim": "Good for Health"},
        {"claim": "Super Tasty Snack"}
    ]
    ingredients = [{"name": "Sugar"}, {"name": "Pork Gelatin"}, {"name": "Palmolein"}]
    
    audited = auditor._audit_claims(claims, nutrition, contains_palm=True, ingredients=ingredients, source_url="https://test")
    verdicts = {c["claim"]: c["audit_verdict"] for c in audited}
    
    # Vegetarian claim contradicted by pork gelatin
    assert verdicts["100% Vegetarian"] == "CONTRADICTED"
    # Zero Sugar contradicted by 12g sugar
    assert verdicts["Zero Sugar"] == "CONTRADICTED"
    # Good for Health contradicted by palm oil and high sodium/sugar
    assert verdicts["Good for Health"] == "CONTRADICTED"
    # Super Tasty Snack is subjective marketing -> NO EVIDENCE
    assert verdicts["Super Tasty Snack"] == "NO EVIDENCE"
    
    # Allowed verdict set validation
    for c in audited:
        assert c["audit_verdict"] in {"VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"}


@pytest.mark.asyncio
async def test_reference_standards_registry():
    from app.services.reference_standards import ReferenceStandardsRegistry
    registry = ReferenceStandardsRegistry(default_share_of_daily=0.15)
    
    sugar_limit = registry.get_per_serving_benchmark("sugar", 0.15)
    assert sugar_limit["daily_limit"] == 25.0
    assert sugar_limit["per_serving_limit"] == round(25.0 * 0.15, 1)
    assert "ICMR-NIN" in sugar_limit["source_name"]
    assert "nin.res.in" in sugar_limit["source_url"]
    assert sugar_limit["access_date"] == "2026-10-24"


@pytest.mark.asyncio
async def test_diet_coke_detection_and_zero_sugar_audit():
    detector = ProductImageDetector()
    img = Image.new('RGB', (100, 100), color='silver')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    
    fn = "coca-cola-white-background-bottle-coca-cola-diet-coke-zero-sugar-white-background-coca-cola-carbonated-soft-drink-191163254.webp"
    result = detector.detect_product_from_bytes(buf.getvalue(), filename=fn)
    assert "Coca-Cola" in result["detected_product"] or "Coke" in result["detected_product"]
    
    # Run audit pipeline for Diet Coke
    scraper = TinyFishScraperService()
    auditor = LabelTruthClaimsAuditor()
    scraped = scraper.run_full_pipeline("Coca-Cola Zero Sugar Diet Coke")
    normalized = auditor.normalize_and_audit("Coca-Cola Zero Sugar Diet Coke", scraped)
    
    assert "Carbonated" in normalized["category"]["value"] or "Beverage" in normalized["category"]["value"]
    # Zero Sugar claim verified against FSSAI <=0.5g/100ml
    zero_sugar_claims = [c for c in normalized["front_pack_claims"] if "zero sugar" in c["claim"].lower()]
    if zero_sugar_claims:
        assert zero_sugar_claims[0]["audit_verdict"] == "VERIFIED"
        assert "fssai" in zero_sugar_claims[0]["verdict_reason"].lower()


@pytest.mark.asyncio
async def test_score_personal_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "product_data": {
                "nutrition": {
                    "carbs_g": {"value": 10.0},
                    "sugars_g": {"value": 1.0},
                    "protein_g": {"value": 5.0},
                    "fat_g": {"value": 2.0},
                    "saturated_fat_g": {"value": 0.5},
                    "sodium_mg": {"value": 80.0}
                },
                "ingredients": [{"name": "Mustard Oil"}, {"name": "Lentils"}],
                "oil_listed": {"value": "Cold Pressed Mustard Oil", "is_palm_oil": False}
            },
            "conditions": ["general_health"],
            "user_allergens": []
        }
        res = await client.post("/api/score-personal", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "product_rating" in data
        assert "nutrient_rating" in data
        assert "ingredient_rating" in data
        assert "allergy_check" in data
        assert "personal_match_score" not in data
        assert data["show_scores"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reference_standards_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/reference-standards?share_of_daily=0.15")
        assert res.status_code == 200
        data = res.json()
        assert "statutory_claim_rules" in data
        assert "daily_guidelines" in data
        assert "diabetes_clinical_guidance" in data
        assert data["access_date"] == "2026-10-24"
    app.dependency_overrides.clear()


# =========================================================================
# REVISED SPECIFICATION TESTS: STRICT PERSONALISED RATING & RECOMMENDATIONS
# =========================================================================

def test_rating_identical_regardless_of_claims_or_former_preference_input():
    """
    Requirement 2 & 6:
    Assert that the Personalised Rating is IDENTICAL regardless of claim verdicts
    or any former preference input.
    Personalised Rating depends ONLY on:
    - nutrient values vs selected health condition limits and weights
    - ingredient risk values
    - selected health conditions
    Nothing else may change it: no preferences, no claim verdicts, no match score.
    """
    engine = PersonalizedScoringEngine()
    
    base_product = {
        "nutrition": {
            "sugars_g": {"value": 8.0},
            "sodium_mg": {"value": 350.0},
            "saturated_fat_g": {"value": 2.5},
            "protein_g": {"value": 4.0},
            "fat_g": {"value": 6.0},
            "carbs_g": {"value": 20.0}
        },
        "ingredients": [
            {"name": "Whole Wheat Flour"},
            {"name": "Oats"},
            {"name": "Sunflower Oil"},
            {"name": "Salt"}
        ],
        "oil_listed": {"value": "Sunflower Oil", "is_palm_oil": False}
    }

    # Case 1: All claims VERIFIED
    prod_verified = dict(base_product)
    prod_verified["front_pack_claims"] = [
        {"claim": "High Fibre", "audit_verdict": "VERIFIED"},
        {"claim": "No Added Preservatives", "audit_verdict": "VERIFIED"}
    ]
    res_verified = engine.evaluate(prod_verified, selected_conditions=["general_health"])

    # Case 2: All claims CONTRADICTED or MISLEADING
    prod_contradicted = dict(base_product)
    prod_contradicted["front_pack_claims"] = [
        {"claim": "100% Superfood", "audit_verdict": "CONTRADICTED"},
        {"claim": "Zero Calorie", "audit_verdict": "MISLEADING"}
    ]
    res_contradicted = engine.evaluate(prod_contradicted, selected_conditions=["general_health"])

    # Case 3: No claims at all
    prod_no_claims = dict(base_product)
    prod_no_claims["front_pack_claims"] = []
    res_no_claims = engine.evaluate(prod_no_claims, selected_conditions=["general_health"])

    # Ratings MUST BE 100% IDENTICAL across all cases
    assert res_verified["product_rating"] == res_contradicted["product_rating"] == res_no_claims["product_rating"]
    assert res_verified["nutrient_rating"] == res_contradicted["nutrient_rating"] == res_no_claims["nutrient_rating"]
    assert res_verified["ingredient_rating"] == res_contradicted["ingredient_rating"] == res_no_claims["ingredient_rating"]
    
    # Assert neither personal_match_score nor preferences exist in output
    assert "personal_match_score" not in res_verified
    assert "preferences" not in res_verified
    assert "match_details" not in res_verified


def test_no_code_path_reads_preferences():
    """
    Requirement 6:
    Assert that no code path reads preferences.
    Evaluate signature takes ONLY product_data, selected_conditions, user_allergens.
    """
    import inspect
    engine = PersonalizedScoringEngine()
    sig = inspect.signature(engine.evaluate)
    param_names = list(sig.parameters.keys())
    
    assert "preferences" not in param_names
    assert "avoided_ingredients" not in param_names
    assert "preferred_ingredients" not in param_names
    assert "match_score" not in param_names

    # Check PersonalizeRequest schema ignores or rejects preferences
    from app.schemas.product import PersonalizeRequest, AuditRequest
    req_fields = list(PersonalizeRequest.model_fields.keys())
    assert "preferences" not in req_fields
    assert "avoided_ingredients" not in req_fields
    assert "preferred_ingredients" not in req_fields
    assert "strict_palm_oil" not in req_fields

    audit_fields = list(AuditRequest.model_fields.keys())
    assert "preferences" not in audit_fields
    assert "avoided_ingredients" not in audit_fields
    assert "preferred_ingredients" not in audit_fields


def test_recommendations_category_ranking_and_allergy_exclusion():
    """
    Requirement 4:
    RECOMMENDATIONS: in the same category, exclude products with allergy status NOT SAFE,
    then rank by Personalised Rating (lowest first). Break ties by fewer CONTRADICTED / MISLEADING claims.
    Show the reason in plain words using nutrient and ingredient findings only.
    """
    engine = PersonalizedScoringEngine()

    current_product = {
        "product_name": {"value": "High Fat Potato Chips"},
        "category": {"value": "Savory Packaged Snack"},
        "nutrition": {
            "sugars_g": {"value": 1.0},
            "saturated_fat_g": {"value": 5.0},
            "sodium_mg": {"value": 450.0}
        },
        "ingredients": ["Potato", "Palmolein", "Salt"],
        "oil_listed": {"value": "Palmolein", "is_palm_oil": True}
    }

    candidates = [
        # Candidate 1: Contains peanut - user is allergic to peanut -> MUST BE EXCLUDED
        {
            "product_name": {"value": "Peanut Chikki Snack", "source_url": "https://test.com"},
            "brand": {"value": "NutBrand"},
            "category": {"value": "Savory Packaged Snack"},
            "nutrition": {"sugars_g": {"value": 4.0}, "saturated_fat_g": {"value": 1.0}, "sodium_mg": {"value": 80.0}},
            "ingredients": [{"name": "Peanuts"}, {"name": "Jaggery"}],
            "oil_listed": {"value": "None"},
            "front_pack_claims": []
        },
        # Candidate 2: Clean, low rating (e.g. 1.8), 0 contradicted claims -> RANK 1
        {
            "product_name": {"value": "Roasted Foxnuts Pink Salt", "source_url": "https://test.com"},
            "brand": {"value": "HealthyBrand"},
            "category": {"value": "Savory Packaged Snack"},
            "nutrition": {"sugars_g": {"value": 0.2}, "saturated_fat_g": {"value": 0.4}, "sodium_mg": {"value": 110.0}},
            "ingredients": [{"name": "Foxnuts (Makhana)"}, {"name": "Olive Oil"}, {"name": "Rock Salt"}],
            "oil_listed": {"value": "Olive Oil", "is_palm_oil": False},
            "front_pack_claims": [
                {"claim": "Roasted", "audit_verdict": "VERIFIED"}
            ]
        },
        # Candidate 3: Moderate rating (e.g. 3.2), 1 contradicted claim -> RANK 2
        {
            "product_name": {"value": "Baked Multigrain Crisp", "source_url": "https://test.com"},
            "brand": {"value": "CrispBrand"},
            "category": {"value": "Savory Packaged Snack"},
            "nutrition": {"sugars_g": {"value": 2.0}, "saturated_fat_g": {"value": 1.8}, "sodium_mg": {"value": 240.0}},
            "ingredients": [{"name": "Wheat"}, {"name": "Corn"}, {"name": "Sunflower Oil"}],
            "oil_listed": {"value": "Sunflower Oil", "is_palm_oil": False},
            "front_pack_claims": [
                {"claim": "Zero Fat", "audit_verdict": "CONTRADICTED"}
            ]
        }
    ]

    recs = engine.rank_recommendations(
        current_product=current_product,
        candidate_products=candidates,
        selected_conditions=["general_health"],
        user_allergens=["peanut"]
    )

    rec_names = [r["product_name"] for r in recs]

    # 1. Product with allergen 'peanut' MUST be excluded
    assert "Peanut Chikki Snack" not in rec_names

    # 2. Lowest rating first
    assert recs[0]["product_name"] == "Roasted Foxnuts Pink Salt"
    assert recs[0]["personalised_rating"] <= recs[-1]["personalised_rating"]
    # Break ties by fewer contradicted/misleading claims
    assert recs[0]["flagged_claims_count"] <= recs[-1]["flagged_claims_count"]

    # 3. Reason uses nutrient and ingredient findings only
    for r in recs:
        reason = r["recommendation_reason"]
        assert len(reason) > 5
        # Must strictly use nutrient and ingredient findings
        assert any(k in reason.lower() for k in ["sodium", "sugar", "saturated fat", "fat", "oil", "additive", "rating"])
        # Must not mention match or preferences
        assert "match" not in reason.lower()
        assert "preference" not in reason.lower()


def test_no_forbidden_leftovers_in_production_codebase():
    """
    Requirement 6:
    Search the codebase for 'match', 'pref', 'profile_fit' and remove leftovers.
    Asserts zero occurrences in backend/app and frontend/src.
    """
    import os, re

    forbidden_patterns = [
        r'\bmatch_score\b',
        r'\bpersonal_match_score\b',
        r'\bprofile_fit\b',
        r'\bpref_fit\b',
        r'\bpreferences\b',
        r'\bavoided_ingredients\b',
        r'\bpreferred_ingredients\b',
        r'\bstrict_palm_oil\b',
        r'Final Clamped Match Score',
        r'Nutrient profile penalty',
    ]
    regex = re.compile('|'.join(forbidden_patterns), re.IGNORECASE)

    paths_to_scan = ['backend/app', 'frontend/src']
    findings = []

    for base_dir in paths_to_scan:
        for root, dirs, files in os.walk(base_dir):
            if '__pycache__' in root or 'node_modules' in root:
                continue
            for f in files:
                if f.endswith(('.py', '.json', '.jsx', '.js', '.css', '.html')):
                    full_p = os.path.join(root, f)
                    with open(full_p, 'r', encoding='utf-8', errors='ignore') as fl:
                        for idx, line in enumerate(fl, 1):
                            if regex.search(line):
                                findings.append(f"{full_p}:{idx}: {line.strip()}")

    assert not findings, f"Found forbidden leftovers in codebase: {findings}"
