import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
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


@pytest.mark.asyncio
async def test_image_detector_service():
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


@pytest.mark.asyncio
async def test_image_detector_lays_filename():
    detector = ProductImageDetector()
    img = Image.new('RGB', (100, 100), color='yellow')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    
    filename = "gripping-pack-lays-chips-lyon-france-may-persons-hand-grasps-bright-bag-against-empty-gray-background-delicious-salt-279584423.webp"
    result = detector.detect_product_from_bytes(buf.getvalue(), filename=filename)
    
    assert "Lays" in result["detected_product"]
    assert result["match_source"] == "filename_metadata"


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


def test_personal_match_score_no_preferences_and_clamp():
    """
    Personal Match Score (0-100, higher = better):
    If user has selected NO preferences, show 'No preferences selected'
    and apply only claim and nutrient signals. Never invent a default like 75.
    """
    engine = PersonalizedScoringEngine()
    
    # 1. Product with no claims and nutrient rating = 1.0 (perfect)
    res_clean = engine.calculate_personal_match_score(
        nutrient_rating=1.0,
        claims=[],
        ingredients=["Oats", "Water"],
        oil_declared="None declared",
        preferences=[],
        avoided_ingredients=[],
        preferred_ingredients=[],
    )
    assert res_clean["personal_match_score"] == 100
    assert res_clean["has_preferences"] is False
    assert res_clean["preferences_label"] == "No preferences selected"
    
    # 2. Product with nutrient rating = 10.0, 1 CONTRADICTED claim (-30), 1 MISLEADING claim (-15)
    # Start 100; -30; -15; nutrient penalty: -(10-1) * 25/9 = -25.
    # Total = 100 - 30 - 15 - 25 = 30
    res_bad = engine.calculate_personal_match_score(
        nutrient_rating=10.0,
        claims=[
            {"claim": "Healthy Growth", "audit_verdict": "CONTRADICTED"},
            {"claim": "Zero Trans Fat", "audit_verdict": "MISLEADING"}
        ],
        ingredients=["Sugar", "Refined Flour"],
        oil_declared="None declared",
        preferences=[],
        avoided_ingredients=[],
        preferred_ingredients=[],
    )
    assert res_bad["personal_match_score"] == 30
    assert res_bad["preferences_label"] == "No preferences selected"


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
    assert eval_res["personal_match_score"] is None


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
            "user_allergens": [],
            "preferences": []
        }
        res = await client.post("/api/score-personal", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "product_rating" in data
        assert "personal_match_score" in data
        assert "allergy_check" in data
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
