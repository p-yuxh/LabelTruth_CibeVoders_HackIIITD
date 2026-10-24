import json
import logging
import math
import os
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("labeltruth.personalized_scoring")

# Paths to statutory configuration files
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_data")
PROFILES_CONFIG_PATH = os.path.join(CONFIG_DIR, "nutrition_profiles.json")
INGREDIENTS_CONFIG_PATH = os.path.join(CONFIG_DIR, "ingredient_risks.json")


def load_profiles_config() -> Dict[str, Any]:
    try:
        with open(PROFILES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("profiles", {})
    except Exception as e:
        logger.error(f"Failed to load nutrition profiles config from {PROFILES_CONFIG_PATH}: {e}")
        return {}


def load_ingredient_risks_config() -> Dict[str, Any]:
    try:
        with open(INGREDIENTS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load ingredient risks config from {INGREDIENTS_CONFIG_PATH}: {e}")
        return {"ingredient_rules": [], "default_safe_risk_score": 1}


def excess_rating(actual: float, limit: float) -> int:
    """
    Computes nutrient excess rating r_k on a 1-10 scale (1 = best, 10 = worst).
    Exact formula:
    r_k = 1 if actual <= limit else min(10, 1 + ceil(round((actual - limit)/limit * 9, 9)))
    """
    if limit <= 0:
        return 10 if actual > 0 else 1
    if actual <= limit:
        return 1
    excess_ratio = (actual - limit) / limit
    val = 1 + math.ceil(round(excess_ratio * 9, 9))
    return int(min(10, val))


class PersonalizedScoringEngine:
    """
    Evidence-based Nutritional Personalization & Multi-Condition Engine.
    Implements:
    1) PERSONALISED RATING (1-10, lower = better):
       - nutrient_rating: weighted r_k with clinical worst-case safety floor: max(base, 0.7*max(r_k) + 0.3*base)
       - ingredient_rating: position weights (first=n, last=1) with flagged override: max(base, 0.7*worst_flagged + 0.3*base)
       - product_rating: 0.6 * nutrient_rating + 0.4 * ingredient_rating
       - Multiple conditions: strictest (lowest) limit, highest weight per nutrient
    2) PERSONAL MATCH SCORE (0-100, higher = better, preferences only):
       - Start 100; avoided ingredient -35; undisclosed oil -15; preferred +15;
       - CONTRADICTED claim -30; MISLEADING claim -15; nutrient penalty -(nutrient_rating - 1) * 25/9. Clamp 0-100.
       - No preferences: shows 'No preferences selected' and applies claim and nutrient signals only.
    3) ALLERGY CHECK: Separate hard rule (NOT SAFE FOR YOU / CANNOT CONFIRM / NONE FOUND). If NOT SAFE, show no scores.
    """

    def __init__(self):
        self.profiles_config = load_profiles_config()
        self.ingredients_config = load_ingredient_risks_config()
        self.ingredient_rules = self.ingredients_config.get("ingredient_rules", [])

    def merge_conditions(self, selected_conditions: List[str]) -> Tuple[Dict[str, Any], str, str]:
        """
        Merges multiple health conditions:
        Takes the strictest (lowest) limit and highest weight per nutrient across selected profiles.
        """
        if not selected_conditions:
            selected_conditions = ["general_health"]

        merged_nutrients: Dict[str, Any] = {}
        names = []
        descriptions = []

        for cond_key in selected_conditions:
            clean_key = cond_key.lower().strip()
            if clean_key not in self.profiles_config:
                clean_key = "general_health"

            profile_data = self.profiles_config.get(clean_key, {})
            names.append(profile_data.get("name", clean_key.title()))
            descriptions.append(profile_data.get("description", ""))

            for n_key, n_spec in profile_data.get("nutrients", {}).items():
                if n_key not in merged_nutrients:
                    merged_nutrients[n_key] = dict(n_spec)
                    merged_nutrients[n_key]["source_condition"] = clean_key
                else:
                    curr = merged_nutrients[n_key]
                    # Rule: Strictest (lowest) limit, highest weight
                    if n_spec["limit"] < curr["limit"]:
                        curr["limit"] = n_spec["limit"]
                        curr["source_condition"] = clean_key
                        curr["rule_name"] = n_spec.get("rule_name", curr.get("rule_name"))
                        curr["source_name"] = n_spec.get("source_name", curr.get("source_name"))
                        curr["source_url"] = n_spec.get("source_url", curr.get("source_url"))
                        curr["access_date"] = n_spec.get("access_date", curr.get("access_date"))
                        curr["notes"] = n_spec.get("notes", curr.get("notes"))
                    if n_spec["weight"] > curr["weight"]:
                        curr["weight"] = n_spec["weight"]

        combined_name = " + ".join(dict.fromkeys(names))
        combined_desc = " • ".join(filter(None, dict.fromkeys(descriptions)))
        return merged_nutrients, combined_name, combined_desc

    def calculate_nutrient_rating(
        self,
        nutrition_data: Dict[str, Any],
        selected_conditions: List[str]
    ) -> Tuple[Optional[float], List[Dict[str, Any]]]:
        """
        Computes nutrient_rating (1-10, lower = better):
        For each nutrient k:
          r_k = 1 if actual <= limit else min(10, 1 + ceil(round((actual - limit)/limit * 9, 9)))
        base = sum(weight_k * r_k) / sum(weight_k)
        nutrient_rating = max(base, 0.7*max(r_k) + 0.3*base)
        """
        merged_nutrients, _, _ = self.merge_conditions(selected_conditions)
        if not merged_nutrients or not nutrition_data:
            return None, []

        breakdown = []
        weighted_sum = 0.0
        total_weight = 0.0
        r_k_values = []

        for n_key, n_spec in merged_nutrients.items():
            nutri_item = nutrition_data.get(n_key, {})
            if isinstance(nutri_item, dict):
                actual_val = nutri_item.get("value", 0.0)
            elif isinstance(nutri_item, (int, float)):
                actual_val = float(nutri_item)
            else:
                actual_val = 0.0

            limit_val = float(n_spec["limit"])
            weight_val = float(n_spec["weight"])

            r_k = excess_rating(actual_val, limit_val)
            r_k_values.append(r_k)
            weighted_sum += (weight_val * r_k)
            total_weight += weight_val

            excess_pct = max(0.0, round(((actual_val - limit_val) / limit_val) * 100, 1)) if limit_val > 0 else 0.0

            breakdown.append({
                "nutrient_key": n_key,
                "name": n_spec.get("name", n_key),
                "actual": actual_val,
                "limit": limit_val,
                "unit": n_spec.get("unit", "g"),
                "basis": n_spec.get("basis", "per serving"),
                "excess_pct": excess_pct,
                "r_k": r_k,
                "weight": weight_val,
                "rule_name": n_spec.get("rule_name", "Statutory Nutritional Threshold"),
                "source_name": n_spec.get("source_name", "ICMR-NIN 2024 / ADA 2026"),
                "source_url": n_spec.get("source_url", "https://www.nin.res.in"),
                "access_date": n_spec.get("access_date", "2026-10-24"),
                "statutory_status": n_spec.get("statutory_status", "Statutory Guideline"),
            })

        if total_weight <= 0:
            return None, breakdown

        base = weighted_sum / total_weight
        max_rk = max(r_k_values) if r_k_values else 1
        nutrient_rating = max(base, 0.7 * max_rk + 0.3 * base)

        return round(nutrient_rating, 2), breakdown

    def calculate_ingredient_rating(
        self,
        ingredients: List[Any],
        oil_declared: str = ""
    ) -> Tuple[Optional[float], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Computes ingredient_rating (1-10, lower = better):
        Position weights (first = n, last = 1);
        base = weighted average;
        if any flagged ingredient: max(base, 0.7*worst_flagged + 0.3*base)
        """
        # Normalize ingredients list
        norm_ingredients = []
        if isinstance(ingredients, str):
            norm_ingredients = [i.strip() for i in ingredients.split(",") if i.strip()]
        elif isinstance(ingredients, list):
            for item in ingredients:
                if isinstance(item, dict):
                    norm_ingredients.append(str(item.get("name", item)).strip())
                elif item:
                    norm_ingredients.append(str(item).strip())

        # If oil is declared and not present in ingredients, incorporate it
        if oil_declared and oil_declared.lower() not in ["none declared", "no cooking oil declared"]:
            if not any(oil_declared.lower() in ing.lower() for ing in norm_ingredients):
                norm_ingredients.append(oil_declared)

        if not norm_ingredients:
            return None, [], {}

        n = len(norm_ingredients)
        scored_ingredients = []
        flagged_list = []

        for idx, ing_name in enumerate(norm_ingredients):
            pos_weight = n - idx  # first = n, last = 1
            risk_score = 1
            is_flagged = False
            flag_reason = "Whole or permitted food ingredient"
            rule_matched = None

            ing_lower = ing_name.lower()
            for rule in self.ingredient_rules:
                pat = rule.get("pattern", "")
                if re.search(pat, ing_lower, re.IGNORECASE):
                    risk_score = rule.get("risk_score", 1)
                    is_flagged = rule.get("flagged", False)
                    flag_reason = rule.get("reason", "")
                    rule_matched = rule
                    break

            item_data = {
                "name": ing_name,
                "position": idx + 1,
                "position_weight": pos_weight,
                "risk_score": risk_score,
                "is_flagged": is_flagged,
                "flag_reason": flag_reason,
                "weighted_contribution": pos_weight * risk_score,
                "source_name": rule_matched.get("source_name", "FSSAI Food Additives & Labelling Standards") if rule_matched else "FSSAI Packaging Standards",
                "source_url": rule_matched.get("source_url", "https://www.fssai.gov.in") if rule_matched else "https://www.fssai.gov.in",
                "access_date": rule_matched.get("access_date", "2026-10-24") if rule_matched else "2026-10-24",
            }
            scored_ingredients.append(item_data)
            if is_flagged:
                flagged_list.append(item_data)

        total_pos_weight = sum(item["position_weight"] for item in scored_ingredients)
        total_weighted_risk = sum(item["weighted_contribution"] for item in scored_ingredients)

        base = total_weighted_risk / total_pos_weight

        if flagged_list:
            worst_flagged_item = max(flagged_list, key=lambda x: x["risk_score"])
            worst_flagged = worst_flagged_item["risk_score"]
            ingredient_rating = max(base, 0.7 * worst_flagged + 0.3 * base)
        else:
            worst_flagged_item = {}
            ingredient_rating = base

        # Sort top 3 contributing ingredients (by risk and position weight)
        top_3 = sorted(
            scored_ingredients,
            key=lambda x: (x["is_flagged"], x["risk_score"], x["position_weight"]),
            reverse=True
        )[:3]

        return round(ingredient_rating, 2), top_3, worst_flagged_item

    def calculate_product_rating(
        self,
        nutrient_rating: Optional[float],
        ingredient_rating: Optional[float]
    ) -> Tuple[Optional[float], bool, str]:
        """
        product_rating = 0.6 * nutrient_rating + 0.4 * ingredient_rating
        (if one is None use the other and mark "partial data")
        """
        if nutrient_rating is None and ingredient_rating is None:
            return None, False, "No nutritional or ingredient data available"

        if nutrient_rating is not None and ingredient_rating is not None:
            prod_rating = 0.6 * nutrient_rating + 0.4 * ingredient_rating
            return round(prod_rating, 2), False, "Complete statutory nutrient and ingredient data applied"

        if nutrient_rating is not None:
            return round(nutrient_rating, 2), True, "Partial data: calculated from nutritional disclosures only"

        return round(ingredient_rating, 2), True, "Partial data: calculated from ingredients list only"

    def check_allergens(
        self,
        ingredients: List[Any],
        oil_declared: str,
        user_allergens: List[str]
    ) -> Dict[str, Any]:
        """
        ALLERGY CHECK stays a separate hard rule:
        NOT SAFE FOR YOU / CANNOT CONFIRM / NONE FOUND.
        If NOT SAFE, show no scores.
        """
        if not user_allergens:
            return {
                "allergy_status": "NONE FOUND",
                "matched_allergens": [],
                "is_safe": True,
                "message": "No user allergen restrictions declared.",
            }

        # Normalize ingredient text
        text_corpus = []
        if isinstance(ingredients, str):
            text_corpus.append(ingredients)
        elif isinstance(ingredients, list):
            for i in ingredients:
                if isinstance(i, dict):
                    text_corpus.append(str(i.get("name", "")))
                elif i:
                    text_corpus.append(str(i))
        if oil_declared:
            text_corpus.append(oil_declared)

        full_text = " ".join(text_corpus).strip().lower()

        if not full_text:
            return {
                "allergy_status": "CANNOT CONFIRM",
                "matched_allergens": [],
                "is_safe": False,
                "message": "CANNOT CONFIRM: Ingredient declaration is missing or incomplete.",
            }

        matched = []
        for user_allergen in user_allergens:
            al_clean = user_allergen.strip().lower()
            if not al_clean:
                continue

            # Standard allergen expansion
            patterns = [re.escape(al_clean)]
            if al_clean in ["peanut", "peanuts"]:
                patterns.extend(["groundnut", "arachis"])
            elif al_clean in ["milk", "dairy"]:
                patterns.extend(["lactose", "casein", "whey", "butter", "cheese", "cream"])
            elif al_clean in ["gluten", "wheat"]:
                patterns.extend(["maida", "atta", "semolina", "suji", "barley", "malt", "rye"])
            elif al_clean in ["soy", "soya"]:
                patterns.extend(["soybean", "soy lecithin", "soya lecithin"])
            elif al_clean in ["nut", "tree nut", "tree nuts"]:
                patterns.extend(["almond", "cashew", "walnut", "pistachio", "hazelnut"])

            regex = r'\b(?:' + '|'.join(patterns) + r')\b'
            if re.search(regex, full_text, re.IGNORECASE):
                matched.append(user_allergen.title())

        if matched:
            return {
                "allergy_status": "NOT SAFE FOR YOU",
                "matched_allergens": list(dict.fromkeys(matched)),
                "is_safe": False,
                "message": f"NOT SAFE FOR YOU: Contains declared allergen(s): {', '.join(dict.fromkeys(matched))}.",
            }

        return {
            "allergy_status": "NONE FOUND",
            "matched_allergens": [],
            "is_safe": True,
            "message": "NONE FOUND: None of your specified allergens were detected in label statement.",
        }

    def calculate_personal_match_score(
        self,
        nutrient_rating: Optional[float],
        claims: List[Dict[str, Any]],
        ingredients: List[Any],
        oil_declared: str,
        preferences: List[str],
        avoided_ingredients: List[str],
        preferred_ingredients: List[str],
    ) -> Dict[str, Any]:
        """
        PERSONAL MATCH SCORE (0-100, higher = better), preferences only:
        start 100;
        avoided ingredient found -35;
        oil source undisclosed -15;
        preferred ingredient confirmed +15;
        each CONTRADICTED claim -30;
        each MISLEADING claim -15;
        nutrient penalty -(nutrient_rating - 1) * 25/9.
        Clamp 0-100.
        If user has selected NO preferences, show "No preferences selected" and apply only claim and nutrient signals.
        Never invent a default like 75.
        """
        score = 100.0
        deductions = []
        has_preferences = bool(preferences or avoided_ingredients or preferred_ingredients)

        # 1. Full text of ingredients
        all_ing_text = []
        if isinstance(ingredients, list):
            for i in ingredients:
                if isinstance(i, dict):
                    all_ing_text.append(str(i.get("name", "")).lower())
                elif i:
                    all_ing_text.append(str(i).lower())
        full_ing_corpus = " ".join(all_ing_text)
        oil_clean = oil_declared.strip().lower()

        # 2. Preference checks (only if user selected preferences)
        if has_preferences:
            # Check avoided ingredients (-35 each)
            all_avoid = list(avoided_ingredients)
            if any("palm" in p.lower() for p in preferences):
                all_avoid.append("palm oil")

            for avoid_term in set(all_avoid):
                term_clean = avoid_term.strip().lower()
                if not term_clean:
                    continue
                # Term patterns
                if term_clean in ["palm oil", "palmolein", "palm"]:
                    is_found = any(p in full_ing_corpus or p in oil_clean for p in ["palmolein", "palm oil", "palm kernel"])
                else:
                    is_found = term_clean in full_ing_corpus

                if is_found:
                    score -= 35.0
                    deductions.append({
                        "type": "avoided_ingredient",
                        "description": f"Avoided ingredient found: '{avoid_term.title()}'",
                        "points": -35
                    })

            # Check undisclosed oil source (-15)
            # e.g. "Vegetable Oil" or "Edible Vegetable Oil" without named plant
            known_plants = ["palmolein", "palm", "sunflower", "soybean", "mustard", "groundnut", "peanut", "rice bran", "sesame", "olive", "coconut", "corn", "canola", "cottonseed"]
            is_undisclosed = False
            if oil_clean and oil_clean not in ["none declared", "no cooking oil declared"]:
                has_veg_oil = "vegetable oil" in oil_clean or "edible oil" in oil_clean
                has_known_plant = any(kp in oil_clean for kp in known_plants)
                if has_veg_oil and not has_known_plant:
                    is_undisclosed = True

            if is_undisclosed:
                score -= 15.0
                deductions.append({
                    "type": "undisclosed_oil",
                    "description": "Oil source undisclosed on label (e.g. generic 'vegetable oil')",
                    "points": -15
                })

            # Check preferred ingredients (+15 each)
            for pref_term in set(preferred_ingredients):
                term_clean = pref_term.strip().lower()
                if term_clean and term_clean in full_ing_corpus:
                    score += 15.0
                    deductions.append({
                        "type": "preferred_ingredient",
                        "description": f"Preferred ingredient confirmed: '{pref_term.title()}'",
                        "points": +15
                    })

        # 3. Claims Signals: each CONTRADICTED claim -30; each MISLEADING claim -15
        for c in (claims or []):
            verdict = str(c.get("audit_verdict", "")).upper()
            claim_text = c.get("claim", "Marketing Claim")
            if "CONTRADICTED" in verdict:
                score -= 30.0
                deductions.append({
                    "type": "contradicted_claim",
                    "description": f"Contradicted claim: \"{claim_text}\"",
                    "points": -30
                })
            elif "MISLEADING" in verdict:
                score -= 15.0
                deductions.append({
                    "type": "misleading_claim",
                    "description": f"Misleading claim: \"{claim_text}\"",
                    "points": -15
                })

        # 4. Nutrient Penalty: -(nutrient_rating - 1) * 25/9
        if nutrient_rating is not None and nutrient_rating > 1.0:
            nutri_penalty = (nutrient_rating - 1.0) * (25.0 / 9.0)
            score -= nutri_penalty
            deductions.append({
                "type": "nutrient_penalty",
                "description": f"Nutrient profile penalty (Rating: {nutrient_rating}/10)",
                "points": -round(nutri_penalty, 1)
            })

        clamped_score = int(round(max(0.0, min(100.0, score))))

        return {
            "personal_match_score": clamped_score,
            "has_preferences": has_preferences,
            "preferences_label": "Preferences applied" if has_preferences else "No preferences selected",
            "deductions": deductions,
            "starting_score": 100,
        }

    def evaluate(
        self,
        product_data: Dict[str, Any],
        selected_conditions: List[str] = None,
        user_allergens: List[str] = None,
        preferences: List[str] = None,
        avoided_ingredients: List[str] = None,
        preferred_ingredients: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Master evaluation pipeline implementing the revised Personalized Rating & Match Score.
        """
        selected_conditions = selected_conditions or ["general_health"]
        user_allergens = user_allergens or []
        preferences = preferences or []
        avoided_ingredients = avoided_ingredients or []
        preferred_ingredients = preferred_ingredients or []

        nutrition = product_data.get("nutrition", {})
        ingredients = product_data.get("ingredients", [])
        oil_info = product_data.get("oil_listed", {})
        oil_declared = oil_info.get("value", "") if isinstance(oil_info, dict) else str(oil_info or "")
        claims = product_data.get("front_pack_claims", [])

        # 1. Allergy Check (Hard Rule)
        allergy_res = self.check_allergens(ingredients, oil_declared, user_allergens)

        # 2. Nutrient Rating (1-10, lower = better)
        nutri_rating, nutri_breakdown = self.calculate_nutrient_rating(nutrition, selected_conditions)

        # 3. Ingredient Rating (1-10, lower = better)
        ing_rating, top_ingredients, worst_flagged = self.calculate_ingredient_rating(ingredients, oil_declared)

        # 4. Overall Product Rating (1-10)
        prod_rating, is_partial, partial_reason = self.calculate_product_rating(nutri_rating, ing_rating)

        # 5. Personal Match Score (0-100, preferences only)
        match_data = self.calculate_personal_match_score(
            nutrient_rating=nutri_rating,
            claims=claims,
            ingredients=ingredients,
            oil_declared=oil_declared,
            preferences=preferences,
            avoided_ingredients=avoided_ingredients,
            preferred_ingredients=preferred_ingredients,
        )

        _, condition_name, condition_desc = self.merge_conditions(selected_conditions)

        # Hard Rule: If NOT SAFE FOR YOU, show no scores!
        if allergy_res["allergy_status"] == "NOT SAFE FOR YOU":
            return {
                "allergy_check": allergy_res,
                "show_scores": False,
                "product_rating": None,
                "nutrient_rating": None,
                "ingredient_rating": None,
                "personal_match_score": None,
                "selected_conditions": selected_conditions,
                "conditions_title": condition_name,
                "conditions_description": condition_desc,
                "nutrient_breakdown": nutri_breakdown,
                "top_ingredients": top_ingredients,
                "worst_flagged": worst_flagged,
                "match_details": match_data,
                "is_partial_data": is_partial,
                "partial_data_note": partial_reason,
            }

        return {
            "allergy_check": allergy_res,
            "show_scores": True,
            "product_rating": prod_rating,
            "nutrient_rating": nutri_rating,
            "ingredient_rating": ing_rating,
            "personal_match_score": match_data["personal_match_score"],
            "selected_conditions": selected_conditions,
            "conditions_title": condition_name,
            "conditions_description": condition_desc,
            "nutrient_breakdown": nutri_breakdown,
            "top_ingredients": top_ingredients,
            "worst_flagged": worst_flagged,
            "match_details": match_data,
            "is_partial_data": is_partial,
            "partial_data_note": partial_reason,
        }
