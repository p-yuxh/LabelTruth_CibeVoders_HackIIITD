import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import get_db, Base
from app.services.auth_service import hash_password, verify_password, validate_password_strength
from app.services.personalized_scoring import PersonalizedScoringEngine

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


def test_password_hashing_and_strength_validation():
    # 1. Password strength rules
    valid, reason, _ = validate_password_strength("short")
    assert not valid
    assert "at least 8 characters" in reason

    valid, reason, score = validate_password_strength("ValidPass123!")
    assert valid
    assert score >= 2

    # 2. PBKDF2 Hashing
    pwd = "SecurePassword2026!"
    hashed = hash_password(pwd)
    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert hashed != pwd

    # 3. Verification
    assert verify_password(pwd, hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.asyncio
async def test_profile_options_endpoint_loads_shared_config(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/profile-options")
        assert res.status_code == 200
        data = res.json()
        assert "sections" in data
        assert len(data["sections"]) == 5
        section_ids = [s["id"] for s in data["sections"]]
        assert section_ids == [
            "dietary_conditions",
            "allergies",
            "nutrition_goals",
            "avoid_ingredients",
            "dietary_pattern",
        ]
        # Check disclaimer
        assert "disclaimer" in data
        assert "General information, not medical advice" in data["disclaimer"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_signup_login_generic_errors_and_session(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "testuser_auth_1@example.com"
        pwd = "TestPassword123!"

        # 1. Sign up requires 18+ and terms
        res_no_terms = await ac.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": email,
            "password": pwd,
            "terms_agreed": False,
            "age_confirmed": True,
        })
        assert res_no_terms.status_code == 422
        assert "Terms" in res_no_terms.json()["detail"]

        res_no_age = await ac.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": email,
            "password": pwd,
            "terms_agreed": True,
            "age_confirmed": False,
        })
        assert res_no_age.status_code == 422
        assert "18 or older" in res_no_age.json()["detail"]

        # 2. Successful Sign Up
        res_signup = await ac.post("/api/auth/signup", json={
            "full_name": "Test User",
            "email": email,
            "password": pwd,
            "terms_agreed": True,
            "age_confirmed": True,
        })
        assert res_signup.status_code == 200
        signup_data = res_signup.json()
        assert "token" in signup_data
        assert signup_data["user"]["email"] == email
        token = signup_data["token"]

        # 3. Duplicate email rejected
        res_dup = await ac.post("/api/auth/signup", json={
            "full_name": "Another User",
            "email": email,
            "password": pwd,
            "terms_agreed": True,
            "age_confirmed": True,
        })
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"].lower()

        # 4. Login with invalid password returns generic failure
        res_bad_login = await ac.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPassword!",
        })
        assert res_bad_login.status_code == 401
        assert res_bad_login.json()["detail"] == "Invalid email or password."

        # 5. Successful Login
        res_login = await ac.post("/api/auth/login", json={
            "email": email,
            "password": pwd,
        })
        assert res_login.status_code == 200
        assert "token" in res_login.json()

        # 6. /auth/me with Bearer token
        res_me = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        assert res_me.json()["user"]["email"] == email
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_personalise_profile_chip_validation_and_consent_gate(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "testuser_profile_1@example.com"
        pwd = "Password123!"
        s_res = await ac.post("/api/auth/signup", json={
            "full_name": "Profile Tester",
            "email": email,
            "password": pwd,
            "terms_agreed": True,
            "age_confirmed": True,
        })
        token = s_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Reject unknown chip IDs
        res_unknown = await ac.post("/api/profile/save", headers=headers, json={
            "dietary_conditions": ["unknown_condition_xyz"],
            "allergies": [],
            "nutrition_goals": [],
            "avoid_ingredients": [],
            "dietary_pattern": "none",
            "health_data_consent": True,
        })
        assert res_unknown.status_code == 422
        assert "unknown" in res_unknown.json()["detail"].lower()

        # 2. Saving health data (Sections 01/02) WITHOUT consent is rejected
        res_no_consent = await ac.post("/api/profile/save", headers=headers, json={
            "dietary_conditions": ["diabetes"],
            "allergies": ["peanuts"],
            "nutrition_goals": ["lower_sugar"],
            "avoid_ingredients": ["palm_oil"],
            "dietary_pattern": "vegetarian",
            "health_data_consent": False,  # Missing consent!
        })
        assert res_no_consent.status_code == 400
        assert "consent" in res_no_consent.json()["detail"].lower()

        # 3. Path A (basic: goals, avoid, pattern only) succeeds without health consent
        res_basic = await ac.post("/api/profile/save", headers=headers, json={
            "dietary_conditions": [],
            "allergies": [],
            "nutrition_goals": ["lower_sugar", "more_protein"],
            "avoid_ingredients": ["palm_oil"],
            "dietary_pattern": "vegetarian",
            "health_data_consent": False,
            "path_taken": "basic",
        })
        assert res_basic.status_code == 200
        assert res_basic.json()["profile"]["path_taken"] == "basic"

        # 4. Path B (complete: with health data) succeeds WITH consent
        res_complete = await ac.post("/api/profile/save", headers=headers, json={
            "dietary_conditions": ["diabetes", "high_blood_pressure"],
            "allergies": ["peanuts", "milk"],
            "nutrition_goals": ["lower_sugar"],
            "avoid_ingredients": ["palm_oil"],
            "dietary_pattern": "vegetarian",
            "health_data_consent": True,
            "consent_version": "1.0",
            "path_taken": "complete",
        })
        assert res_complete.status_code == 200
        saved_p = res_complete.json()["profile"]
        assert saved_p["dietary_conditions"] == ["diabetes", "high_blood_pressure"]
        assert saved_p["allergies"] == ["peanuts", "milk"]
        assert saved_p["health_data_consent"] is True

        # 5. Guest session path without login
        res_guest = await ac.post("/api/profile/save", json={
            "dietary_conditions": [],
            "allergies": [],
            "nutrition_goals": ["lower_calories"],
            "avoid_ingredients": ["artificial_sweeteners"],
            "dietary_pattern": "vegan",
            "health_data_consent": False,
            "path_taken": "basic",
        })
        assert res_guest.status_code == 200
        assert res_guest.json()["is_guest"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_saved_comparisons_and_data_export_and_hard_delete(async_db):
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "testuser_export_delete@example.com"
        pwd = "Password123!"
        s_res = await ac.post("/api/auth/signup", json={
            "full_name": "Export Tester",
            "email": email,
            "password": pwd,
            "terms_agreed": True,
            "age_confirmed": True,
        })
        token = s_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Save comparison item (Product ID/query and timestamp ONLY; never health data)
        sc_res = await ac.post("/api/saved-comparisons", headers=headers, json={
            "query": "Cadbury Bournvita",
            "product_name": "Cadbury Bournvita Chocolate Health Drink",
            "product_id": 1,
        })
        assert sc_res.status_code == 200

        # List saved comparisons
        sc_list = await ac.get("/api/saved-comparisons", headers=headers)
        assert len(sc_list.json()) >= 1
        assert sc_list.json()[0]["query"] == "Cadbury Bournvita"

        # 2. Export my data (JSON)
        export_res = await ac.get("/api/auth/export-data", headers=headers)
        assert export_res.status_code == 200
        exp = export_res.json()
        assert exp["account_information"]["email"] == email
        assert len(exp["saved_comparisons"]) >= 1

        # 3. Hard delete account with password verification
        bad_del = await ac.request("DELETE", "/api/auth/account", headers=headers, json={"password": "Wrong"})
        assert bad_del.status_code == 401

        good_del = await ac.request("DELETE", "/api/auth/account", headers=headers, json={"password": pwd})
        assert good_del.status_code == 200

        # Login must fail after hard delete
        re_login = await ac.post("/api/auth/login", json={"email": email, "password": pwd})
        assert re_login.status_code == 401
    app.dependency_overrides.clear()


def test_gate_conditions_coeliac_and_lactose_intolerance():
    """
    Gate conditions run BEFORE rating and hide scores if unsafe:
    - coeliac_disease triggers gluten check
    - lactose_intolerance triggers milk check
    """
    engine = PersonalizedScoringEngine()

    # Product with Wheat Flour (Gluten)
    product_with_wheat = {
        "nutrition": {"sugars_g": {"value": 5.0}, "sodium_mg": {"value": 100.0}},
        "ingredients": ["Wheat Flour (Maida)", "Sugar", "Edible Vegetable Oil"],
        "oil_listed": {"value": "Sunflower Oil"},
    }

    # 1. Coeliac Disease selected -> Gluten detected -> NOT SAFE FOR YOU -> Scores Hidden
    eval_coeliac = engine.evaluate(
        product_data=product_with_wheat,
        selected_conditions=["coeliac_disease"],
        user_allergens=[],
    )
    assert eval_coeliac["allergy_check"]["allergy_status"] == "NOT SAFE FOR YOU"
    assert eval_coeliac["show_scores"] is False
    assert eval_coeliac["product_rating"] is None

    # Product with Milk Solids
    product_with_milk = {
        "nutrition": {"sugars_g": {"value": 2.0}, "fat_g": {"value": 1.0}},
        "ingredients": ["Milk Solids", "Sugar"],
        "oil_listed": {"value": "None declared"},
    }

    # 2. Lactose Intolerance selected -> Milk detected -> NOT SAFE FOR YOU -> Scores Hidden
    eval_lactose = engine.evaluate(
        product_data=product_with_milk,
        selected_conditions=["lactose_intolerance"],
        user_allergens=[],
    )
    assert eval_lactose["allergy_check"]["allergy_status"] == "NOT SAFE FOR YOU"
    assert eval_lactose["show_scores"] is False
    assert eval_lactose["product_rating"] is None

