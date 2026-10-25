import copy
import json
from datetime import date
from pathlib import Path
import pytest
import httpx

from app.services.independent_evidence_service import IndependentEvidenceService
from app.services.link_verifier import (
    LinkVerifier,
    validate_evidence_url,
    verify_unbox_pdf_candidate,
    normalize_and_sanitize_url,
)
from app.services.personalized_scoring import PersonalizedScoringEngine


@pytest.fixture
def evidence_service():
    ref_date = date(2026, 10, 25)
    return IndependentEvidenceService(reference_date=ref_date)


# =============================================================================
# CASE 1: Fixture parsing and separate per-lab values (no averaging)
# =============================================================================
def test_case1_fixture_parsing_and_separate_per_lab_values_no_averaging():
    """
    1) Fixture parsing and separate per-lab values (no averaging):
    - trustified ghee: Eurofins, failed, batch KCGA14ECP, published 2025-07-21
    - trustified patanjali honey: Eurofins, NMR interpretation (sugar syrup)
    - unbox nakpro whey: ALS & Eurofins reports separate, protein 53.8 vs 50.44, fat 2.21 vs 3.86
    """
    seed_path = Path("data/lab_reports_seed.json")
    assert seed_path.exists(), "Seed file data/lab_reports_seed.json must exist"

    with open(seed_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # 1. Trustified Ghee
    ghee = next((r for r in fixtures if "ashirvaadghee" in r.get("original_report_url", "")), None)
    assert ghee is not None
    assert ghee["tested_by"] == "Eurofins Analytical Services India Pvt. Ltd."
    assert ghee["testing_status"] == "Failed"
    assert ghee["batch"] == "KCGA14ECP"
    assert ghee["publication_date"] == "2025-07-21"

    # 2. Trustified Patanjali Honey NMR
    honey = next((r for r in fixtures if "nmr-reports/patanjali" in r.get("original_report_url", "")), None)
    assert honey is not None
    assert honey["report_type"] == "nmr"
    assert honey["batch"] == "BCM2400071"
    assert honey["publication_date"] == "2025-04-05"
    assert "sugar syrup" in (honey.get("interpretation") or honey.get("nmr_interpretation") or "").lower()

    # 3. Unbox Nakpro Whey
    nakpro = next((r for r in fixtures if "unboxhealth" in r.get("original_report_url", "")), None)
    assert nakpro is not None
    assert nakpro.get("rating_letter") == "B" or nakpro.get("unbox_rating") == "B"
    assert nakpro.get("aggregate_score") == 78 or nakpro.get("unbox_score") == 78

    lab_reports = nakpro.get("lab_reports", [])
    assert len(lab_reports) >= 2, "Must contain separate lab reports from ALS and Eurofins"

    als_rep = next((lr for lr in lab_reports if "ALS" in lr.get("lab_name", "")), None)
    eurofins_rep = next((lr for lr in lab_reports if "Eurofins" in lr.get("lab_name", "")), None)
    assert als_rep is not None
    assert eurofins_rep is not None

    als_fat_test = next((t for t in als_rep.get("tests", []) if t.get("parameter") == "fat"), None)
    euro_fat_test = next((t for t in eurofins_rep.get("tests", []) if t.get("parameter") == "fat"), None)
    assert als_fat_test is not None
    assert euro_fat_test is not None
    assert als_fat_test["result"] == 2.21
    assert euro_fat_test["result"] == 3.86
    # No averaging should occur
    assert als_fat_test["result"] != euro_fat_test["result"]


# =============================================================================
# CASE 2: Exact 'No lab report found...' text and NO EVIDENCE on unseeded/unmatched product
# =============================================================================
def test_case2_no_lab_report_found_exact_text_and_no_evidence_on_unseeded(evidence_service):
    """
    2) If a product has no accepted record from Trustified or Unbox Health, show exactly:
    'No lab report found for this product on Trustified or Unbox Health (searched <date>). This does not mean the product is safe or unsafe.'
    Verdict stays NO EVIDENCE.
    """
    ref_date = date(2026, 10, 25)
    res = evidence_service.get_evidence_for_product(
        query="Completely Unknown Generic Snack 9999",
        product_name="Generic Snack",
        brand="Unseeded Brand",
        ref_date=ref_date,
    )
    sec1 = res["section_1"]
    assert len(sec1["accepted"]) == 0

    expected_empty_text = (
        "No lab report found for this product on Trustified or Unbox Health (searched 25 Oct 2026). "
        "This does not mean the product is safe or unsafe."
    )
    assert sec1["empty_state_text"] == expected_empty_text
    assert sec1["coverage_badge"]["status"] == "SEARCHED_NONE_FOUND"

    # Verdict application defaults to / stays NO EVIDENCE
    claims = [
        {"claim": "Rich in Dietary Fiber", "category": "Fiber", "audit_verdict": "NO EVIDENCE"}
    ]
    updated = evidence_service.apply_evidence_to_claim_verdicts(claims, res)
    assert updated[0]["audit_verdict"] == "NO EVIDENCE"


# =============================================================================
# CASE 3: Rejection of homepage, index, brand, category, compare URLs
# =============================================================================
def test_case3_rejection_of_homepage_index_brand_category_compare_urls():
    """
    3) Rejection of homepage, index, brand, category, compare URLs:
    Never use as an evidence link: a homepage, index (/passandfail, /nmr-reports, /explore),
    brand page, category page, collection, compare page or search page.
    """
    # Trustified home & indexes
    assert not validate_evidence_url("https://www.trustified.in/")[0]
    assert not validate_evidence_url("https://www.trustified.in/passandfail")[0]
    assert not validate_evidence_url("https://www.trustified.in/passandfail/")[0]
    assert not validate_evidence_url("https://www.trustified.in/nmr-reports")[0]

    # Disallowed host shop.trustified.in
    is_valid_shop, reason_shop = validate_evidence_url("https://shop.trustified.in/products/ghee")
    assert not is_valid_shop
    assert "disallowed host" in reason_shop.lower()

    # Unbox home & indexes
    assert not validate_evidence_url("https://www.unboxhealth.in/")[0]
    assert not validate_evidence_url("https://www.unboxhealth.in/explore")[0]
    assert not validate_evidence_url("https://www.unboxhealth.in/explore/brand-list")[0]
    assert not validate_evidence_url("https://www.unboxhealth.in/explore/category/dairy")[0]
    assert not validate_evidence_url("https://www.unboxhealth.in/compare")[0]
    assert not validate_evidence_url("https://www.unboxhealth.in/search?q=protein")[0]

    # Valid URLs must pass
    assert validate_evidence_url("https://www.trustified.in/passandfail/ashirvaadghee")[0]
    assert validate_evidence_url("https://www.trustified.in/nmr-reports/patanjali")[0]
    assert validate_evidence_url("https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30")[0]
    assert validate_evidence_url("https://unboxhealth-production.s3.amazonaws.com/unbox/media/Public_Documents/nakpro.pdf")[0]


# =============================================================================
# CASE 4: Redirect to '/' or shallower path is dead; wrong path pattern is dead
# =============================================================================
def test_case4_redirect_to_shallower_path_or_wrong_pattern_is_dead():
    """
    4) Redirect to '/' or shallower path is dead; wrong path pattern is dead.
    """
    def mock_handler(request):
        url_str = str(request.url)
        if "redirect-to-root" in url_str:
            return httpx.Response(302, headers={"Location": "https://www.trustified.in/"})
        elif "redirect-to-shallower" in url_str:
            return httpx.Response(302, headers={"Location": "https://www.unboxhealth.in/explore"})
        elif "redirect-to-compare" in url_str:
            return httpx.Response(302, headers={"Location": "https://www.unboxhealth.in/compare"})
        elif "https://www.trustified.in/" == url_str:
            return httpx.Response(200, text="<html><body>Homepage</body></html>")
        elif "https://www.unboxhealth.in/explore" == url_str:
            return httpx.Response(200, text="<html><body>Explore Index</body></html>")
        elif "https://www.unboxhealth.in/compare" == url_str:
            return httpx.Response(200, text="<html><body>Compare</body></html>")
        return httpx.Response(200, text="<html><body>Valid Product Name</body></html>")

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    verifier = LinkVerifier()

    # 1. Redirect to root -> dead
    res1 = verifier.verify_link(
        "https://www.trustified.in/passandfail/redirect-to-root",
        client=mock_client,
        strict_evidence_rules=True,
    )
    assert res1["link_status"] == "dead"
    assert "shallower path" in res1["error_reason"].lower() or "root" in res1["error_reason"].lower()

    # 2. Redirect to shallower path -> dead
    res2 = verifier.verify_link(
        "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30?sim=redirect-to-shallower",
        client=mock_client,
        strict_evidence_rules=True,
    )
    assert res2["link_status"] == "dead"

    # 3. Redirect to wrong pattern (/compare) -> dead
    res3 = verifier.verify_link(
        "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30?sim=redirect-to-compare",
        client=mock_client,
        strict_evidence_rules=True,
    )
    assert res3["link_status"] == "dead"


# =============================================================================
# CASE 5: Unbox UUID mismatch is dead; PDF candidate returning HTML is not shown; verified PDF is shown
# =============================================================================
def test_case5_unbox_uuid_mismatch_and_pdf_candidate_verification():
    """
    5) Unbox UUID mismatch is dead; PDF candidate returning HTML is not shown; verified PDF is shown.
    """
    # 1. UUID mismatch in HTML
    html_with_mismatch = """
    <html>
      <head>
        <link rel="canonical" href="https://www.unboxhealth.in/explore/product/nakpro/00000000-0000-0000-0000-000000000000" />
      </head>
      <body><h1>Nakpro Whey</h1></body>
    </html>
    """
    def mock_unbox_handler(request):
        return httpx.Response(200, text=html_with_mismatch, headers={"Content-Type": "text/html"})

    client_mismatch = httpx.Client(transport=httpx.MockTransport(mock_unbox_handler))
    verifier = LinkVerifier()
    res = verifier.verify_link(
        "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30",
        client=client_mismatch,
        strict_evidence_rules=True,
    )
    assert res["link_status"] == "dead"
    assert "uuid mismatch" in res["error_reason"].lower()

    # 2. PDF candidate returning HTML is not shown
    def mock_pdf_html_handler(request):
        return httpx.Response(200, text="<html><body>403 Forbidden Error XML</body></html>", headers={"Content-Type": "text/html"})

    client_pdf_html = httpx.Client(transport=httpx.MockTransport(mock_pdf_html_handler))
    page_html = '<img src="/unbox/media/product_variant/all_images/Nakpro-Whey.webp" />'
    cand_url, err = verify_unbox_pdf_candidate(page_html, client=client_pdf_html)
    assert cand_url is None
    assert "require an unbox health login" in err.lower()

    # 3. Verified PDF returning application/pdf starting with %PDF is shown
    def mock_pdf_ok_handler(request):
        return httpx.Response(
            200,
            content=b"%PDF-1.4\n1 0 obj\nEurofins ALS Analytical Lab Report Nakpro\nendobj",
            headers={"Content-Type": "application/pdf"}
        )

    client_pdf_ok = httpx.Client(transport=httpx.MockTransport(mock_pdf_ok_handler))
    cand_url_ok, err_ok = verify_unbox_pdf_candidate(page_html, client=client_pdf_ok)
    assert cand_url_ok is not None
    assert cand_url_ok.endswith("Nakpro-Whey.pdf")
    assert err_ok is None


# =============================================================================
# CASE 6: Labs disagreeing on fat (2.21 vs 3.86) -> no CONTRADICTED, reason 'labs disagree'; non-accredited tests cannot set verdict
# =============================================================================
def test_case6_labs_disagree_on_fat_no_contradicted_and_non_accredited(evidence_service):
    """
    6) Labs disagreeing on fat (2.21 vs 3.86) -> no CONTRADICTED, reason 'labs disagree';
       non-accredited tests cannot set verdict.
    """
    claim_fat = {
        "claim": "Only 3g Total Fat per serving",
        "category": "Fat",
        "audit_verdict": "VERIFIED",
    }

    # Evidence where ALS and Eurofins disagree materially on fat
    disagreeing_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "nakpro_fat_test",
                    "parameter": "Total Fat",
                    "label_value": 3.0,
                    "lab_value": 2.21,
                    "labs_disagree": True,
                    "disagreement_summary": "ALS 2.21 vs Eurofins 3.86 g/100g",
                    "accreditation_checked": True,
                    "age_status": "recent",
                    "source_name": "Unbox Health",
                    "tier": "C",
                    "original_report_url": "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30",
                }
            ]
        }
    }

    updated = evidence_service.apply_evidence_to_claim_verdicts([claim_fat], disagreeing_evidence)
    assert updated[0]["audit_verdict"] == "NO EVIDENCE"
    assert "labs disagree" in updated[0]["reason"].lower()

    # Non-accredited test: cannot produce CONTRADICTED
    claim_protein = {
        "claim": "High Protein 50g",
        "category": "Protein",
        "audit_verdict": "VERIFIED",
    }
    non_accredited_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "non_acc_protein",
                    "parameter": "Protein Content",
                    "label_value": 50.0,
                    "lab_value": 25.0,  # 50% deficit
                    "lab_gap_pct": -50.0,
                    "labs_disagree": False,
                    "accreditation_checked": False,  # Non-accredited
                    "age_status": "recent",
                    "source_name": "Private Unaccredited Lab",
                    "tier": "C",
                    "original_report_url": "https://www.trustified.in/passandfail/someproduct",
                }
            ]
        }
    }
    updated_protein = evidence_service.apply_evidence_to_claim_verdicts([claim_protein], non_accredited_evidence)
    assert updated_protein[0]["audit_verdict"] != "CONTRADICTED"
    assert "non-accredited" in updated_protein[0]["reason"].lower()


# =============================================================================
# CASE 7: Page-vs-PDF mismatch flagged and PDF values win
# =============================================================================
def test_case7_page_vs_pdf_mismatch_flagged_and_pdf_values_win(evidence_service):
    """
    7) Page-vs-PDF mismatch flagged and PDF values win.
    """
    claim = {
        "claim": "50g Protein Formula",
        "category": "Protein",
        "audit_verdict": "NO EVIDENCE",
    }
    mismatch_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "test_mismatch",
                    "parameter": "Protein Content",
                    "label_value": 50.0,
                    "lab_value": 40.0,  # Page summary says 40.0 (-20%)
                    "lab_gap_pct": -20.0,
                    "page_vs_pdf_mismatch": True,
                    "pdf_lab_value": 52.0,  # PDF actual value is 52.0 (+4%, within 15% tolerance)
                    "pdf_lab_gap_pct": 4.0,
                    "accreditation_checked": True,
                    "age_status": "recent",
                    "source_name": "Unbox Health",
                    "tier": "C",
                    "original_report_url": "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30",
                }
            ]
        }
    }

    updated = evidence_service.apply_evidence_to_claim_verdicts([claim], mismatch_evidence)
    # PDF values win: +4% gap is within tolerance -> VERIFIED (not CONTRADICTED)
    assert updated[0]["audit_verdict"] == "VERIFIED"


# =============================================================================
# CASE 8: Missing values are null; image-only Trustified sections never feed verdicts
# =============================================================================
def test_case8_missing_values_null_and_image_only_never_feed_verdicts(evidence_service):
    """
    8) Missing values are null; image-only Trustified sections never feed verdicts.
    """
    rec = evidence_service.extract_and_validate_record({
        "section": "lab_regulatory",
        "source_name": "Trustified",
        "label_value": "not stated",
        "lab_value": "",
        "original_report_url": "https://www.trustified.in/passandfail/ashirvaadghee",
        "verified_by": "analyst",
        "verified_at": "2026-10-25",
    })
    assert rec["label_value"] is None
    assert rec["lab_value"] is None
    assert rec["lab_gap_pct"] is None

    # Image-only section
    image_only_claim = {
        "claim": "Heavy Metals Free",
        "category": "Purity",
        "audit_verdict": "NO EVIDENCE",
    }
    image_only_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "trustified_heavy_metals",
                    "parameter": "Purity",
                    "status": "image_only",
                    "needs_review": True,
                    "original_report_url": "https://www.trustified.in/passandfail/ashirvaadghee",
                }
            ]
        }
    }
    updated = evidence_service.apply_evidence_to_claim_verdicts([image_only_claim], image_only_evidence)
    # Stays unchanged / NO EVIDENCE
    assert updated[0]["audit_verdict"] == "NO EVIDENCE"


# =============================================================================
# CASE 9: Trustified NMR and Unbox letter ratings never set a verdict
# =============================================================================
def test_case9_trustified_nmr_and_unbox_letter_ratings_never_set_verdict(evidence_service):
    """
    9) Trustified NMR and Unbox letter ratings never set a verdict.
    """
    claim = {
        "claim": "100% Pure Honey",
        "category": "Purity",
        "audit_verdict": "VERIFIED",
    }
    nmr_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "trustified_nmr",
                    "parameter": "Purity",
                    "report_type": "nmr",
                    "interpretation": "adulterated with sugar syrup",
                    "original_report_url": "https://www.trustified.in/nmr-reports/patanjali",
                }
            ]
        }
    }
    updated_nmr = evidence_service.apply_evidence_to_claim_verdicts([claim], nmr_evidence)
    assert updated_nmr[0]["audit_verdict"] != "CONTRADICTED"
    assert "informational" in updated_nmr[0]["reason"].lower()

    # Unbox letter rating
    unbox_evidence = {
        "section_1": {
            "accepted": [
                {
                    "record_id": "unbox_rating_only",
                    "parameter": "Unbox Rating",
                    "is_letter_rating": True,
                    "unbox_rating": "B",
                    "original_report_url": "https://www.unboxhealth.in/explore/product/nakpro/eec64a4a-fe84-4e6e-8964-4aedaa7f1d30",
                }
            ]
        }
    }
    updated_unbox = evidence_service.apply_evidence_to_claim_verdicts([claim], unbox_evidence)
    assert updated_unbox[0]["audit_verdict"] != "CONTRADICTED"


# =============================================================================
# CASE 10: Disabled sources produce no evidence records
# =============================================================================
def test_case10_disabled_sources_produce_no_evidence_records(evidence_service):
    """
    10) Disabled sources (Consumer VOICE, Ministry of Consumer Affairs, FSSAI as a lab source,
        YouTube, social media) produce no evidence records.
    """
    for disabled_name in ["Consumer VOICE", "Ministry of Consumer Affairs", "FSSAI (as a lab source)", "YouTube", "Social Media"]:
        status, reason = evidence_service.evaluate_acceptance_rules(
            record={
                "record_id": "test_disabled",
                "source_name": disabled_name,
                "product": "Test Product",
                "brand": "Test Brand",
                "original_report_url": "https://consumer-voice.org/report.pdf",
            }
        )
        assert status == "reported_not_verified"
        assert "disabled" in reason.lower() or "rejected" in reason.lower() or "not listed" in reason.lower()


# =============================================================================
# CASE 11: Personalised Rating, claim verdict thresholds, and allergy results unchanged
# =============================================================================
def test_case11_personalized_rating_allergy_and_thresholds_unchanged():
    """
    11) Personalised Rating, claim verdict thresholds, and allergy results are unchanged.
    """
    scorer = PersonalizedScoringEngine()
    product_data = {
        "nutrition": {
            "sugars_g": {"value": 25.0},
            "sodium_mg": {"value": 450.0},
            "fat_g": {"value": 15.0},
        },
        "ingredients": ["Whole Wheat Flour", "Peanut Oil", "Sugar"],
        "oil_listed": {"value": "Peanut Oil"},
    }

    # 1. Rating with no allergens
    res1 = scorer.evaluate(
        product_data,
        user_allergens=[],
        selected_conditions=["general_health"],
    )
    score1 = res1.get("product_rating")
    assert score1 is not None
    assert 1.0 <= score1 <= 10.0
    assert res1["allergy_check"]["allergy_status"] == "NONE FOUND"

    # 2. Rating with matching allergen (peanuts)
    res2 = scorer.evaluate(
        product_data,
        user_allergens=["peanuts"],
        selected_conditions=["general_health"],
    )
    assert res2["allergy_check"]["allergy_status"] == "NOT SAFE FOR YOU"
    assert res2["show_scores"] is False
    assert res2["product_rating"] is None
