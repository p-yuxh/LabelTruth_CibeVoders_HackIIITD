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
        assert "source_url" in claim

    # Verify claim integrity score
    assert 0 <= normalized["claim_integrity_score"] <= 100


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
    
    res = detector.detect_product_from_bytes(buf.getvalue())
    assert "Bournvita" in res["detected_product"]
    assert res["match_source"] == "pattern_match"


@pytest.mark.asyncio
async def test_detect_image_endpoint():
    img = Image.new('RGB', (450, 120), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((25, 40), "Nestle Maggi Noodles", fill='black')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test_package.png", buf.getvalue(), "image/png")}
        response = await client.post("/api/detect-image", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "Maggi" in data["detected_product"]


@pytest.mark.asyncio
async def test_audit_image_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    
    img = Image.new('RGB', (450, 120), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((25, 40), "Cadbury Bournvita 500g", fill='black')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("bournvita.png", buf.getvalue(), "image/png")}
        response = await client.post("/api/audit-image", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "Cadbury" in data["data"]["product_name"]["value"]
        assert data["data"]["oil_listed"] is not None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_audit_endpoint(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Nestle Maggi 2-Minute Noodles"}
        response = await client.post("/api/audit", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Nestle Maggi 2-Minute Noodles"
        assert data["is_cached"] is False
        assert "oil_listed" in data["data"]
        assert data["data"]["oil_listed"]["is_palm_oil"] is True
        
        # Test evidence logs endpoint
        logs_res = await client.get("/api/evidence-logs")
        assert logs_res.status_code == 200
        logs = logs_res.json()
        assert len(logs) >= 1
        assert logs[0]["query"] == "Nestle Maggi 2-Minute Noodles"

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
    
    # Verified with caveat for Zero Trans Fat
    trans_fat_claims = [c for c in claims if "trans" in c["claim"].lower()]
    if trans_fat_claims:
        assert trans_fat_claims[0]["audit_verdict"] == "Verified with Caveat"
        assert "saturated fat" in trans_fat_claims[0]["verdict_reason"].lower()
    
    # 5. Integrity score should reflect deep-fried snack with palm oil (~50-65)
    assert 40 <= normalized["claim_integrity_score"] <= 70


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


@pytest.mark.asyncio
async def test_personalized_scoring_and_hard_exclusion():
    from app.services.personalized_scoring import PersonalizedScoringEngine
    engine = PersonalizedScoringEngine(share_of_daily=0.15)
    
    # 1. Product without palm oil (Clean snack)
    clean_snack = {
        "nutrition": {
            "carbs_g": {"value": 14.0},
            "sugars_g": {"value": 2.0},
            "protein_g": {"value": 8.0},
            "fat_g": {"value": 4.0},
            "saturated_fat_g": {"value": 1.0},
            "sodium_mg": {"value": 110.0}
        },
        "oil_listed": {"value": "Sunflower Oil", "is_palm_oil": False}
    }
    
    res = engine.evaluate_personalized_fit(clean_snack, profile_key="diabetes_aware")
    assert res["status"] == "MATCHED"
    assert res["is_hard_excluded"] is False
    assert 0 <= res["personal_match_score"] <= 100
    # Verify formula math
    expected_match = int(round(0.75 * res["profile_suitability"] + 0.25 * res["preference_match"]))
    assert res["personal_match_score"] == expected_match
    
    # 2. Hard Exclusion: Palm Oil avoidance marked strict
    palm_snack = {
        "nutrition": {
            "protein_g": {"value": 25.0},  # High protein cannot compensate
            "sugars_g": {"value": 0.0}
        },
        "oil_listed": {"value": "Palmolein", "is_palm_oil": True}
    }
    ex_res = engine.evaluate_personalized_fit(
        palm_snack,
        profile_key="protein_conscious",
        strict_palm_oil_avoidance=True
    )
    assert ex_res["is_hard_excluded"] is True
    assert ex_res["status"] == "EXCLUDED"
    assert ex_res["personal_match_score"] == 0
    assert "Strict Palm Oil Avoidance" in ex_res["hard_exclusion_reason"]


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
        assert zero_sugar_claims[0]["audit_verdict"] == "Verified"
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
                "oil_listed": {"value": "Cold Pressed Mustard Oil", "is_palm_oil": False}
            },
            "profile": "general_health",
            "strict_palm_oil": False,
            "goals": ["lower_sugar", "low_sodium"],
            "share_of_daily": 0.15
        }
        res = await client.post("/api/score-personal", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "personal_match_score" in data
        assert "all_profiles" in data
        assert "General Health-Aware" in data["profile_name"]
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
