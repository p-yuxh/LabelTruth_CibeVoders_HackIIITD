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


def test_creator_post_without_lab_report_only_in_section_2(evidence_service):
    """
    A creator post without a lab report appears only in Section 2 and has zero effect on verdicts.
    """
    res = evidence_service.get_evidence_for_product(
        query="Nestle Maggi 2-Minute Noodles",
        product_name="Nestle Maggi 2-Minute Noodles",
        brand="Nestle India",
    )
    section_1_ids = [x["record_id"] for x in res["section_1"]["accepted"]]
    section_2_handles = [x.get("handle") for x in res["section_2"]["items"]]

    # Nutritionist creator Pooja Malhotra is in Section 2
    assert "@nutrition_by_pooja" in section_2_handles
    # Does NOT appear in Section 1 accepted
    assert "social_maggi_instagram_001" not in section_1_ids

    # Section 2 items must carry mandatory unverified disclaimer
    for item in res["section_2"]["items"]:
        assert "Unverified opinion" in item["disclaimer"]


def test_creator_post_linking_qualifying_lab_report_adds_section_1(evidence_service):
    """
    A creator post linking a qualifying lab report adds a Section 1 record
    (with creator as discovery source) and keeps the post itself in Section 2.
    """
    res = evidence_service.get_evidence_for_product(
        query="Cadbury Bournvita",
        product_name="Cadbury Bournvita",
        brand="Cadbury / Mondelez",
    )
    # Creator Revant Himatsingka (@foodpharmer) is in Section 2
    section_2_creators = [x.get("handle") for x in res["section_2"]["items"]]
    assert "@foodpharmer" in section_2_creators

    # The linked lab report (lab_bournvita_sugar_002) is present in Section 1 accepted
    accepted_ids = [x["record_id"] for x in res["section_1"]["accepted"]]
    assert "lab_bournvita_sugar_002" in accepted_ids

    # Find the accepted report
    sugar_rep = next(x for x in res["section_1"]["accepted"] if x["record_id"] == "lab_bournvita_sugar_002")
    assert sugar_rep["status"] == "accepted"
    assert sugar_rep["original_report_url"] != ""


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
    # Attach rich Section 1 and Section 2 independent evidence records
    product_with_evidence["independent_evidence"] = {
        "section_1": {
            "accepted": [
                {"record_id": "rec_01", "lab_gap_pct": 50.0, "parameter": "Sugar"}
            ],
            "reported_not_verified": [
                {"record_id": "rec_02", "not_verified_reason": "Low confidence"}
            ]
        },
        "section_2": {
            "items": [{"creator_name": "FoodPharmer", "summary": "Unverified comment"}]
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
