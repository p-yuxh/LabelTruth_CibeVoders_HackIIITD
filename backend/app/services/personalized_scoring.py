"""
LabelTruth Personalized Scoring Engine
Implements the specification from 'LabelTruth_Personalized_Scoring_One_Page.pdf':

Key Principles:
- Formula: Personal Match Score = round(0.75 * Profile Suitability + 0.25 * Preference Match)
- Three Primary Profiles:
  1. General Health-Aware (Balanced everyday nutrition)
  2. Diabetes-Aware (Emphasis on carbohydrates, sugars, serving size & fiber)
  3. Protein-Conscious (Prioritizes protein intake against FSSAI/ICMR targets)
- Hard Exclusions: Strict Palm-Oil Avoidance triggers hard exclusion when palm oil/palmolein
  is confirmed, completely overriding match scores (protein cannot compensate).
- Keep Trust Separate: Claim Integrity Score & Evidence Completeness remain separate
  from nutritional match scores.
- Clear Regulatory & Clinical Provenance: App-defined assumptions are labeled transparently.
"""

from typing import Dict, Any, List, Optional
import logging
from app.services.reference_standards import (
    ReferenceStandardsRegistry,
    ICMR_NIN_DAILY_LIMITS,
    DIABETES_CLINICAL_GUIDANCE,
    FSSAI_CLAIM_RULES,
)

logger = logging.getLogger("labeltruth.personalized_scoring")


class PersonalizedScoringEngine:
    def __init__(self, share_of_daily: float = 0.15):
        self.registry = ReferenceStandardsRegistry(default_share_of_daily=share_of_daily)
        self.share_of_daily = share_of_daily

    def evaluate_personalized_fit(
        self,
        product_data: Dict[str, Any],
        profile_key: str = "general_health",
        strict_palm_oil_avoidance: bool = False,
        preferred_goals: Optional[List[str]] = None,
        share_of_daily: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates Profile Suitability (0-100), Preference Match (0-100),
        and Personal Match Score = round(0.75 * profile + 0.25 * preference).
        Enforces strict hard exclusions before score aggregation.
        """
        share = share_of_daily if share_of_daily is not None else self.share_of_daily
        goals = preferred_goals or []

        nutrition = product_data.get("nutrition", {})
        oil_data = product_data.get("oil_listed", {})
        contains_palm = oil_data.get("is_palm_oil", False)
        oil_value = oil_data.get("value", "None declared")

        # Extract nutritional metrics per serving
        kcal = self._get_val(nutrition.get("kcal"))
        carbs = self._get_val(nutrition.get("carbs_g"))
        sugars = self._get_val(nutrition.get("sugars_g"))
        protein = self._get_val(nutrition.get("protein_g"))
        fat = self._get_val(nutrition.get("fat_g"))
        sat_fat = self._get_val(nutrition.get("saturated_fat_g"))
        sodium = self._get_val(nutrition.get("sodium_mg"))

        # -------------------------------------------------------------
        # STEP 1: HARD EXCLUSIONS (Strict Palm Oil Avoidance)
        # -------------------------------------------------------------
        # "If palm-oil avoidance is marked 'strict,' exclude products where palm oil
        # is confirmed instead of allowing a high protein score to compensate.
        # If oil is undisclosed, show 'unknown'—do not assume it contains palm oil."
        is_hard_excluded = False
        exclusion_reason = None
        palm_oil_status = "not_detected"

        if contains_palm:
            palm_oil_status = "confirmed"
            if strict_palm_oil_avoidance:
                is_hard_excluded = True
                exclusion_reason = "Strict Palm Oil Avoidance: Product confirmed to contain Palm Oil / Palmolein. Hard exclusion overrides other nutritional scores."
        elif oil_value.lower() in ["none declared", "no cooking oil declared", "none"]:
            palm_oil_status = "unknown"
        else:
            palm_oil_status = "clean"

        # -------------------------------------------------------------
        # STEP 2: PROFILE SUITABILITY (0–100)
        # -------------------------------------------------------------
        profile_fit, profile_details = self._calculate_profile_suitability(
            profile_key=profile_key,
            kcal=kcal,
            carbs=carbs,
            sugars=sugars,
            protein=protein,
            fat=fat,
            sat_fat=sat_fat,
            sodium=sodium,
            share=share,
            contains_palm=contains_palm
        )

        # -------------------------------------------------------------
        # STEP 3: PREFERENCE MATCH (0–100)
        # -------------------------------------------------------------
        preference_fit, preference_details = self._calculate_preference_match(
            goals=goals,
            sugars=sugars,
            protein=protein,
            sat_fat=sat_fat,
            sodium=sodium,
            contains_palm=contains_palm,
            palm_oil_status=palm_oil_status
        )

        # -------------------------------------------------------------
        # STEP 4: PERSONAL MATCH SCORE (75% Profile + 25% Preference)
        # -------------------------------------------------------------
        if is_hard_excluded:
            match_score = 0
            interpretation = "EXCLUDED: Product violates your strict palm oil restriction. Nutritional benefits cannot compensate."
            status = "EXCLUDED"
        else:
            match_score = int(round(0.75 * profile_fit + 0.25 * preference_fit))
            interpretation = self._interpret_score(profile_key, match_score, profile_fit, preference_fit)
            status = "MATCHED"

        return {
            "profile_key": profile_key,
            "profile_name": self._profile_name(profile_key),
            "personal_match_score": match_score,
            "status": status,
            "formula_breakdown": f"75% × Profile Suitability ({profile_fit}) + 25% × Preference Match ({preference_fit})",
            "calculation_detail": f"0.75 × {profile_fit} + 0.25 × {preference_fit} = {round(0.75 * profile_fit + 0.25 * preference_fit, 2)} → {match_score}",
            "profile_suitability": profile_fit,
            "preference_match": preference_fit,
            "interpretation": interpretation,
            "is_hard_excluded": is_hard_excluded,
            "hard_exclusion_reason": exclusion_reason,
            "palm_oil_status": palm_oil_status,
            "share_of_daily_applied": share,
            "profile_breakdown": profile_details,
            "preference_breakdown": preference_details,
            "guardrail_note": "Scores illustrate personalization logic; they are not clinical assessments or validated medical ratings."
        }

    def evaluate_all_three_profiles(
        self,
        product_data: Dict[str, Any],
        strict_palm_oil_avoidance: bool = False,
        preferred_goals: Optional[List[str]] = None,
        share_of_daily: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates all 3 PDF profiles simultaneously so the user can compare side-by-side:
        1. General Health-Aware
        2. Diabetes-Aware
        3. Protein-Conscious
        """
        profiles = ["general_health", "diabetes_aware", "protein_conscious"]
        results = {}
        for p in profiles:
            results[p] = self.evaluate_personalized_fit(
                product_data=product_data,
                profile_key=p,
                strict_palm_oil_avoidance=strict_palm_oil_avoidance,
                preferred_goals=preferred_goals,
                share_of_daily=share_of_daily
            )
        return results

    # -------------------------------------------------------------
    # Internal Calculation Logic
    # -------------------------------------------------------------
    def _calculate_profile_suitability(
        self,
        profile_key: str,
        kcal: float,
        carbs: float,
        sugars: float,
        protein: float,
        fat: float,
        sat_fat: float,
        sodium: float,
        share: float,
        contains_palm: bool
    ) -> tuple[int, Dict[str, Any]]:
        """
        Scores 0-100 based on profile-specific nutrition targets.
        """
        sugar_benchmark = 25.0 * share  # e.g., 3.8g for 15%
        sodium_benchmark = 2000.0 * share  # e.g., 300mg for 15%
        sat_fat_benchmark = 20.0 * share  # e.g., 3.0g for 15%

        details = {}

        if profile_key == "general_health":
            # Balanced everyday nutrition
            score = 85
            # Sugar penalty
            if sugars > sugar_benchmark * 2:  # > 7.5g
                score -= 25
                details["sugar"] = f"Carries {sugars}g sugar (exceeds {round(sugar_benchmark, 1)}g per-serve benchmark)"
            elif sugars > sugar_benchmark:
                score -= 10
                details["sugar"] = f"Moderate sugar ({sugars}g)"
            else:
                details["sugar"] = f"Well within sugar limit ({sugars}g)"

            # Saturated fat penalty
            if sat_fat > sat_fat_benchmark * 1.5:  # > 4.5g
                score -= 20
                details["saturated_fat"] = f"High saturated fat ({sat_fat}g)"
            elif sat_fat > sat_fat_benchmark:
                score -= 8
                details["saturated_fat"] = f"Moderate saturated fat ({sat_fat}g)"

            # Sodium penalty
            if sodium > sodium_benchmark * 1.8:  # > 540mg
                score -= 15
                details["sodium"] = f"High sodium ({sodium}mg)"
            elif sodium > sodium_benchmark:
                score -= 6
                details["sodium"] = f"Moderate sodium ({sodium}mg)"

            # Palm oil penalty
            if contains_palm:
                score -= 15
                details["cooking_fat"] = "Fried or formulated with Palmolein/Palm Oil"

            score = max(20, min(95, score))
            return score, details

        elif profile_key == "diabetes_aware":
            # Emphasis on carbohydrates, sugars, and serving size (ADA 2026, RSSDI)
            score = 85
            # ADA snack carb recommendation: 15g
            if carbs > 30.0:
                score -= 35
                details["carbohydrates"] = f"High total carbs ({carbs}g); significant glycemic load for snack"
            elif carbs > 20.0:
                score -= 20
                details["carbohydrates"] = f"Moderate-high carbs ({carbs}g; exceeds 15g carb choice)"
            elif carbs > 15.0:
                score -= 8
                details["carbohydrates"] = f"Close to 15g carb choice limit ({carbs}g)"
            else:
                details["carbohydrates"] = f"Low carbohydrate load ({carbs}g); well-controlled"

            # Added sugar strictly discouraged
            if sugars > 6.0:
                score -= 30
                details["sugars"] = f"High sugar ({sugars}g); causes rapid postprandial glucose spike"
            elif sugars > 2.0:
                score -= 15
                details["sugars"] = f"Carries {sugars}g sugar (target < 2g per serve)"
            else:
                score += 5
                details["sugars"] = f"Minimal sugar load ({sugars}g)"

            if contains_palm:
                score -= 10
                details["fat_quality"] = "Palm oil fats increase metabolic resistance load"

            details["clinical_note"] = "App-defined assumption based on ADA Standards of Care 2026. Review serving size; score is not a safety guarantee."
            score = max(15, min(95, score))
            return score, details

        elif profile_key == "protein_conscious":
            # Prioritizes protein intake (FSSAI high protein: >= 10.8g, source: >= 5.4g)
            score = 50  # Neutral base
            if protein >= 15.0:
                score += 45
                details["protein"] = f"Exceptional protein content ({protein}g per serve)"
            elif protein >= 10.8:
                score += 35
                details["protein"] = f"Meets FSSAI 'High in Protein' threshold ({protein}g per serve)"
            elif protein >= 5.4:
                score += 15
                details["protein"] = f"Meets FSSAI 'Source of Protein' threshold ({protein}g per serve)"
            elif protein >= 3.0:
                score -= 5
                details["protein"] = f"Modest protein ({protein}g); low relative to fitness targets"
            else:
                score -= 25
                details["protein"] = f"Negligible protein ({protein}g); does not support high-protein diet goals"

            # Check protein-to-calorie density
            if kcal > 0:
                protein_kcal_pct = (protein * 4 / kcal) * 100
                if protein_kcal_pct >= 25:
                    score += 10
                    details["protein_density"] = f"High protein-to-energy ratio ({round(protein_kcal_pct, 1)}% of calories)"

            # Moderate penalties for excessive fat/sugar
            if sat_fat > 5.0:
                score -= 10
                details["fat"] = f"High saturated fat ({sat_fat}g)"
            if sugars > 10.0:
                score -= 15
                details["sugar"] = f"High sugar ({sugars}g) dilutes nutrient density"

            score = max(15, min(95, score))
            return score, details

        # Fallback
        return 75, {"note": "General profile applied"}

    def _calculate_preference_match(
        self,
        goals: List[str],
        sugars: float,
        protein: float,
        sat_fat: float,
        sodium: float,
        contains_palm: bool,
        palm_oil_status: str
    ) -> tuple[int, Dict[str, Any]]:
        """
        Scores 0-100 based on explicit user-toggled goals.
        """
        if not goals:
            # Default neutral-positive preference when no explicit goal toggled
            base_score = 75
            if contains_palm:
                base_score -= 10
            return max(50, base_score), {"default": "Standard balanced nutritional preferences"}

        goal_scores = []
        details = {}

        for g in goals:
            g_clean = g.lower().replace("-", "_")
            if g_clean in ["lower_sugar", "low_sugar"]:
                if sugars <= 2.5:
                    goal_scores.append(100)
                    details["lower_sugar"] = f"Excellent: only {sugars}g sugar"
                elif sugars <= 5.0:
                    goal_scores.append(80)
                    details["lower_sugar"] = f"Good: {sugars}g sugar (FSSAI Low Sugar threshold)"
                elif sugars <= 10.0:
                    goal_scores.append(50)
                    details["lower_sugar"] = f"Moderate: {sugars}g sugar"
                else:
                    goal_scores.append(20)
                    details["lower_sugar"] = f"Poor fit: {sugars}g sugar"

            elif g_clean in ["higher_protein", "high_protein"]:
                if protein >= 10.0:
                    goal_scores.append(100)
                    details["higher_protein"] = f"Excellent: {protein}g protein"
                elif protein >= 5.0:
                    goal_scores.append(70)
                    details["higher_protein"] = f"Acceptable: {protein}g protein"
                else:
                    goal_scores.append(30)
                    details["higher_protein"] = f"Low protein: only {protein}g"

            elif g_clean in ["low_sodium", "lower_sodium"]:
                if sodium <= 120.0:
                    goal_scores.append(100)
                    details["low_sodium"] = f"Excellent: {sodium}mg sodium (FSSAI Low Sodium)"
                elif sodium <= 300.0:
                    goal_scores.append(75)
                    details["low_sodium"] = f"Good: {sodium}mg sodium"
                else:
                    goal_scores.append(35)
                    details["low_sodium"] = f"High sodium: {sodium}mg"

            elif g_clean in ["low_saturated_fat", "low_fat"]:
                if sat_fat <= 1.5:
                    goal_scores.append(100)
                    details["low_saturated_fat"] = f"Excellent: {sat_fat}g saturated fat"
                elif sat_fat <= 3.0:
                    goal_scores.append(70)
                    details["low_saturated_fat"] = f"Moderate: {sat_fat}g saturated fat"
                else:
                    goal_scores.append(30)
                    details["low_saturated_fat"] = f"High: {sat_fat}g saturated fat"

            elif g_clean in ["palm_oil_avoidance", "no_palm_oil"]:
                if palm_oil_status == "clean" or not contains_palm:
                    goal_scores.append(100)
                    details["palm_oil_avoidance"] = "No palm oil or palmolein detected"
                elif palm_oil_status == "unknown":
                    goal_scores.append(60)
                    details["palm_oil_avoidance"] = "Oil declaration is undisclosed/unknown"
                else:
                    goal_scores.append(15)
                    details["palm_oil_avoidance"] = "Contains confirmed Palm Oil / Palmolein"

        if goal_scores:
            pref_score = int(round(sum(goal_scores) / len(goal_scores)))
        else:
            pref_score = 75

        return max(15, min(95, pref_score)), details

    def _interpret_score(self, profile: str, match: int, prof_fit: int, pref_fit: int) -> str:
        """
        Produces accurate, clinically guarded interpretation text matching the PDF examples.
        """
        if profile == "diabetes_aware":
            if match >= 75:
                return "Good alignment with carbohydrate-conscious priorities; monitor serving size."
            elif match >= 55:
                return "Review total carbohydrates and serving size; score is not a safety guarantee."
            else:
                return "High carbohydrate or sugar load; not recommended for strict glycemic management."

        elif profile == "protein_conscious":
            if match >= 75:
                return "Strong protein density aligns well with fitness & recovery targets."
            elif match >= 55:
                return "Protein amount is modest; may rank below higher-protein alternatives for this user."
            else:
                return "Negligible protein content; fails to meet personal protein priority."

        else:
            # general_health
            if match >= 75:
                return "A reasonable fit for this person's general nutritional priorities."
            elif match >= 55:
                return "Moderate fit; check saturated fat and sodium loads for frequent consumption."
            else:
                return "Significant nutritional flags (sugar, saturated fat, or sodium) for everyday diet."

    def _profile_name(self, key: str) -> str:
        names = {
            "general_health": "General Health-Aware",
            "diabetes_aware": "Diabetes-Aware",
            "protein_conscious": "Protein-Conscious",
            "hypertension_aware": "Hypertension / Low Sodium",
        }
        return names.get(key, key.replace("_", " ").title())

    def _get_val(self, metric: Any) -> float:
        if not metric:
            return 0.0
        if isinstance(metric, (int, float)):
            return float(metric)
        if isinstance(metric, dict):
            val = metric.get("value", 0.0)
            if isinstance(val, (int, float)):
                return float(val)
            try:
                import re
                m = re.search(r'[\d.]+', str(val))
                return float(m.group()) if m else 0.0
            except Exception:
                return 0.0
        return 0.0

