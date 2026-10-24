"""
Official Reference Standards & Regulatory Knowledge Base
Primary sources for Indian food safety, dietary guidance, diabetes nutrition,
and global food standards.

Every standard stores:
- source_name
- source_url
- access_date
- statutory_status ('Statutory Gazette Standard', 'Official Dietary Guideline', 'App-Defined Clinical Assumption', 'Reported Third-Party Evidence')
- daily_limit / threshold_value
- calculation notes
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

ACCESS_DATE = "2026-10-24"


@dataclass
class ReferenceStandardCitation:
    id: str
    parameter: str
    benchmark_type: str  # 'claim_rule', 'daily_limit', 'clinical_guidance', 'third_party_evidence'
    value: Any
    unit: str
    source_name: str
    source_url: str
    access_date: str
    statutory_status: str
    notes: str


# ---------------------------------------------------------------------------
# 1. INDIA: STATUTORY CLAIM RULES (FSSAI)
# ---------------------------------------------------------------------------
FSSAI_CLAIM_RULES: Dict[str, ReferenceStandardCitation] = {
    "zero_sugar": ReferenceStandardCitation(
        id="fssai_zero_sugar",
        parameter="Zero Sugar / Sugar-Free",
        benchmark_type="claim_rule",
        value=0.5,
        unit="g / 100g or 100ml",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="Maximum 0.5 g sugars per 100 g (solids) or 100 ml (liquids) to claim 'Sugar-Free' or 'Zero Sugar'."
    ),
    "low_sugar": ReferenceStandardCitation(
        id="fssai_low_sugar",
        parameter="Low Sugar",
        benchmark_type="claim_rule",
        value=5.0,
        unit="g / 100g (solids), 2.5 g / 100ml (liquids)",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="<= 5 g sugar per 100 g for solids, <= 2.5 g sugar per 100 ml for liquids."
    ),
    "zero_trans_fat": ReferenceStandardCitation(
        id="fssai_zero_trans_fat",
        parameter="Zero Trans Fat / Trans-Fat Free",
        benchmark_type="claim_rule",
        value=0.2,
        unit="g / serving",
        source_name="FSS (Labelling and Display) Regulations 2020 Gazette Notification",
        source_url="https://www.fssai.gov.in/upload/notifications/2020/12/5fd87c6a0f6adGazette_Notification_Labelling_Display_14_12_2020.pdf",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="Permitted only where trans fat is less than 0.2 g per serving and saturated fat <= 1.5 g / 100g."
    ),
    "low_saturated_fat": ReferenceStandardCitation(
        id="fssai_low_saturated_fat",
        parameter="Low Saturated Fat",
        benchmark_type="claim_rule",
        value=1.5,
        unit="g / 100g (solids), 0.75 g / 100ml (liquids)",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="<= 1.5 g saturated fat per 100 g for solids, <= 0.75 g per 100 ml for liquids, and not more than 10% of total energy."
    ),
    "low_sodium": ReferenceStandardCitation(
        id="fssai_low_sodium",
        parameter="Low Sodium / Low Salt",
        benchmark_type="claim_rule",
        value=120.0,
        unit="mg / 100g",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="<= 120 mg sodium (0.3 g salt equivalent) per 100 g."
    ),
    "high_protein": ReferenceStandardCitation(
        id="fssai_high_protein",
        parameter="High Protein / Rich in Protein",
        benchmark_type="claim_rule",
        value=10.8,
        unit="g / 100g (or 20% of adult daily RDA)",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="Product must provide at least 20% of adult RDA of protein (>= 10.8 g based on 54 g RDA) per 100 g."
    ),
    "source_of_protein": ReferenceStandardCitation(
        id="fssai_source_protein",
        parameter="Source of Protein",
        benchmark_type="claim_rule",
        value=5.4,
        unit="g / 100g (or 10% of adult daily RDA)",
        source_name="Food Safety and Standards (Advertising and Claims) Regulations, 2018",
        source_url="https://www.fssai.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="Statutory Gazette Standard",
        notes="Product must provide at least 10% of adult RDA of protein (>= 5.4 g) per 100 g."
    ),
}


# ---------------------------------------------------------------------------
# 2. INDIA: GENERAL HEALTHY LIMITS (ICMR-NIN 2024 Dietary Guidelines)
# ---------------------------------------------------------------------------
ICMR_NIN_DAILY_LIMITS: Dict[str, ReferenceStandardCitation] = {
    "salt_daily": ReferenceStandardCitation(
        id="icmr_salt_daily",
        parameter="Daily Salt (Sodium) Upper Limit",
        benchmark_type="daily_limit",
        value=5.0,
        unit="g / day (Sodium: 2000 mg / day)",
        source_name="ICMR-NIN Dietary Guidelines for Indians, 2024",
        source_url="https://www.nin.res.in",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Maximum salt intake of 5 g/day (2000 mg sodium) for healthy adults to prevent hypertension and stroke."
    ),
    "sugar_daily": ReferenceStandardCitation(
        id="icmr_sugar_daily",
        parameter="Daily Added Sugar Upper Limit",
        benchmark_type="daily_limit",
        value=25.0,
        unit="g / day (~5% of daily energy intake)",
        source_name="ICMR-NIN Dietary Guidelines for Indians, 2024",
        source_url="https://www.nin.res.in",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Upper limit of 25 g/day added sugar for adults; foods high in free sugars classified as HFSS (High Fat, Sugar, Salt)."
    ),
    "total_fat_daily": ReferenceStandardCitation(
        id="icmr_total_fat_daily",
        parameter="Total Fat Percentage of Energy",
        benchmark_type="daily_limit",
        value=30.0,
        unit="% of daily total energy",
        source_name="ICMR-NIN Dietary Guidelines for Indians, 2024",
        source_url="https://www.nin.res.in",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Total dietary fat should not exceed 30% of energy (~50-60 g/day for a 2000 kcal diet); vegetable oils high in saturated fats (palm oil/palmolein) should be restricted."
    ),
    "saturated_fat_daily": ReferenceStandardCitation(
        id="icmr_saturated_fat_daily",
        parameter="Saturated Fat Percentage of Energy",
        benchmark_type="daily_limit",
        value=8.0,
        unit="% of daily total energy (~18-20 g/day)",
        source_name="ICMR-NIN Dietary Guidelines for Indians, 2024",
        source_url="https://www.nin.res.in",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Saturated fatty acid intake must be kept under 8-10% of total daily energy."
    ),
    "dietary_fibre_daily": ReferenceStandardCitation(
        id="icmr_fibre_daily",
        parameter="Minimum Daily Dietary Fiber",
        benchmark_type="daily_limit",
        value=30.0,
        unit="g / day",
        source_name="ICMR-NIN Dietary Guidelines for Indians, 2024",
        source_url="https://www.nin.res.in",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Recommended minimum 30 g/day of dietary fibre from whole grains, legumes, vegetables, and seeds."
    ),
}


# ---------------------------------------------------------------------------
# 3. DIABETES-AWARE GUIDELINES (ADA 2026, RSSDI, ICMR-INDIAB)
# ---------------------------------------------------------------------------
DIABETES_CLINICAL_GUIDANCE: Dict[str, ReferenceStandardCitation] = {
    "snack_carbs_per_serving": ReferenceStandardCitation(
        id="ada_snack_carbs",
        parameter="Carbohydrate per Snack Serving (Diabetes Profile)",
        benchmark_type="clinical_guidance",
        value=15.0,
        unit="g / serving",
        source_name="ADA Standards of Care in Diabetes 2026 (Nutrition Section)",
        source_url="https://diabetesjournals.org/care/issue/49/Supplement_1",
        access_date=ACCESS_DATE,
        statutory_status="App-Defined Clinical Assumption",
        notes="App-defined assumption based on 1 carbohydrate choice (15 g carbs); statutory authorities do not publish per-product limits. Review serving size carefully."
    ),
    "added_sugar_diabetes": ReferenceStandardCitation(
        id="ada_added_sugar_diabetes",
        parameter="Added Sugar Target (Diabetes Profile)",
        benchmark_type="clinical_guidance",
        value=2.0,
        unit="g / serving",
        source_name="ADA Standards of Care 2026 & RSSDI Clinical Guidelines",
        source_url="https://www.rssdi.in",
        access_date=ACCESS_DATE,
        statutory_status="App-Defined Clinical Assumption",
        notes="App-defined threshold. Both ADA and RSSDI advise strictly minimizing sugar-sweetened beverages and added sucrose/fructose to prevent acute glycemic spikes."
    ),
    "fibre_diabetes_bonus": ReferenceStandardCitation(
        id="icmr_indiab_fibre",
        parameter="Dietary Fiber Minimum per Serving",
        benchmark_type="clinical_guidance",
        value=3.0,
        unit="g / serving",
        source_name="ICMR-INDIAB Study & Diabetes Nutrition Guidance",
        source_url="https://www.icmr.gov.in",
        access_date=ACCESS_DATE,
        statutory_status="App-Defined Clinical Assumption",
        notes="Higher viscous soluble fiber blunts postprandial glucose excursions in individuals with insulin resistance."
    ),
}


# ---------------------------------------------------------------------------
# 4. GLOBAL REFERENCES (WHO, EFSA, US FDA)
# ---------------------------------------------------------------------------
GLOBAL_REFERENCES: Dict[str, ReferenceStandardCitation] = {
    "who_sugar": ReferenceStandardCitation(
        id="who_sugar",
        parameter="WHO Free Sugars Intake Guideline",
        benchmark_type="daily_limit",
        value=25.0,
        unit="g / day",
        source_name="WHO Guideline: Sugars intake for adults and children",
        source_url="https://www.who.int",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="WHO strongly recommends reducing intake of free sugars to less than 10% of total energy, with a conditional recommendation to drop below 5% (25 g/day) for additional health benefits."
    ),
    "who_sodium": ReferenceStandardCitation(
        id="who_sodium",
        parameter="WHO Sodium Intake Guideline",
        benchmark_type="daily_limit",
        value=2000.0,
        unit="mg / day",
        source_name="WHO Guideline: Sodium intake for adults and children",
        source_url="https://www.who.int",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="WHO recommends a reduction in sodium intake to < 2 g/day (equivalent to 5 g salt/day) in adults."
    ),
    "efsa_sweeteners": ReferenceStandardCitation(
        id="efsa_sweeteners",
        parameter="EFSA Artificial Sweeteners Safety Assessment",
        benchmark_type="clinical_guidance",
        value="ADI compliance",
        unit="mg / kg body weight / day",
        source_name="EFSA (European Food Safety Authority) Sweetener Evaluations",
        source_url="https://www.efsa.europa.eu",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Non-sugar sweeteners (Aspartame, Acesulfame K, Sucralose) are assessed as safe within established Acceptable Daily Intake (ADI) levels; however, WHO recommends not using NSS as a means of achieving weight control."
    ),
    "us_fda_comparison": ReferenceStandardCitation(
        id="fda_labeling",
        parameter="US FDA Daily Value Benchmarks (For International Comparison)",
        benchmark_type="daily_limit",
        value="50g added sugar / 2300mg sodium",
        unit="daily value",
        source_name="US FDA Food Labeling & Nutrition",
        source_url="https://www.fda.gov",
        access_date=ACCESS_DATE,
        statutory_status="Official Dietary Guideline",
        notes="Referenced solely for international nutritional comparisons against Indian FSSAI benchmarks."
    ),
}


# ---------------------------------------------------------------------------
# 5. LAB TEST / THIRD-PARTY EVIDENCE (Trustified, Consumer Voice)
# ---------------------------------------------------------------------------
THIRD_PARTY_LAB_FRAMEWORK = {
    "source_name": "Reported Third-Party Laboratory Evidence (Trustified / Consumer Voice)",
    "source_url": "https://consumer-voice.org",
    "access_date": ACCESS_DATE,
    "statutory_status": "Reported Third-Party Evidence",
    "disclaimer": "Reported third-party evidence represents independent laboratory test findings published by accredited consumer research groups; it does not constitute official statutory proof of regulatory non-compliance or wrongdoing.",
}


class ReferenceStandardsRegistry:
    """
    Registry and calculation engine for verified dietary standards.
    Converts per-day guidelines to per-serving thresholds using an open, configurable share of daily allowance.
    """

    def __init__(self, default_share_of_daily: float = 0.15):
        # Default: 15% of daily allowance per packaged food serving/snack
        self.default_share_of_daily = default_share_of_daily

    def get_per_serving_benchmark(self, parameter: str, share_of_daily: Optional[float] = None) -> Dict[str, Any]:
        """
        Converts daily guidelines to per-serving limits:
        per_serving_limit = daily_limit * share_of_daily
        """
        share = share_of_daily if share_of_daily is not None else self.default_share_of_daily
        share_pct = int(round(share * 100))

        if parameter == "sugar":
            citation = ICMR_NIN_DAILY_LIMITS["sugar_daily"]
            per_serving_val = round(citation.value * share, 1)  # 25g * 0.15 = 3.8g
            return {
                "parameter": "Added Sugar",
                "per_serving_limit": per_serving_val,
                "daily_limit": citation.value,
                "unit": "g",
                "share_of_daily": share,
                "share_percentage": f"{share_pct}%",
                "source_name": citation.source_name,
                "source_url": citation.source_url,
                "access_date": citation.access_date,
                "statutory_status": citation.statutory_status,
                "calculation_disclosure": f"Per-serving limit ({per_serving_val}g) calculated as {share_pct}% configurable share of ICMR-NIN 2024 daily limit ({citation.value}g/day).",
            }

        elif parameter == "sodium":
            citation = ICMR_NIN_DAILY_LIMITS["salt_daily"]
            daily_na = 2000.0  # 5g salt = 2000mg sodium
            per_serving_val = round(daily_na * share, 0)  # 2000mg * 0.15 = 300mg
            return {
                "parameter": "Sodium",
                "per_serving_limit": per_serving_val,
                "daily_limit": daily_na,
                "unit": "mg",
                "share_of_daily": share,
                "share_percentage": f"{share_pct}%",
                "source_name": citation.source_name,
                "source_url": citation.source_url,
                "access_date": citation.access_date,
                "statutory_status": citation.statutory_status,
                "calculation_disclosure": f"Per-serving limit ({per_serving_val}mg) calculated as {share_pct}% configurable share of ICMR-NIN 2024 / WHO daily sodium recommendation (2000mg/day).",
            }

        elif parameter == "saturated_fat":
            daily_sat_fat = 20.0  # ~20g saturated fat in 2000 kcal diet
            citation = ICMR_NIN_DAILY_LIMITS["saturated_fat_daily"]
            per_serving_val = round(daily_sat_fat * share, 1)  # 20g * 0.15 = 3.0g
            return {
                "parameter": "Saturated Fat",
                "per_serving_limit": per_serving_val,
                "daily_limit": daily_sat_fat,
                "unit": "g",
                "share_of_daily": share,
                "share_percentage": f"{share_pct}%",
                "source_name": citation.source_name,
                "source_url": citation.source_url,
                "access_date": citation.access_date,
                "statutory_status": citation.statutory_status,
                "calculation_disclosure": f"Per-serving limit ({per_serving_val}g) calculated as {share_pct}% configurable share of ICMR-NIN 2024 saturated fat recommendation (~20g/day).",
            }

        elif parameter == "diabetes_carbs":
            citation = DIABETES_CLINICAL_GUIDANCE["snack_carbs_per_serving"]
            return {
                "parameter": "Snack Carbohydrates",
                "per_serving_limit": citation.value,
                "unit": citation.unit,
                "source_name": citation.source_name,
                "source_url": citation.source_url,
                "access_date": citation.access_date,
                "statutory_status": citation.statutory_status,
                "calculation_disclosure": "App-defined clinical assumption based on ADA Standards of Care 2026 carbohydrate exchange (15g); statutory agencies do not publish product-specific limits.",
            }

        return {}

    def get_all_citations_for_product(self, claims: List[Dict], ingredients: List[Dict]) -> List[Dict[str, Any]]:
        """
        Gathers all applicable citations with primary URLs and access dates for a given product audit.
        """
        citations = []
        
        # 1. ICMR-NIN General Nutrition
        for key in ["salt_daily", "sugar_daily", "total_fat_daily", "dietary_fibre_daily"]:
            citations.append(asdict(ICMR_NIN_DAILY_LIMITS[key]))
        
        # 2. ADA / RSSDI Diabetes
        for key in ["snack_carbs_per_serving", "added_sugar_diabetes", "icmr_indiab_fibre"]:
            if key in DIABETES_CLINICAL_GUIDANCE:
                citations.append(asdict(DIABETES_CLINICAL_GUIDANCE[key]))
        
        # 3. FSSAI Claim Rules
        claim_texts = " ".join([c.get("claim", "") for c in claims]).lower()
        if any(w in claim_texts for w in ["sugar", "sweet"]):
            citations.append(asdict(FSSAI_CLAIM_RULES["zero_sugar"]))
            citations.append(asdict(FSSAI_CLAIM_RULES["low_sugar"]))
        if any(w in claim_texts for w in ["trans", "fat"]):
            citations.append(asdict(FSSAI_CLAIM_RULES["zero_trans_fat"]))
            citations.append(asdict(FSSAI_CLAIM_RULES["low_saturated_fat"]))
        if any(w in claim_texts for w in ["protein", "power"]):
            citations.append(asdict(FSSAI_CLAIM_RULES["high_protein"]))
            citations.append(asdict(FSSAI_CLAIM_RULES["source_of_protein"]))
        
        # 4. Global Standards
        citations.append(asdict(GLOBAL_REFERENCES["who_sugar"]))
        citations.append(asdict(GLOBAL_REFERENCES["who_sodium"]))

        # Check for artificial sweeteners to attach EFSA citation
        ing_text = " ".join([i.get("name", "") for i in ingredients]).lower()
        if any(s in ing_text for s in ["aspartame", "acesulfame", "sucralose", "stevia", "saccharin", "950", "951", "955"]):
            citations.append(asdict(GLOBAL_REFERENCES["efsa_sweeteners"]))

        return citations

