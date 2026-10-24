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
