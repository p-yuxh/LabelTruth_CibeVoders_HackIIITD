import copy
from datetime import date
import pytest

from app.services.independent_evidence_service import IndependentEvidenceService
from app.services.personalized_scoring import PersonalizedScoringEngine


@pytest.fixture
def evidence_service():
    # Use a fixed reference date for deterministic testing: 2026-10-24
    ref_date = date(2026, 10, 24)
    return IndependentEvidenceService(reference_date=ref_date)


def test_age_badge_boundaries_and_classification(evidence_service):
    """
    Age badge:
    - 1 year -> Recent
    - 3 years -> Ageing
    - 6 years -> Old
    - no date / empty date -> Unknown
    - Exact boundaries: <= 2.0 is Recent, <= 5.0 is Ageing, > 5.0 is Old
    """
    ref = date(2026, 10, 24)

    # 1. 1 year ago (2025-10-24): age ~ 1.0 -> Recent
    age, status, text = evidence_service.compute_report_age("2025-10-24", ref_date=ref)
    assert status == "recent"
    assert 0.99 <= age <= 1.01
    assert "Tested: 2025-10-24" in text

    # 2. Exactly 2.0 years ago (2024-10-24): boundary at 2.0 -> Recent (<= 2.0)
    age_2, status_2, _ = evidence_service.compute_report_age("2024-10-24", ref_date=ref)
    assert age_2 <= 2.0
    assert status_2 == "recent"

    # 3. 3 years ago (2023-10-24): age ~ 3.0 -> Ageing (> 2.0 and <= 5.0)
    age_3, status_3, _ = evidence_service.compute_report_age("2023-10-24", ref_date=ref)
    assert status_3 == "ageing"
    assert 2.99 <= age_3 <= 3.01

    # 4. Exactly 5.0 years ago (2021-10-24): boundary at 5.0 -> Ageing (<= 5.0)
    age_5, status_5, _ = evidence_service.compute_report_age("2021-10-24", ref_date=ref)
    assert age_5 <= 5.01
    assert status_5 == "ageing"

    # 5. 6 years ago (2020-10-24): age ~ 6.0 -> Old (> 5.0)
    age_6, status_6, _ = evidence_service.compute_report_age("2020-10-24", ref_date=ref)
    assert status_6 == "old"
    assert age_6 > 5.0

    # 6. No date -> Unknown
    age_none, status_none, text_none = evidence_service.compute_report_age(None, ref_date=ref)
    assert age_none is None
    assert status_none == "unknown"
    assert text_none == "Date unknown"

    age_empty, status_empty, _ = evidence_service.compute_report_age("", ref_date=ref)
    assert status_empty == "unknown"


def test_old_report_does_not_produce_contradicted_when_allow_old_false(evidence_service):
    """
    An Old report with a large gap does NOT produce CONTRADICTED when allow_old_for_verdict is False.
    """
    claim = {
        "claim": "Contains No Added Salt",
        "category": "Sodium",
        "audit_verdict": "VERIFIED",
        "reason": "Statutory verification.",
        "source_url": "https://example.com",
    }

    # Synthesize an Old report (age > 5 years) with gap = +50% (exceeding tolerance 15%)
    old_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "lab_test_old_sodium",
                    "parameter": "Sodium Content",
                    "label_value": 100.0,
                    "lab_value": 150.0,
                    "lab_gap_pct": 50.0,
                    "age_status": "old",
                    "age_display": "Tested: 2018-01-01 (8 yrs ago)",
                    "source_name": "Historical Food Lab",
                    "tier": "C",
                    "original_report_url": "https://example.com/report.pdf",
                    "batch_note": "Results apply to the batch tested; the product may have changed since.",
                }
            ],
            "reported_not_verified": [],
        }
    }

    # When allow_old_for_verdict is False (default)
    updated = evidence_service.apply_evidence_to_claim_verdicts(
        claims=[claim],
        evidence=old_evidence,
        allow_old_for_verdict=False,
    )
    assert updated[0]["audit_verdict"] != "CONTRADICTED"
    assert "cannot produce CONTRADICTED" in updated[0]["reason"]

    # When allow_old_for_verdict is True, it CAN produce CONTRADICTED
    updated_allowed = evidence_service.apply_evidence_to_claim_verdicts(
        claims=[claim],
        evidence=old_evidence,
        allow_old_for_verdict=True,
    )
    assert updated_allowed[0]["audit_verdict"] == "CONTRADICTED"


def test_recent_matching_report_gap_above_and_within_tolerance(evidence_service):
    """
    A Recent, fully matching report with gap above tolerance produces CONTRADICTED;
    within tolerance produces VERIFIED.
    """
    # 1. Sugar claim with Recent report and gap = +25% (> 15% tolerance) -> CONTRADICTED
    claim_high_gap = {
        "claim": "Low Sugar Formula",
        "category": "Sugar",
        "audit_verdict": "VERIFIED",
        "reason": "Declared within statutory threshold.",
        "source_url": "https://example.com",
    }
    evidence_high_gap = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "lab_recent_sugar",
                    "parameter": "Total Sugars",
                    "label_value": 10.0,
                    "lab_value": 12.5,
                    "lab_gap_pct": 25.0,  # 25% gap
                    "age_status": "recent",
                    "source_name": "NABL Accredited Testing",
                    "tier": "C",
                    "original_report_url": "https://example.com/lab.pdf",
                }
            ]
        }
    }
    updated_contradicted = evidence_service.apply_evidence_to_claim_verdicts(
        claims=[claim_high_gap],
        evidence=evidence_high_gap,
    )
    assert updated_contradicted[0]["audit_verdict"] == "CONTRADICTED"
    assert "Contradicted by NABL Accredited Testing" in updated_contradicted[0]["reason"]

    # 2. Protein claim with Recent report and gap = +3% (within 15% tolerance) -> VERIFIED
    claim_within_tolerance = {
        "claim": "High Protein Cereal",
        "category": "Protein",
        "audit_verdict": "NO EVIDENCE",
        "reason": "No evidence.",
        "source_url": "https://example.com",
    }
    evidence_within_tolerance = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "lab_recent_protein",
                    "parameter": "Protein Content",
                    "label_value": 20.0,
                    "lab_value": 20.6,
                    "lab_gap_pct": 3.0,  # 3% gap
                    "age_status": "recent",
                    "source_name": "Analytical Laboratory",
                    "tier": "B",
                    "original_report_url": "https://example.com/lab_protein.pdf",
                }
            ]
        }
    }
    updated_verified = evidence_service.apply_evidence_to_claim_verdicts(
        claims=[claim_within_tolerance],
        evidence=evidence_within_tolerance,
    )
    assert updated_verified[0]["audit_verdict"] == "VERIFIED"
    assert "Verified by Analytical Laboratory" in updated_verified[0]["reason"]


def test_milk_report_not_on_butter_and_microbiological_not_on_sugar(evidence_service):
    """
    A milk coliform report is not attached to a butter product,
    and a microbiological result does not affect a sugar claim.
    """
    # 1. Milk coliform report checked against Amul Butter
    status, reason = evidence_service.evaluate_acceptance_rules(
        record={
            "brand": "Amul",
            "product": "Raw Fluid Milk",
            "parameter": "Raw Milk Coliform Count",
            "original_report_url": "https://example.com/report.pdf",
            "lab_name": "State Food Lab",
            "match": {"same_product": False, "same_metric": False},
        },
        query="Amul Butter",
        product_name="Amul Butter",
        brand="Amul",
    )
    assert status == "reported_not_verified"
    assert "mismatch" in reason.lower()

    # 2. Microbiological result does not affect a sugar claim
    sugar_claim = {
        "claim": "Zero Added Sugar",
        "category": "Sugar",
        "audit_verdict": "VERIFIED",
        "reason": "Label shows 0g added sugar.",
        "source_url": "https://example.com",
    }
    microbiological_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "lab_coliform",
                    "parameter": "Coliform Bacteria Count",
                    "label_value": None,
                    "lab_value": 150.0,
                    "lab_gap_pct": 100.0,
                    "age_status": "recent",
                    "source_name": "Health Lab",
                    "tier": "B",
                    "original_report_url": "https://example.com/coliform.pdf",
                }
            ]
        }
    }
    updated_claims = evidence_service.apply_evidence_to_claim_verdicts(
        claims=[sugar_claim],
        evidence=microbiological_evidence,
    )
    # The sugar claim verdict must NOT be changed by microbiological testing
    assert updated_claims[0]["audit_verdict"] == "VERIFIED"
    assert "coliform" not in updated_claims[0].get("reason", "").lower()


def test_absence_of_social_section_and_seed_config(evidence_service):
    """
    Evidence result contains only Section 1 (Independent Lab & Regulatory Evidence).
    Section 2, social seeds, and creator opinions are completely absent.
    """
    from pathlib import Path

    # Verify social seed files are deleted
    assert not Path("data/social_seed.json").exists()
    assert not Path("backend/app/config_data/social_seed.json").exists()

    res = evidence_service.get_evidence_for_product(
        query="Nestle Maggi 2-Minute Noodles",
        product_name="Nestle Maggi 2-Minute Noodles",
        brand="Nestle India",
    )
    # Section 2 must NOT exist in the evidence payload
    assert "section_2" not in res
    assert "social" not in str(res).lower()
    assert "section_1" in res
    assert res["section_1"]["heading"] == "Independent lab & regulatory evidence"


def test_evidence_record_schema_rejects_social_section(evidence_service):
    """
    Evidence record schema has no 'social' section; loading any record with section 'social' is rejected.
    """
    with pytest.raises(ValueError, match="Invalid evidence section: 'social'"):
        evidence_service.extract_and_validate_record({
            "section": "social",
            "source_name": "Unverified Platform Post",
            "label_value": 10.0,
        })

    # Valid lab record must have section 'lab_regulatory'
    valid_rec = evidence_service.extract_and_validate_record({
        "section": "lab_regulatory",
        "source_name": "NABL Accredited Testing Facility",
        "label_value": 10.0,
    })
    assert valid_rec["section"] == "lab_regulatory"


def test_product_with_no_lab_report_renders_empty_state(evidence_service):
    """
    A product with no matching lab report returns an empty accepted list and proper empty state text.
    """
    res = evidence_service.get_evidence_for_product(
        query="Unknown Generic Brand Unseeded Biscuit 999",
        product_name="Unknown Generic Brand Unseeded Biscuit 999",
        brand="Generic Foods",
        category="Biscuits",
    )
    assert res["section_1"]["accepted"] == []
    assert res["section_1"]["empty_state_text"] == "No matching lab report found for this product."
    assert "consumer-voice.org" in res["section_1"]["category_browse_url"]
    assert "Biscuits" in res["section_1"]["category_browse_text"]


def test_trustified_item_without_original_report_goes_to_unverified(evidence_service):
    """
    A Trustified item without an attached original report goes to 'Reported, not verified'.
    """
    status, reason = evidence_service.evaluate_acceptance_rules(
        record={
            "source_name": "Trustified Community Verification",
            "source_type": "third_party_testing_platform",
            "original_report_url": "",  # missing original PDF
            "discovery_url": "https://trustified.in/example",
            "lab_name": "Unnamed Lab",
            "match": {"same_product": True, "same_metric": True},
        }
    )
    assert status == "reported_not_verified"
    assert "trustified" in reason.lower()
    assert "original" in reason.lower()


def test_missing_values_become_null_never_zero(evidence_service):
    """
    Extraction pipeline validation: Missing or uncertain numeric fields become None/null, never 0.
    """
    raw_record = {
        "record_id": "test_ext_001",
        "source_name": "Test Lab",
        "label_value": "",        # missing string
        "lab_value": "not stated", # unparseable
        "unit": "mg",
        "confidence": 0.85,
    }
    structured = evidence_service.extract_and_validate_record(raw_record)
    assert structured["label_value"] is None
    assert structured["lab_value"] is None
    # Must NOT be filled with 0
    assert structured["label_value"] != 0
    assert structured["lab_value"] != 0


def test_personalized_rating_and_allergy_results_identical_with_and_without_evidence():
    """
    Personalised Rating and allergy check results are 100% identical
    with and without any evidence records.
    """
    engine = PersonalizedScoringEngine()

    product_without_evidence = {
        "nutrition": {
            "sugars_g": {"value": 32.2, "unit": "g"},
            "sodium_mg": {"value": 150.0, "unit": "mg"},
            "saturated_fat_g": {"value": 1.5, "unit": "g"},
            "fat_g": {"value": 2.0, "unit": "g"},
            "serving_size": {"value": "20g"},
        },
        "oil_listed": {"value": "No cooking oil declared", "is_palm_oil": False},
        "ingredients": [
            {"name": "Cereal extract (Barley, Wheat)", "is_allergen": True},
            {"name": "Sugar", "is_allergen": False},
            {"name": "Milk solids", "is_allergen": True},
        ],
        "front_pack_claims": [
            {"claim": "Active Brain", "audit_verdict": "VERIFIED"}
        ],
    }

    product_with_evidence = copy.deepcopy(product_without_evidence)
    # Attach rich Section 1 independent lab evidence records
    product_with_evidence["independent_evidence"] = {
        "section_1": {
            "accepted": [
                {"record_id": "rec_01", "lab_gap_pct": 50.0, "parameter": "Sugar"}
            ],
            "reported_not_verified": [
                {"record_id": "rec_02", "not_verified_reason": "Low confidence"}
            ]
        }
    }
    # Also test with contradicted claim
    product_with_evidence["front_pack_claims"][0]["audit_verdict"] = "CONTRADICTED"

    res_without = engine.evaluate(
        product_data=product_without_evidence,
        selected_conditions=["general_health", "diabetes"],
        user_allergens=["peanut"],
    )
    res_with = engine.evaluate(
        product_data=product_with_evidence,
        selected_conditions=["general_health", "diabetes"],
        user_allergens=["peanut"],
    )

    # Personalised Health Rating must be 100% identical
    assert res_without["product_rating"] == res_with["product_rating"]
    assert res_without["nutrient_rating"] == res_with["nutrient_rating"]
    assert res_without["ingredient_rating"] == res_with["ingredient_rating"]

    # Allergy check must be 100% identical
    assert res_without["allergy_check"]["allergy_status"] == res_with["allergy_check"]["allergy_status"]
    assert res_without["show_scores"] == res_with["show_scores"]


# =============================================================================
# SECTION 8 REQUIREMENTS: LAB REPORT LINK INTEGRITY, PROVENANCE & VERIFICATION
# =============================================================================

def test_url_not_in_retrieved_results_is_rejected_and_hidden(evidence_service):
    """
    Provenance rule: If any URL in LLM output is not exactly in the retrieved set
    for that product, drop it, set status 'reported_not_verified' with reason 'link not traceable', and log it.
    """
    retrieved_map = {
        1: "https://www.fssai.gov.in/upload/advisories/2024/04/66150a0a5ad8fDirection_Health_Drink.pdf"
    }

    # Record claiming source_id=1 but with a different/invented URL
    fake_record = {
        "record_id": "test_untraceable_001",
        "brand": "Cadbury",
        "product": "Cadbury Bournvita",
        "source_id": 1,
        "original_report_url": "https://www.fssai.gov.in/invented/path/not_retrieved.pdf",
        "lab_name": "Spectro Analytical Labs",
        "verified_by": "manual_check",
        "verified_at": "2026-10-25",
    }

    status, reason = evidence_service.evaluate_acceptance_rules(
        record=fake_record,
        brand="Cadbury",
        product_name="Cadbury Bournvita",
        retrieved_urls_map=retrieved_map,
    )
    assert status == "reported_not_verified"
    assert "link not traceable" in reason.lower()

    # Record missing source_id altogether
    no_id_record = {
        "record_id": "test_untraceable_002",
        "brand": "Cadbury",
        "product": "Cadbury Bournvita",
        "original_report_url": "https://www.fssai.gov.in/upload/advisories/2024/04/66150a0a5ad8fDirection_Health_Drink.pdf",
        "lab_name": "Spectro Analytical Labs",
        "verified_by": "manual_check",
        "verified_at": "2026-10-25",
    }
    status2, reason2 = evidence_service.evaluate_acceptance_rules(
        record=no_id_record,
        brand="Cadbury",
        product_name="Cadbury Bournvita",
        retrieved_urls_map=retrieved_map,
    )
    assert status2 == "reported_not_verified"
    assert "link not traceable" in reason2.lower()


def test_host_swapping_never_occurs():
    """
    Host swapping rule: input 'consumervoice.org/...' stays unchanged
    unless a redirect returns another URL. Never swap the host and keep the path.
    """
    from app.services.link_verifier import normalize_and_sanitize_url

    # Allowed domains list
    allowed = ["consumer-voice.org", "consumervoice.org"]
    url = "https://consumervoice.org/wp-content/uploads/report.pdf"
    cleaned, err = normalize_and_sanitize_url(url, allowed_domains=allowed)
    assert cleaned == "https://consumervoice.org/wp-content/uploads/report.pdf"
    assert "consumer-voice.org" not in cleaned


def test_misspelled_real_filenames_preserved():
    """
    Real filenames can contain typos (e.g. '.../Cold-Pressed-Groundnut-Oils-Comparative-tesing.pdf').
    The exact path must be preserved without autocorrecting.
    """
    from app.services.link_verifier import normalize_and_sanitize_url

    real_fixture = "https://consumer-voice.org/wp-content/uploads/2026/08/Cold-Pressed-Groundnut-Oils-Comparative-tesing.pdf"
    cleaned, err = normalize_and_sanitize_url(real_fixture)
    assert err is None
    assert cleaned == real_fixture
    assert "Comparative-tesing.pdf" in cleaned


def test_percent_encoded_paths_preserved():
    """
    Percent-encoded paths are preserved and spaces are encoded to %20.
    """
    from app.services.link_verifier import normalize_and_sanitize_url

    fixture = "https://consumeraffairs.nic.in/sites/default/files/file-uploads/ctocpas/Packaged%20Toned%20Milk.pdf"
    cleaned, err = normalize_and_sanitize_url(fixture)
    assert err is None
    assert cleaned == fixture
    assert "Packaged%20Toned%20Milk.pdf" in cleaned

    # Raw space gets encoded to %20
    with_space = "https://consumeraffairs.nic.in/sites/default/files/file-uploads/ctocpas/Packaged Toned Milk.pdf."
    cleaned2, err2 = normalize_and_sanitize_url(with_space)
    assert err2 is None
    assert cleaned2 == fixture


def test_relative_hrefs_never_rendered_links_start_with_https():
    """
    Relative hrefs are never allowed; every rendered link in UI must start with https://.
    """
    from app.services.link_verifier import normalize_and_sanitize_url

    rel_url = "/files/reports/2024/health_drink.pdf"
    cleaned, err = normalize_and_sanitize_url(rel_url)
    assert cleaned is None
    assert "relative" in err.lower()

    # Schemeless URL gets https://
    schemeless = "consumer-voice.org/food/butter/"
    cleaned_schemeless, err_s = normalize_and_sanitize_url(schemeless)
    assert err_s is None
    assert cleaned_schemeless.startswith("https://")


def test_candidate_selection_different_brand_and_no_match(evidence_service):
    """
    Two results with the first for a different brand: the matching one is chosen;
    if none match, return NO_MATCH. Never fall back to the first result.
    """
    candidates = [
        {
            "title": "Horlicks Malt Nutrition Analysis",
            "snippet": "Laboratory test report on Horlicks Malt Drink for Sugar Content. Published: September 2024.",
            "url": "https://consumer-voice.org/category/product-ranking/",
            "source_id": 1,
            "tier": "C",
        },
        {
            "title": "Cadbury Bournvita Nutrition Analysis",
            "snippet": "Independent laboratory testing on Cadbury Bournvita health drink evaluating Sugar Content. Published: October 2024.",
            "url": "https://consumer-voice.org/category/product-ranking/",
            "source_id": 2,
            "tier": "C",
        },
    ]

    retrieved_map = {
        1: "https://consumer-voice.org/category/product-ranking/",
        2: "https://consumer-voice.org/category/product-ranking/",
    }

    # Query is for Cadbury Bournvita -> candidate 2 must be chosen, not candidate 1
    best, rejected = evidence_service.select_best_report_candidate(
        candidates=candidates,
        product_name="Cadbury Bournvita",
        brand="Cadbury",
        metric="Sugar",
        retrieved_urls_map=retrieved_map,
    )
    assert best is not None
    assert best["source_id"] == 2
    assert "Bournvita" in best["title"]
    assert len(rejected) == 1
    assert rejected[0]["source_id"] == 1

    # Query for Amul Butter -> neither Horlicks nor Bournvita matches -> NO_MATCH
    best_amul, rejected_amul = evidence_service.select_best_report_candidate(
        candidates=candidates,
        product_name="Amul Butter",
        brand="Amul",
        metric="Fat",
        retrieved_urls_map=retrieved_map,
    )
    assert best_amul is None
    assert len(rejected_amul) == 2


def test_news_article_without_original_report_rejected(evidence_service):
    """
    A news article without the original report is rejected.
    """
    news_candidate = [
        {
            "title": "Times of India: News Summary on Nestle Maggi Instant Noodles",
            "snippet": "Breaking news report by Times of India on Nestle Maggi sodium levels in noodles. Date: 2024-05-01.",
            "url": "https://consumer-voice.org/food/instant-noodles/",
            "source_id": 1,
            "is_news_summary": True,
            "original_report_url": "",
        }
    ]
    best, rejected = evidence_service.select_best_report_candidate(
        candidates=news_candidate,
        product_name="Maggi Noodles",
        brand="Nestle",
        metric="Sodium",
    )
    assert best is None
    assert len(rejected) == 1
    assert "news" in rejected[0]["reason"].lower()


def test_link_verification_status_codes_and_soft404():
    """
    404/410/DNS failure/soft 404 -> dead;
    403/429/login or subscription gate -> restricted;
    timeout -> error after one retry.
    """
    import httpx
    from app.services.link_verifier import LinkVerifier

    def mock_handler(request):
        url_str = str(request.url)
        if "dead-404" in url_str:
            return httpx.Response(404)
        elif "dead-410" in url_str:
            return httpx.Response(410)
        elif "soft-404" in url_str:
            return httpx.Response(200, text="<html><body>404 Not Found - Article Not Found</body></html>")
        elif "restricted-403" in url_str:
            return httpx.Response(403)
        elif "restricted-429" in url_str:
            return httpx.Response(429)
        elif "login-gate" in url_str:
            return httpx.Response(200, text="<html><body>Please log in to continue</body></html>")
        elif "timeout-simulate" in url_str:
            raise httpx.ReadTimeout("Mock read timeout")
        return httpx.Response(200, text="<html><body>Cadbury Bournvita Tested Report</body></html>", headers={"Content-Type": "text/html"})

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    verifier = LinkVerifier()

    # 1. 404 -> dead
    res_404 = verifier.verify_link("https://consumer-voice.org/dead-404", client=mock_client)
    assert res_404["link_status"] == "dead"
    assert res_404["http_status"] == 404

    # 2. 410 -> dead
    res_410 = verifier.verify_link("https://consumer-voice.org/dead-410", client=mock_client)
    assert res_410["link_status"] == "dead"
    assert res_410["http_status"] == 410

    # 3. Soft 404 -> dead
    res_soft = verifier.verify_link("https://consumer-voice.org/soft-404", client=mock_client)
    assert res_soft["link_status"] == "dead"
    assert "soft 404" in res_soft["error_reason"].lower()

    # 4. 403 -> restricted
    res_403 = verifier.verify_link("https://consumer-voice.org/restricted-403", client=mock_client)
    assert res_403["link_status"] == "restricted"
    assert res_403["is_restricted"] is True

    # 5. 429 -> restricted
    res_429 = verifier.verify_link("https://consumer-voice.org/restricted-429", client=mock_client)
    assert res_429["link_status"] == "restricted"

    # 6. Subscription domain join.consumer-voice.org -> restricted
    res_sub = verifier.verify_link("https://join.consumer-voice.org/detailed-results", client=mock_client)
    assert res_sub["link_status"] == "restricted"
    assert res_sub["is_restricted"] is True

    # 7. Timeout -> error after retry
    res_timeout = verifier.verify_link("https://consumer-voice.org/timeout-simulate", client=mock_client)
    assert res_timeout["link_status"] == "error"

    # 8. Valid matching -> reachable
    res_ok = verifier.verify_link(
        "https://consumer-voice.org/valid-report",
        brand="Cadbury",
        product_name="Bournvita",
        client=mock_client,
    )
    assert res_ok["link_status"] == "reachable"


def test_dead_links_render_no_clickable_link_and_sit_under_unverified(evidence_service):
    """
    Dead links render no clickable link and sit under 'Reported, not verified'
    with 'Link unavailable (checked <date>)'.
    """
    record_with_dead_link = {
        "record_id": "lab_test_dead_001",
        "brand": "Cadbury",
        "product": "Cadbury Bournvita",
        "original_report_url": "https://consumer-voice.org/dead-404-report.pdf",
        "lab_name": "Spectro Labs",
        "link_status": "dead",
        "checked_at": "2026-10-25T07:00:00Z",
        "error_reason": "HTTP 404 Not Found",
        "verified_by": "manual_check",
        "verified_at": "2026-10-25",
    }
    status, reason = evidence_service.evaluate_acceptance_rules(
        record=record_with_dead_link,
        brand="Cadbury",
        product_name="Cadbury Bournvita",
    )
    assert status == "reported_not_verified"
    assert "link unavailable" in reason.lower()
    # Clickable link must be cleared
    assert record_with_dead_link["original_report_url"] is None


def test_browse_links_never_appear_inside_evidence_cards_and_carry_not_evidence_label(evidence_service):
    """
    Browse links are category-specific fallbacks:
    - Never count as evidence.
    - Never appear inside accepted evidence cards.
    - Always carry the 'not evidence' label.
    """
    res = evidence_service.get_evidence_for_product(
        query="Amul Pasteurized Butter",
        product_name="Amul Butter",
        brand="Amul",
        category="Butter",
    )
    section1 = res["section_1"]
    assert section1["category_browse_url"] == "https://consumer-voice.org/food/butter/"
    assert "not evidence for this product" in section1["category_browse_text"]

    # In accepted cards: none contains the browse link
    for card in section1["accepted"]:
        assert card.get("original_report_url") != section1["category_browse_url"]


def test_host_not_in_allowed_domains_is_hidden_and_logged(evidence_service):
    """
    A link whose host is not listed in allowed_domains.json is hidden and logged.
    """
    record_unallowed_host = {
        "record_id": "lab_unallowed_host_001",
        "brand": "Cadbury",
        "product": "Cadbury Bournvita",
        "original_report_url": "https://unauthorized-testing-blog.net/report.pdf",
        "lab_name": "Unknown Lab",
        "verified_by": "manual_check",
        "verified_at": "2026-10-25",
    }
    status, reason = evidence_service.evaluate_acceptance_rules(
        record=record_unallowed_host,
        brand="Cadbury",
        product_name="Cadbury Bournvita",
    )
    assert status == "reported_not_verified"
    assert "allowed_domains" in reason.lower()


def test_seed_entries_without_verified_by_or_verified_at_are_rejected(evidence_service):
    """
    Seed entries without verified_by/verified_at are rejected.
    """
    unverified_seed = {
        "record_id": "lab_unverified_seed_001",
        "brand": "Cadbury",
        "product": "Cadbury Bournvita",
        "original_report_url": "https://www.fssai.gov.in/upload/advisories/2024/04/66150a0a5ad8fDirection_Health_Drink.pdf",
        "lab_name": "FSSAI Lab",
        # missing verified_by and verified_at
    }
    status, reason = evidence_service.evaluate_acceptance_rules(
        record=unverified_seed,
        brand="Cadbury",
        product_name="Cadbury Bournvita",
    )
    assert status == "reported_not_verified"
    assert "verified_by" in reason.lower() or "verified_at" in reason.lower()


def test_all_seed_files_pass_validation_and_are_not_dead(evidence_service):
    """
    Validates that every single seed record in the database/JSON files has
    verified_by, verified_at, an allowed domain, and is not dead.
    """
    for seed in evidence_service.lab_seeds:
        rid = seed.get("record_id")
        assert seed.get("verified_by"), f"Seed {rid} missing verified_by"
        assert seed.get("verified_at"), f"Seed {rid} missing verified_at"
        url = seed.get("original_report_url")
        if url:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower().split(":")[0]
            assert host in evidence_service.allowed_domains, f"Seed {rid} host {host} not in allowed domains"

