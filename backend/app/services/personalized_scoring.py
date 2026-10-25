import json
import logging
import math
import os
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("labeltruth.personalized_scoring")

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
    Formula:
    r_k = 1 if actual <= limit else min(10, 1 + ceil(round((actual - limit)/limit * 9, 9)))
    """
    if limit <= 0:
        return 10 if actual > 0 else 1
    if actual <= limit:
        return 1
    excess_ratio = (actual - limit) / limit
    val = 1 + math.ceil(round(excess_ratio * 9, 9))
    return int(min(10, val))


# Built-in reference products across common Indian categories for category recommendations
CATEGORY_REFERENCE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "product_name": {"value": "The Whole Truth Roasted Makhana Himalayan Pink Salt", "source_url": "https://thewholetruthfoods.com"},
        "brand": {"value": "The Whole Truth", "source_url": "https://thewholetruthfoods.com"},
        "category": {"value": "Savory Packaged Snack", "source_url": "https://thewholetruthfoods.com"},
        "nutrition": {
            "serving_size": {"value": "30g", "source_url": "https://thewholetruthfoods.com"},
            "kcal": {"value": 115.0, "unit": "kcal", "source_url": "https://thewholetruthfoods.com"},
            "carbs_g": {"value": 19.0, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "sugars_g": {"value": 0.2, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "protein_g": {"value": 3.0, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "fat_g": {"value": 2.1, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "saturated_fat_g": {"value": 0.4, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "sodium_mg": {"value": 110.0, "unit": "mg", "source_url": "https://thewholetruthfoods.com"},
        },
        "ingredients": [
            {"name": "Foxnuts (Makhana)", "source_url": "https://thewholetruthfoods.com"},
            {"name": "Cold Pressed Sunflower Oil", "source_url": "https://thewholetruthfoods.com"},
            {"name": "Himalayan Pink Salt", "source_url": "https://thewholetruthfoods.com"}
        ],
        "oil_listed": {"value": "Cold Pressed Sunflower Oil", "is_palm_oil": False, "source_url": "https://thewholetruthfoods.com"},
        "front_pack_claims": [
            {"claim": "No Palm Oil", "audit_verdict": "VERIFIED", "verdict_reason": "Cold pressed sunflower oil confirmed."},
            {"claim": "Low Saturated Fat", "audit_verdict": "VERIFIED", "verdict_reason": "0.4g saturated fat per serving."}
        ]
    },
    {
        "product_name": {"value": "Farmley Roasted Peri Peri Makhana", "source_url": "https://farmley.com"},
        "brand": {"value": "Farmley", "source_url": "https://farmley.com"},
        "category": {"value": "Savory Packaged Snack", "source_url": "https://farmley.com"},
        "nutrition": {
            "serving_size": {"value": "30g", "source_url": "https://farmley.com"},
            "kcal": {"value": 120.0, "unit": "kcal", "source_url": "https://farmley.com"},
            "carbs_g": {"value": 20.0, "unit": "g", "source_url": "https://farmley.com"},
            "sugars_g": {"value": 0.5, "unit": "g", "source_url": "https://farmley.com"},
            "protein_g": {"value": 2.8, "unit": "g", "source_url": "https://farmley.com"},
            "fat_g": {"value": 2.4, "unit": "g", "source_url": "https://farmley.com"},
            "saturated_fat_g": {"value": 0.5, "unit": "g", "source_url": "https://farmley.com"},
            "sodium_mg": {"value": 140.0, "unit": "mg", "source_url": "https://farmley.com"},
        },
        "ingredients": [
            {"name": "Foxnuts (Makhana)", "source_url": "https://farmley.com"},
            {"name": "Olive Oil", "source_url": "https://farmley.com"},
            {"name": "Chilli Powder", "source_url": "https://farmley.com"},
            {"name": "Iodised Salt", "source_url": "https://farmley.com"}
        ],
        "oil_listed": {"value": "Olive Oil", "is_palm_oil": False, "source_url": "https://farmley.com"},
        "front_pack_claims": [
            {"claim": "Roasted Not Fried", "audit_verdict": "VERIFIED", "verdict_reason": "Roasted processing confirmed with low fat."},
            {"claim": "Zero Cholesterol", "audit_verdict": "VERIFIED", "verdict_reason": "Plant-based oil confirmed."}
        ]
    },
    {
        "product_name": {"value": "WickedGud 100% Whole Wheat & Multi-Millet Noodles", "source_url": "https://wickedgud.com"},
        "brand": {"value": "WickedGud", "source_url": "https://wickedgud.com"},
        "category": {"value": "Instant Noodles", "source_url": "https://wickedgud.com"},
        "nutrition": {
            "serving_size": {"value": "70g", "source_url": "https://wickedgud.com"},
            "kcal": {"value": 240.0, "unit": "kcal", "source_url": "https://wickedgud.com"},
            "carbs_g": {"value": 46.0, "unit": "g", "source_url": "https://wickedgud.com"},
            "sugars_g": {"value": 1.5, "unit": "g", "source_url": "https://wickedgud.com"},
            "protein_g": {"value": 9.0, "unit": "g", "source_url": "https://wickedgud.com"},
            "fat_g": {"value": 1.8, "unit": "g", "source_url": "https://wickedgud.com"},
            "saturated_fat_g": {"value": 0.4, "unit": "g", "source_url": "https://wickedgud.com"},
            "sodium_mg": {"value": 260.0, "unit": "mg", "source_url": "https://wickedgud.com"},
        },
        "ingredients": [
            {"name": "Whole Wheat Flour (Atta)", "source_url": "https://wickedgud.com"},
            {"name": "Finger Millet (Ragi)", "source_url": "https://wickedgud.com"},
            {"name": "Pearl Millet (Bajra)", "source_url": "https://wickedgud.com"},
            {"name": "Oats Flour", "source_url": "https://wickedgud.com"},
            {"name": "Spices & Condiments", "source_url": "https://wickedgud.com"}
        ],
        "oil_listed": {"value": "None declared / Steamed and baked", "is_palm_oil": False, "source_url": "https://wickedgud.com"},
        "front_pack_claims": [
            {"claim": "Zero Maida", "audit_verdict": "VERIFIED", "verdict_reason": "100% whole grain flours verified."},
            {"claim": "No Palm Oil", "audit_verdict": "VERIFIED", "verdict_reason": "Non-fried noodle cakes."}
        ]
    },
    {
        "product_name": {"value": "Slurrp Farm Millet Noodles", "source_url": "https://slurrpfarm.com"},
        "brand": {"value": "Slurrp Farm", "source_url": "https://slurrpfarm.com"},
        "category": {"value": "Instant Noodles", "source_url": "https://slurrpfarm.com"},
        "nutrition": {
            "serving_size": {"value": "70g", "source_url": "https://slurrpfarm.com"},
            "kcal": {"value": 245.0, "unit": "kcal", "source_url": "https://slurrpfarm.com"},
            "carbs_g": {"value": 48.0, "unit": "g", "source_url": "https://slurrpfarm.com"},
            "sugars_g": {"value": 1.2, "unit": "g", "source_url": "https://slurrpfarm.com"},
            "protein_g": {"value": 8.0, "unit": "g", "source_url": "https://slurrpfarm.com"},
            "fat_g": {"value": 2.0, "unit": "g", "source_url": "https://slurrpfarm.com"},
            "saturated_fat_g": {"value": 0.5, "unit": "g", "source_url": "https://slurrpfarm.com"},
            "sodium_mg": {"value": 280.0, "unit": "mg", "source_url": "https://slurrpfarm.com"},
        },
        "ingredients": [
            {"name": "Foxtail Millet Flour", "source_url": "https://slurrpfarm.com"},
            {"name": "Whole Wheat Flour", "source_url": "https://slurrpfarm.com"},
            {"name": "Natural Spices", "source_url": "https://slurrpfarm.com"}
        ],
        "oil_listed": {"value": "Cold Pressed Sesame Oil", "is_palm_oil": False, "source_url": "https://slurrpfarm.com"},
        "front_pack_claims": [
            {"claim": "No Maida No Palm Oil", "audit_verdict": "VERIFIED", "verdict_reason": "Ingredients confirm millet flour and cold pressed oil."}
        ]
    },
    {
        "product_name": {"value": "The Whole Truth 100% Cocoa & Almond Health Mix", "source_url": "https://thewholetruthfoods.com"},
        "brand": {"value": "The Whole Truth", "source_url": "https://thewholetruthfoods.com"},
        "category": {"value": "Malt-based Health Food Drink", "source_url": "https://thewholetruthfoods.com"},
        "nutrition": {
            "serving_size": {"value": "20g", "source_url": "https://thewholetruthfoods.com"},
            "kcal": {"value": 80.0, "unit": "kcal", "source_url": "https://thewholetruthfoods.com"},
            "carbs_g": {"value": 9.0, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "sugars_g": {"value": 1.8, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "protein_g": {"value": 4.5, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "fat_g": {"value": 3.0, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "saturated_fat_g": {"value": 0.8, "unit": "g", "source_url": "https://thewholetruthfoods.com"},
            "sodium_mg": {"value": 25.0, "unit": "mg", "source_url": "https://thewholetruthfoods.com"},
        },
        "ingredients": [
            {"name": "Almonds", "source_url": "https://thewholetruthfoods.com"},
            {"name": "Oats Flour", "source_url": "https://thewholetruthfoods.com"},
            {"name": "Raw Cocoa", "source_url": "https://thewholetruthfoods.com"},
            {"name": "Dates Powder", "source_url": "https://thewholetruthfoods.com"}
        ],
        "oil_listed": {"value": "None declared / No added fats", "is_palm_oil": False, "source_url": "https://thewholetruthfoods.com"},
        "front_pack_claims": [
            {"claim": "Zero Added Sugar", "audit_verdict": "VERIFIED", "verdict_reason": "Sweetened purely with whole dates powder."},
            {"claim": "No Artificial Additives", "audit_verdict": "VERIFIED", "verdict_reason": "Clean four-ingredient formulation."}
        ]
    },
    {
        "product_name": {"value": "Raw Pressery Pure Tender Coconut Water", "source_url": "https://rawpressery.com"},
        "brand": {"value": "Raw Pressery", "source_url": "https://rawpressery.com"},
        "category": {"value": "Carbonated Beverage", "source_url": "https://rawpressery.com"},
        "nutrition": {
            "serving_size": {"value": "200ml", "source_url": "https://rawpressery.com"},
            "kcal": {"value": 40.0, "unit": "kcal", "source_url": "https://rawpressery.com"},
            "carbs_g": {"value": 9.0, "unit": "g", "source_url": "https://rawpressery.com"},
            "sugars_g": {"value": 3.5, "unit": "g", "source_url": "https://rawpressery.com"},
            "protein_g": {"value": 0.4, "unit": "g", "source_url": "https://rawpressery.com"},
            "fat_g": {"value": 0.0, "unit": "g", "source_url": "https://rawpressery.com"},
            "saturated_fat_g": {"value": 0.0, "unit": "g", "source_url": "https://rawpressery.com"},
            "sodium_mg": {"value": 45.0, "unit": "mg", "source_url": "https://rawpressery.com"},
        },
        "ingredients": [
            {"name": "Tender Coconut Water", "source_url": "https://rawpressery.com"},
            {"name": "Bio-fermented Vitamin C", "source_url": "https://rawpressery.com"}
        ],
        "oil_listed": {"value": "None declared", "is_palm_oil": False, "source_url": "https://rawpressery.com"},
        "front_pack_claims": [
            {"claim": "No Added Sugar", "audit_verdict": "VERIFIED", "verdict_reason": "Naturally occurring sugars only."},
            {"claim": "Zero Artificial Sweeteners", "audit_verdict": "VERIFIED", "verdict_reason": "No intense sweeteners detected."}
        ]
    }
]


ALLERGEN_CATEGORIES = {
    "peanuts": {
        "display_name": "Peanuts",
        "aliases": [
            "peanuts", "peanut", "groundnut", "groundnuts", "arachis", "mungfali", "moongphali", "singdana", "shengdana"
        ],
        "patterns": [
            r"\bpeanuts?\b",
            r"\bgroundnuts?\b",
            r"\barachis\b",
            r"\bm[uo]{1,2}ngphali\b",
            r"\bs[hi]ngdana\b",
            r"\bshengdana\b",
            r"\bpeanut\s*(?:butter|oil|paste|flour|protein)\b",
            r"\bgroundnut\s*(?:oil|protein)\b",
        ]
    },
    "tree_nuts": {
        "display_name": "Tree Nuts",
        "aliases": [
            "tree_nuts", "tree nuts", "tree nut", "treenut", "treenuts", "nuts", "nut",
            "almonds", "almond", "badam", "cashews", "cashew", "kaju", "walnuts", "walnut",
            "akhrot", "pistachios", "pistachio", "pista", "hazelnuts", "hazelnut", "pecans",
            "pecan", "macadamia", "macadamias", "pine nuts", "pine nut", "chilgoza",
            "brazil nuts", "brazil nut", "chestnuts", "chestnut"
        ],
        "patterns": [
            r"\btree\s*nuts?\b",
            r"\balmonds?\b",
            r"\bbadam\b",
            r"\bcashews?\b",
            r"\bcashewnuts?\b",
            r"\bkaju\b",
            r"\bwalnuts?\b",
            r"\bakhrot\b",
            r"\bpistachios?\b",
            r"\bpista\b",
            r"\bhazelnuts?\b",
            r"\bpecans?\b",
            r"\bmacadamias?\b",
            r"\bpine\s*nuts?\b",
            r"\bchilgoza\b",
            r"\bbrazil\s*nuts?\b",
            r"\bchestnuts?\b",
            r"\bpraline\b",
            r"\bmarzipan\b",
        ]
    },
    "milk": {
        "display_name": "Milk / Dairy",
        "aliases": [
            "milk", "dairy", "lactose", "lactose_intolerance", "lactose intolerance",
            "milk / dairy proteins", "dairy proteins", "dairy protein", "milk protein",
            "milk solids", "milk fat", "casein", "whey", "butter", "ghee"
        ],
        "patterns": [
            r"\bmilks?\b",
            r"\bdairy\b",
            r"\blactose\b",
            r"\bcasein(?:ate|ates)?\b",
            r"\bwhey\b",
            r"\bghee\b",
            r"\bclarified\s+butter\b",
            r"\bdesi\s+ghee\b",
            r"\bpaneer\b",
            r"\bcottage\s+cheese\b",
            r"\bcheeses?\b",
            r"\bcheddar\b",
            r"\bmozzarella\b",
            r"\bparmesan\b",
            r"\bcurd\b",
            r"\bdahi\b",
            r"\byog[hu]rts?\b",
            r"\bshrikhand\b",
            r"\bkhoya\b",
            r"\bmawa\b",
            r"\bkhoa\b",
            r"\bmalai\b",
            r"\blactalbumin\b",
            r"\blactoglobulin\b",
            r"\bcondensed\s+milk\b",
            r"\bice\s*cream\b",
            r"(?<!cocoa\s)(?<!peanut\s)(?<!almond\s)(?<!shea\s)(?<!apple\s)\bbutters?\b",
            r"\bbutterfat\b",
            r"\bbutter\s*oil\b",
            r"\bmilk\s*fat\b",
            r"\banhydrous\s*milk\s*fat\b",
            r"\bcream\b(?!\s*of\s*tartar)",
        ]
    },
    "eggs": {
        "display_name": "Eggs",
        "aliases": [
            "eggs", "egg", "egg white", "egg yolk", "egg powder", "albumin", "ovalbumin", "mayonnaise", "mayo", "anda", "ande", "whole egg", "egg solids"
        ],
        "patterns": [
            r"\beggs?\b",
            r"\banda\b",
            r"\bande\b",
            r"\balbumen\b",
            r"\balbumin\b",
            r"\bovalbumin\b",
            r"\bovomucin\b",
            r"\bovomucoid\b",
            r"\bovovitellin\b",
            r"\blivetin\b",
            r"\bvitellin\b",
            r"(?<!eggless\s)\bmayonnaise\b",
            r"(?<!eggless\s)\bmayo\b",
            r"\bmeringue\b",
            r"\blysozyme\b",
            r"\begg\s*(?:yolk|white|powder|solids?|albumin|protein|lecithin|oil)\b",
            r"\bwhole\s*eggs?\b",
            r"\bliquid\s*eggs?\b",
            r"\bpasteuri[sz]ed\s*eggs?\b",
            r"\bcontains\s+(?:fresh\s+)?eggs?\b",
            r"\bcontains\s+egg\b",
        ]
    },
    "soy": {
        "display_name": "Soy",
        "aliases": [
            "soy", "soya", "soybeans", "soybean", "soya bean", "soya beans", "soy lecithin", "soya lecithin"
        ],
        "patterns": [
            r"\bsoya?\b",
            r"\bsoybeans?\b",
            r"\bsoya\s*beans?\b",
            r"\bsoya?\s*lecithin\b",
            r"\bsoylecithin\b",
            r"\bsoya?\s*protein\b",
            r"\bsoya?\s*isolate\b",
            r"\btofu\b",
            r"\bedamame\b",
            r"\btempeh\b",
            r"\bsoya?\s*chunks?\b",
            r"\bsoya?\s*sauce\b",
            r"\btextured\s+(?:soy|soya|vegetable)\s+protein\b",
            r"\btvp\b",
            r"(?<!sunflower\s)\blecithins?\b",
            r"\b(?:ins|e)\s*322(?:\([a-ziv]+\))?\b",
            r"\b322(?:\([a-ziv]+\)|i)?\s*(?:-\s*)?soya?\b",
            r"\b(?:emulsifier\s*)?322\b",
        ]
    },
    "wheat": {
        "display_name": "Wheat",
        "aliases": [
            "wheat", "refined wheat flour", "maida", "atta", "wheat flour", "whole wheat", "chakki atta"
        ],
        "patterns": [
            r"\bwheats?\b",
            r"\bmaida\b",
            r"\batta\b",
            r"\brefined\s*(?:wheat\s*)?flour\b",
            r"\bwhole\s*wheat\b",
            r"\bchakki\s*atta\b",
            r"\bgehu\b",
            r"\bwheat\s*(?:bran|germ|gluten|starch|protein)\b",
            r"\bspelt\b",
            r"\bfarina\b",
            r"\bbulgur\b",
            r"\bcouscous\b",
            r"\btriticale\b",
            r"\bkamut\b",
            r"\bemmer\b",
            r"\beinkorn\b",
            r"\bseitan\b",
        ]
    },
    "gluten": {
        "display_name": "Gluten",
        "aliases": [
            "gluten", "wheat", "coeliac", "coeliac_disease", "celiac", "celiac_disease",
            "coeliac disease / medically required gluten avoidance", "barley", "rye", "malt",
            "semolina", "suji", "sooji", "rava", "rawa"
        ],
        "patterns": [
            r"\bglutens?\b",
            r"\bwheats?\b",
            r"\bmaida\b",
            r"\batta\b",
            r"\bsemolina\b",
            r"\bsuji\b",
            r"\bsooji\b",
            r"\brava\b",
            r"\brawa\b",
            r"\bdurum\b",
            r"\bbarley\b",
            r"\bmalt(?:ed)?\b",
            r"\bmalt\s*extract\b",
            r"\brye\b",
            r"\bspelt\b",
            r"\btriticale\b",
            r"\bkamut\b",
            r"\bseitan\b",
            r"\bwheat\s*(?:bran|germ|starch|protein|gluten|flour)\b",
        ]
    },
    "sesame": {
        "display_name": "Sesame",
        "aliases": [
            "sesame", "sesame seeds", "sesame seed", "til", "tila", "gingelly"
        ],
        "patterns": [
            r"\bsesames?\b",
            r"\bsesame\s*seeds?\b",
            r"\bsesame\s*oil\b",
            r"\btil\b",
            r"\btila\b",
            r"\bgingelly\b",
            r"\btahini\b",
            r"\btahina\b",
            r"\bbenne\b",
            r"\bbenniseed\b",
        ]
    },
    "fish_shellfish": {
        "display_name": "Fish / Shellfish",
        "aliases": [
            "fish_shellfish", "fish / shellfish", "fish", "shellfish", "crustacean", "crustaceans",
            "seafood", "prawn", "prawns", "shrimp", "shrimps", "crab", "crabs", "lobster",
            "oyster", "clam", "mussel", "squid", "calamari", "octopus"
        ],
        "patterns": [
            r"\bfish(?:es)?\b",
            r"\bfish\s*(?:oil|sauce|gelatin|collagen)\b",
            r"\bmachh?li\b",
            r"\bshellfish(?:es)?\b",
            r"\bcrustaceans?\b",
            r"\bmollus[ck]s?\b",
            r"\bprawns?\b",
            r"\bshrimps?\b",
            r"\bjh[ie]ng[aa]\b",
            r"\bcrabs?\b",
            r"\blobsters?\b",
            r"\boysters?\b",
            r"\bclams?\b",
            r"\bmussels?\b",
            r"\bscallops?\b",
            r"\bsquids?\b",
            r"\bcalamari\b",
            r"\boctopus(?:es)?\b",
            r"\banchov(?:y|ies)\b",
            r"\btuna\b",
            r"\bsalmon\b",
            r"\bcod\b",
            r"\bsardines?\b",
            r"\bmackerel\b",
        ]
    },
    "mustard": {
        "display_name": "Mustard",
        "aliases": [
            "mustard", "mustards", "sarson", "rai", "kasundi"
        ],
        "patterns": [
            r"\bmustards?\b",
            r"\bmustard\s*(?:seeds?|oil|powder|paste)\b",
            r"\bsarson\b",
            r"\brai\b",
            r"\bkasundi\b",
        ]
    }
}


AVOID_INGREDIENT_RULES = {
    "palm_oil": {
        "id": "palm_oil",
        "display_name": "Palm Oil",
        "aliases": ["palm_oil", "palm oil", "palmolein", "palm fat", "rpo"],
        "patterns": [
            r"\bpalms?\s*(?:oil|olein|fat|kernel(?:\s*oil)?)\b",
            r"\bpalmolein\b",
            r"\brpo\b",
            r"\bfractionated\s*palm\b",
            r"\bhydrogenated\s+(?:vegetable\s+)?(?:oil|fat)\s*(?:\(palm\))?\b",
        ],
        "warning": "Contains Palm Oil / Palmolein, high in saturated fatty acids.",
    },
    "artificial_sweeteners": {
        "id": "artificial_sweeteners",
        "display_name": "Artificial Sweeteners",
        "aliases": ["artificial_sweeteners", "artificial sweeteners", "sweeteners", "sweetener"],
        "patterns": [
            r"\baspartame\b",
            r"\bacesulfame(?:\s*[-kK])?\b",
            r"\bsucralose\b",
            r"\bsaccharin(?:e)?\b",
            r"\bneotame\b",
            r"\balitame\b",
            r"\bcyclamate\b",
            r"\badvantame\b",
            r"\bstevia\b",
            r"\bsteviol\b",
            r"\brebaudioside\b",
            r"\b(?:ins|e)?\s*(?:950|951|952|954|955|960|961|962)\b",
            r"\bnon-caloric\s+sweeteners?\b",
            r"\bartificial\s+sweeteners?\b",
        ],
        "warning": "Contains Artificial / Non-Caloric Sweeteners (mandates front-pack FSSAI disclosure).",
    },
    "added_sugar": {
        "id": "added_sugar",
        "display_name": "Added Sugar",
        "aliases": ["added_sugar", "added sugar", "sugar", "sugars"],
        "patterns": [
            r"\bsugars?\b",
            r"\bsucrose\b",
            r"\binvert\s*(?:sugar\s*)?syrup\b",
            r"\bliquid\s*glucose\b",
            r"\bglucose\s*syrup\b",
            r"\bcorn\s*syrup\b",
            r"\bhigh\s*fructose\s*corn\s*syrup\b",
            r"\bhfcs\b",
            r"\bmaltodextrin\b",
            r"\bdextrose\b",
            r"\bcane\s*sugar\b",
            r"\bbrown\s*sugar\b",
            r"\bmolasses\b",
            r"\bgolden\s*syrup\b",
            r"\bcaramel\s*(?:sugar|syrup)\b",
        ],
        "warning": "Contains Added Sugar or refined high-glycaemic syrup.",
    },
    "caffeine": {
        "id": "caffeine",
        "display_name": "Caffeine",
        "aliases": ["caffeine", "coffee"],
        "patterns": [
            r"\bcaffeine\b",
            r"\bcoffee(?:\s*extract|\s*powder)?\b",
            r"\bespresso\b",
            r"\bkola\s*nut\b",
            r"\bguarana\b",
            r"\bgreen\s*tea\s*extract\b",
            r"\benergy\s*blend\b",
            r"\btaurine\b",
        ],
        "warning": "Contains Stimulant Caffeine or Kola Nut / Guarana extract.",
    },
    "gelatin": {
        "id": "gelatin",
        "display_name": "Gelatin / Animal-derived Ingredients",
        "aliases": ["gelatin", "gelatin / animal-derived ingredients", "animal-derived", "animal-derived ingredients"],
        "patterns": [
            r"\bgelatins?\b",
            r"\bgelatines?\b",
            r"\banimal\s*(?:gelatin|fat|collagen|rennet|protein|lipid)\b",
            r"\bcollagen\b",
            r"\bisinglass\b",
            r"\bcarmine\b",
            r"\bcochineal\b",
            r"\b(?:ins|e)\s*120\b",
            r"\bbone\s*(?:phosphate|char)\b",
            r"\btallow\b",
            r"\blard\b",
        ],
        "warning": "Contains Gelatin or Animal-Derived Processing Ingredients.",
    },
}

DIETARY_PATTERN_RULES = {
    "vegetarian": {
        "id": "vegetarian",
        "display_name": "Vegetarian",
        "forbidden_rules": [
            (r"\beggs?\b|\banda\b|\bande\b|\balbumen\b|\bovalbumin\b|\begg\s*yolk\b|\begg\s*white\b|(?<!eggless\s)\bmayonnaise\b", "Eggs / Egg derivatives"),
            (r"\b(?:chicken|mutton|lamb|goat|beef|pork|bacon|ham|meat|poultry|turkey|veal)\b", "Meat / Poultry"),
            (r"\b(?:fish|prawns?|shrimps?|crabs?|lobsters?|clams?|oysters?|mussels?|squids?|tuna|salmon|anchov(?:y|ies))\b", "Fish / Seafood"),
            (r"\b(?:gelatins?|gelatines?|collagen|isinglass|carmine|cochineal|e\s*120|ins\s*120|tallow|lard|animal\s*rennet)\b", "Gelatin / Animal-derived ingredients"),
            (r"\bnon[\s-]?veg(?:etarian)?\b", "Non-Vegetarian declaration"),
        ],
        "compliance_message": "Suitable for Vegetarian diet (no meat, fish, poultry, eggs, or animal gelatin detected).",
        "conflict_message_prefix": "Not suitable for Vegetarian diet: Contains",
    },
    "vegan": {
        "id": "vegan",
        "display_name": "Vegan",
        "forbidden_rules": [
            (r"\beggs?\b|\banda\b|\bande\b|\balbumen\b|\bovalbumin\b|\begg\s*yolk\b|\begg\s*white\b|(?<!eggless\s)\bmayonnaise\b", "Eggs"),
            (r"\b(?:chicken|mutton|lamb|goat|beef|pork|bacon|ham|meat|poultry|turkey|veal)\b", "Meat / Poultry"),
            (r"\b(?:fish|prawns?|shrimps?|crabs?|lobsters?|clams?|oysters?|mussels?|squids?|tuna|salmon|anchov(?:y|ies))\b", "Fish / Seafood"),
            (r"\b(?:milks?|dairy|butter|ghee|paneer|curd|dahi|yogurt|cheese|cheddar|mozzarella|whey|casein|caseinate|lactose|milk\s*solids|milk\s*fat|cream|malai|khoya|mawa)\b", "Dairy / Milk products"),
            (r"\b(?:honey|beeswax)\b", "Honey / Bee products"),
            (r"\b(?:gelatins?|gelatines?|collagen|isinglass|carmine|cochineal|e\s*120|ins\s*120|tallow|lard|animal\s*rennet)\b", "Gelatin / Animal derivatives"),
            (r"\bnon[\s-]?veg(?:etarian)?\b", "Non-Vegetarian declaration"),
        ],
        "compliance_message": "Suitable for Vegan diet (100% plant-based, no animal or dairy ingredients).",
        "conflict_message_prefix": "Not suitable for Vegan diet: Contains",
    },
    "vegetarian_eggs": {
        "id": "vegetarian_eggs",
        "display_name": "Vegetarian + Eggs",
        "forbidden_rules": [
            (r"\b(?:chicken|mutton|lamb|goat|beef|pork|bacon|ham|meat|poultry|turkey|veal)\b", "Meat / Poultry"),
            (r"\b(?:fish|prawns?|shrimps?|crabs?|lobsters?|clams?|oysters?|mussels?|squids?|tuna|salmon|anchov(?:y|ies))\b", "Fish / Seafood"),
            (r"\b(?:gelatins?|gelatines?|collagen|isinglass|carmine|cochineal|e\s*120|ins\s*120|tallow|lard|animal\s*rennet)\b", "Gelatin / Animal derivatives"),
        ],
        "compliance_message": "Suitable for Ovo-Vegetarian standards (no meat, poultry, or fish; eggs and dairy permitted).",
        "conflict_message_prefix": "Not suitable for Ovo-Vegetarian diet: Contains",
    },
    "jain": {
        "id": "jain",
        "display_name": "Jain Food Preferences",
        "forbidden_rules": [
            (r"\beggs?\b|\banda\b|\bande\b|\balbumen\b|\bovalbumin\b|(?<!eggless\s)\bmayonnaise\b", "Eggs"),
            (r"\b(?:chicken|mutton|lamb|goat|beef|pork|meat|fish|seafood)\b", "Meat / Seafood"),
            (r"\b(?:gelatins?|gelatines?|collagen|carmine|cochineal|e\s*120|ins\s*120|animal\s*rennet)\b", "Gelatin / Animal derivatives"),
            (r"\b(?:onions?|pyaz|pyaj|dehydrated\s*onion)\b", "Onion"),
            (r"\b(?:garlic|lahsun|lasun)\b", "Garlic"),
            (r"\b(?:potato(?:es)?|aloo|alu|potato\s*starch)\b", "Potato"),
            (r"\b(?:carrots?|gajar)\b", "Carrot"),
            (r"\b(?:radish(?:es)?|mooli)\b", "Radish"),
            (r"\b(?:beetroots?|beet|chukandar)\b", "Beetroot"),
            (r"\b(?:ginger|adrak)\b", "Ginger"),
            (r"\b(?:turnips?|shalgam|yam|suran|jimikand|sweet\s*potato|shakarkand)\b", "Root Vegetables"),
        ],
        "compliance_message": "Suitable for Jain dietary preferences (no root vegetables, onions, garlic, potato, eggs, or animal derivatives).",
        "conflict_message_prefix": "Not suitable for Jain dietary preferences: Contains restricted ingredient(s)",
    },
}

NUTRITION_GOAL_RULES = {
    "more_protein": {
        "id": "more_protein",
        "label": "More protein",
        "nutrient_key": "protein_g",
        "threshold": 5.0,
        "is_upper_bound": False,
        "target_desc": ">= 5.0g per serve",
    },
    "lower_calories": {
        "id": "lower_calories",
        "label": "Lower calories",
        "nutrient_key": "kcal",
        "threshold": 150.0,
        "is_upper_bound": True,
        "target_desc": "<= 150 kcal per serve",
    },
    "lower_sugar": {
        "id": "lower_sugar",
        "label": "Lower sugar",
        "nutrient_key": "sugars_g",
        "threshold": 5.0,
        "is_upper_bound": True,
        "target_desc": "<= 5.0g per serve",
    },
    "higher_fibre": {
        "id": "higher_fibre",
        "label": "Higher fibre",
        "nutrient_key": "fibre_g",
        "threshold": 3.0,
        "is_upper_bound": False,
        "target_desc": ">= 3.0g per serve",
    },
    "lower_sodium": {
        "id": "lower_sodium",
        "label": "Lower sodium",
        "nutrient_key": "sodium_mg",
        "threshold": 200.0,
        "is_upper_bound": True,
        "target_desc": "<= 200mg per serve",
    },
    "lower_saturated_fat": {
        "id": "lower_saturated_fat",
        "label": "Lower saturated fat",
        "nutrient_key": "saturated_fat_g",
        "threshold": 2.0,
        "is_upper_bound": True,
        "target_desc": "<= 2.0g per serve",
    },
}


class PersonalizedScoringEngine:
    """
    Evidence-based Nutritional Personalization & Multi-Condition Rating Engine.
    Implements:
    1) PERSONALISED RATING (1-10, lower = better):
       - nutrient_rating: weighted r_k with clinical worst-case safety floor: max(base, 0.7*max(r_k) + 0.3*base)
       - ingredient_rating: position weights (first=n, last=1) with flagged override: max(base, 0.7*worst_flagged + 0.3*base)
         including condition-specific risk values from ingredient_risks.json.
       - product_rating: 0.6 * nutrient_rating + 0.4 * ingredient_rating
       - Multiple conditions: strictest (lowest) limit, highest weight per nutrient
       - Depends ONLY on nutrients vs health condition limits/weights, ingredient risks, and health conditions.
    2) ALLERGY CHECK: Separate hard rule (NOT SAFE FOR YOU / CANNOT CONFIRM / NONE FOUND). If NOT SAFE, show no rating.
    3) RECOMMENDATIONS: In the same category, exclude products with allergy status NOT SAFE, rank by
       Personalised Rating (lowest first), breaking ties by fewer CONTRADICTED / MISLEADING claims.
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
            # Map condition aliases to canonical profile keys
            if clean_key in ["high_blood_pressure", "bp"]:
                clean_key = "hypertension"
            
            # Gate-type conditions are handled by allergy & safety check gates, not nutrient limits
            if clean_key in ["coeliac_disease", "coeliac", "celiac", "celiac_disease", "lactose_intolerance"]:
                continue

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

        if not merged_nutrients:
            default_p = self.profiles_config.get("general_health", {})
            merged_nutrients = {k: dict(v) for k, v in default_p.get("nutrients", {}).items()}
            if not names:
                names = [default_p.get("name", "General Health-Aware")]
                descriptions = [default_p.get("description", "")]

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
        oil_declared: str = "",
        selected_conditions: Optional[List[str]] = None
    ) -> Tuple[Optional[float], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Computes ingredient_rating (1-10, lower = better):
        Position weights (first = n, last = 1);
        Evaluates ingredient risks including condition-specific risk values;
        base = weighted average;
        if any flagged ingredient: max(base, 0.7*worst_flagged + 0.3*base)
        """
        norm_ingredients = []
        if isinstance(ingredients, str):
            norm_ingredients = [i.strip() for i in ingredients.split(",") if i.strip()]
        elif isinstance(ingredients, list):
            for item in ingredients:
                if isinstance(item, dict):
                    norm_ingredients.append(str(item.get("name", item)).strip())
                elif item:
                    norm_ingredients.append(str(item).strip())

        if oil_declared and oil_declared.lower() not in ["none declared", "no cooking oil declared"]:
            if not any(oil_declared.lower() in ing.lower() for ing in norm_ingredients):
                norm_ingredients.append(oil_declared)

        if not norm_ingredients:
            return None, [], {}

        active_conditions = [c.lower().strip() for c in (selected_conditions or ["general_health"])]

        n = len(norm_ingredients)
        scored_ingredients = []
        flagged_list = []

        for idx, ing_name in enumerate(norm_ingredients):
            pos_weight = n - idx  # first = n, last = 1
            risk_score = 1
            is_flagged = False
            flag_reason = "Whole or permitted food ingredient"
            rule_applied = None

            ing_lower = ing_name.lower()
            for rule in self.ingredient_rules:
                pat = rule.get("pattern", "")
                if re.search(pat, ing_lower, re.IGNORECASE):
                    risk_score = rule.get("risk_score", 1)
                    # Condition-specific risk lookup
                    condition_risks = rule.get("condition_risks", {})
                    for cond in active_conditions:
                        if cond in condition_risks:
                            risk_score = max(risk_score, condition_risks[cond])

                    is_flagged = rule.get("flagged", False)
                    flag_reason = rule.get("reason", "")
                    rule_applied = rule
                    break

            item_data = {
                "name": ing_name,
                "position": idx + 1,
                "position_weight": pos_weight,
                "risk_score": risk_score,
                "is_flagged": is_flagged,
                "flag_reason": flag_reason,
                "weighted_contribution": pos_weight * risk_score,
                "source_name": rule_applied.get("source_name", "FSSAI Food Additives & Labelling Standards") if rule_applied else "FSSAI Packaging Standards",
                "source_url": rule_applied.get("source_url", "https://www.fssai.gov.in") if rule_applied else "https://www.fssai.gov.in",
                "access_date": rule_applied.get("access_date", "2026-10-24") if rule_applied else "2026-10-24",
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
        (if one is None use the other and mark partial data)
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
        user_allergens: List[str],
        product_name: str = "",
        extra_text: str = "",
    ) -> Dict[str, Any]:
        """
        ALLERGY CHECK stays a separate hard rule:
        NOT SAFE FOR YOU / CANNOT CONFIRM / NONE FOUND.
        If NOT SAFE FOR YOU, show no rating.
        Checks all user declared allergens and gate condition targets against
        the ingredients list, declared oils, product name, and allergen disclosures.
        """
        if not user_allergens:
            return {
                "allergy_status": "NONE FOUND",
                "found_allergens": [],
                "is_safe": True,
                "message": "No user allergen restrictions declared.",
            }

        text_corpus = []
        if product_name:
            text_corpus.append(str(product_name))
        if extra_text:
            text_corpus.append(str(extra_text))

        if isinstance(ingredients, str):
            text_corpus.append(ingredients)
        elif isinstance(ingredients, list):
            for i in ingredients:
                if isinstance(i, dict):
                    text_corpus.append(str(i.get("name", "")))
                    if "sub_ingredients" in i:
                        text_corpus.append(str(i["sub_ingredients"]))
                    if "allergens" in i and isinstance(i["allergens"], list):
                        text_corpus.extend([str(a) for a in i["allergens"]])
                elif i:
                    text_corpus.append(str(i))
        elif isinstance(ingredients, dict):
            val = ingredients.get("value")
            if isinstance(val, list):
                for i in val:
                    text_corpus.append(str(i.get("name", i) if isinstance(i, dict) else i))
            elif val:
                text_corpus.append(str(val))

        if oil_declared:
            if isinstance(oil_declared, dict):
                text_corpus.append(str(oil_declared.get("value", "")))
            else:
                text_corpus.append(str(oil_declared))

        full_text = " ".join(text_corpus).strip().lower()

        if not full_text:
            return {
                "allergy_status": "CANNOT CONFIRM",
                "found_allergens": [],
                "is_safe": False,
                "message": "CANNOT CONFIRM: Ingredient declaration is missing or incomplete.",
            }

        found_allergens = []
        for user_al in user_allergens:
            u_raw = str(user_al).strip()
            u_clean = u_raw.lower()
            if not u_clean:
                continue

            matched_cats = []
            if u_clean in ALLERGEN_CATEGORIES:
                matched_cats.append((u_clean, ALLERGEN_CATEGORIES[u_clean]))
            else:
                for cat_key, cat_data in ALLERGEN_CATEGORIES.items():
                    if u_clean in cat_data["aliases"]:
                        matched_cats.append((cat_key, cat_data))
                        break
                if not matched_cats:
                    for cat_key, cat_data in ALLERGEN_CATEGORIES.items():
                        if any(a in u_clean for a in cat_data["aliases"]):
                            matched_cats.append((cat_key, cat_data))
                            break

            detected = False
            if matched_cats:
                for cat_key, cat_data in matched_cats:
                    for pat in cat_data["patterns"]:
                        if re.search(pat, full_text, re.IGNORECASE):
                            disp = cat_data["display_name"] if "_" in u_raw else u_raw.title()
                            found_allergens.append(disp)
                            detected = True
                            break
                    if detected:
                        break
            else:
                clean_tok = re.sub(r'[^a-z0-9\s]', ' ', u_clean).strip()
                if clean_tok:
                    words = clean_tok.split()
                    for w in words:
                        if len(w) >= 3 and re.search(r'\b' + re.escape(w) + r's?\b', full_text, re.IGNORECASE):
                            found_allergens.append(u_raw.title())
                            break

        if found_allergens:
            unique_found = list(dict.fromkeys(found_allergens))
            return {
                "allergy_status": "NOT SAFE FOR YOU",
                "found_allergens": unique_found,
                "is_safe": False,
                "message": f"NOT SAFE FOR YOU: Contains declared allergen(s): {', '.join(unique_found)}.",
            }

        return {
            "allergy_status": "NONE FOUND",
            "found_allergens": [],
            "is_safe": True,
            "message": "NONE FOUND: None of your specified allergens were detected in label statement.",
        }

    def check_avoid_ingredients(
        self,
        ingredients: List[Any],
        oil_declared: str,
        avoid_ingredients: List[str],
        product_name: str = "",
        extra_text: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluates Section 04 Ingredients to Avoid.
        Does NOT alter the clinical 1-10 rating, but flags detected items clearly for the user.
        """
        if not avoid_ingredients:
            return {
                "has_conflict": False,
                "avoided_ingredients_found": [],
                "status": "NONE SPECIFIED",
                "message": "No ingredients marked to avoid.",
            }

        text_corpus = []
        if product_name:
            text_corpus.append(str(product_name))
        if extra_text:
            text_corpus.append(str(extra_text))
        if oil_declared and str(oil_declared).lower() != "none declared":
            text_corpus.append(str(oil_declared))

        if isinstance(ingredients, str):
            text_corpus.append(ingredients)
        elif isinstance(ingredients, list):
            for i in ingredients:
                if isinstance(i, dict):
                    text_corpus.append(str(i.get("name", "")))
                    if "sub_ingredients" in i:
                        text_corpus.append(str(i["sub_ingredients"]))
                elif i:
                    text_corpus.append(str(i))

        full_text = " ".join(text_corpus).lower()
        detected_items = []

        for item_key in avoid_ingredients:
            clean_k = item_key.strip().lower()
            rule = None
            for r_key, r_spec in AVOID_INGREDIENT_RULES.items():
                if clean_k in r_spec["aliases"] or clean_k == r_key:
                    rule = r_spec
                    break

            if not rule:
                continue

            matched_terms = []
            for pat in rule["patterns"]:
                m = re.findall(pat, full_text, re.IGNORECASE)
                if m:
                    for found in m:
                        s_str = found if isinstance(found, str) else str(found[0] if found else "")
                        s_clean = s_str.strip()
                        if s_clean and s_clean not in matched_terms:
                            matched_terms.append(s_clean)

            if matched_terms:
                detected_items.append({
                    "id": rule["id"],
                    "label": rule["display_name"],
                    "matched_terms": matched_terms[:4],
                    "warning": rule["warning"],
                })

        has_conflict = len(detected_items) > 0
        names = [d["label"] for d in detected_items]
        return {
            "has_conflict": has_conflict,
            "avoided_ingredients_found": detected_items,
            "status": "CONTAINS AVOIDED INGREDIENTS" if has_conflict else "NONE FOUND",
            "message": f"Contains avoided ingredient(s): {', '.join(names)}." if has_conflict else "None of your selected avoided ingredients were detected.",
        }

    def check_dietary_pattern(
        self,
        ingredients: List[Any],
        oil_declared: str,
        dietary_pattern: str,
        product_name: str = "",
        extra_text: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluates Section 05 Dietary Pattern (Vegetarian, Vegan, Vegetarian + eggs, Jain).
        Flags any non-compliant ingredient.
        """
        clean_pat = (dietary_pattern or "none").strip().lower()
        if clean_pat in ["none", "no specific dietary pattern", ""]:
            return {
                "pattern_id": "none",
                "pattern_name": "No specific dietary pattern",
                "is_compliant": True,
                "status": "NOT_APPLICABLE",
                "conflicts": [],
                "message": "No specific dietary pattern configured.",
            }

        rule = DIETARY_PATTERN_RULES.get(clean_pat)
        if not rule:
            for r_key, r_spec in DIETARY_PATTERN_RULES.items():
                if clean_pat == r_spec["display_name"].lower() or r_key in clean_pat:
                    rule = r_spec
                    break

        if not rule:
            return {
                "pattern_id": clean_pat,
                "pattern_name": clean_pat.title(),
                "is_compliant": True,
                "status": "UNKNOWN_PATTERN",
                "conflicts": [],
                "message": "Custom dietary pattern.",
            }

        text_corpus = []
        if product_name:
            text_corpus.append(str(product_name))
        if extra_text:
            text_corpus.append(str(extra_text))
        if oil_declared and str(oil_declared).lower() != "none declared":
            text_corpus.append(str(oil_declared))

        if isinstance(ingredients, str):
            text_corpus.append(ingredients)
        elif isinstance(ingredients, list):
            for i in ingredients:
                if isinstance(i, dict):
                    text_corpus.append(str(i.get("name", "")))
                    if "sub_ingredients" in i:
                        text_corpus.append(str(i["sub_ingredients"]))
                elif i:
                    text_corpus.append(str(i))

        full_text = " ".join(text_corpus).lower()
        conflicts = []

        for pat, reason in rule["forbidden_rules"]:
            if re.search(pat, full_text, re.IGNORECASE):
                if reason not in conflicts:
                    conflicts.append(reason)

        is_compliant = (len(conflicts) == 0)
        if is_compliant:
            return {
                "pattern_id": rule["id"],
                "pattern_name": rule["display_name"],
                "is_compliant": True,
                "status": "COMPLIANT",
                "conflicts": [],
                "message": rule["compliance_message"],
            }
        else:
            return {
                "pattern_id": rule["id"],
                "pattern_name": rule["display_name"],
                "is_compliant": False,
                "status": "CONFLICT DETECTED",
                "conflicts": conflicts,
                "message": f"{rule['conflict_message_prefix']} {', '.join(conflicts)}.",
            }

    def check_nutrition_goals(
        self,
        nutrition_data: Dict[str, Any],
        nutrition_goals: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluates Section 03 Nutrition Goals against actual product nutrition metrics.
        """
        if not nutrition_goals:
            return {
                "has_goals": False,
                "goals": [],
                "met_count": 0,
                "total_count": 0,
            }

        evaluated_goals = []
        for g_id in nutrition_goals:
            g_clean = g_id.strip().lower()
            rule = NUTRITION_GOAL_RULES.get(g_clean)
            if not rule:
                for r_key, r_spec in NUTRITION_GOAL_RULES.items():
                    if g_clean == r_spec["label"].lower() or r_key in g_clean:
                        rule = r_spec
                        break
            if not rule:
                continue

            n_key = rule["nutrient_key"]
            nutri_item = nutrition_data.get(n_key, {})
            if isinstance(nutri_item, dict):
                actual_val = nutri_item.get("value", 0.0)
            elif isinstance(nutri_item, (int, float)):
                actual_val = float(nutri_item)
            else:
                actual_val = 0.0

            thresh = rule["threshold"]
            if rule["is_upper_bound"]:
                is_met = (actual_val <= thresh)
            else:
                is_met = (actual_val >= thresh)

            evaluated_goals.append({
                "id": rule["id"],
                "label": rule["label"],
                "is_met": is_met,
                "actual_value": actual_val,
                "target_description": rule["target_desc"],
                "status_text": f"Goal Met: {actual_val}" if is_met else f"Goal Exceeded: {actual_val} ({rule['target_desc']})",
            })

        met_count = sum(1 for g in evaluated_goals if g["is_met"])
        return {
            "has_goals": len(evaluated_goals) > 0,
            "goals": evaluated_goals,
            "met_count": met_count,
            "total_count": len(evaluated_goals),
        }

    def rank_recommendations(
        self,
        current_product: Dict[str, Any],
        candidate_products: List[Dict[str, Any]],
        selected_conditions: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None,
        avoid_ingredients: Optional[List[str]] = None,
        dietary_pattern: Optional[str] = "none",
        nutrition_goals: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        RECOMMENDATIONS: in the same category, exclude products with allergy status NOT SAFE,
        and exclude products non-compliant with the user's dietary pattern,
        then rank by Personalised Rating (lowest first).
        Break ties by fewer CONTRADICTED / MISLEADING claims.
        Show the reason in plain words using nutrient and ingredient findings only.
        """
        selected_conditions = selected_conditions or ["general_health"]
        user_allergens = user_allergens or []
        avoid_ingredients = avoid_ingredients or []
        dietary_pattern = dietary_pattern or "none"

        active_allergens = list(user_allergens)
        for cond in selected_conditions:
            c_lower = str(cond).lower().strip()
            if any(k in c_lower for k in ["coeliac", "celiac"]):
                if not any(a.lower() in ["gluten", "wheat"] for a in active_allergens):
                    active_allergens.append("gluten")
            elif any(k in c_lower for k in ["lactose"]):
                if not any(a.lower() in ["milk", "dairy", "lactose"] for a in active_allergens):
                    active_allergens.append("milk")

        # Trigger check on current product
        p_eval = self.evaluate(
            product_data=current_product,
            selected_conditions=selected_conditions,
            user_allergens=active_allergens,
            avoid_ingredients=avoid_ingredients,
            dietary_pattern=dietary_pattern,
            nutrition_goals=nutrition_goals,
        )
        p_rating = p_eval.get("product_rating")
        p_allergy = p_eval.get("allergy_check", {})
        has_allergen_conflict = (p_allergy.get("allergy_status") == "NOT SAFE FOR YOU")
        p_pattern = p_eval.get("dietary_pattern_check", {})
        has_pattern_conflict = not p_pattern.get("is_compliant", True)
        is_p_rating_valid = (p_rating is not None and isinstance(p_rating, (int, float)) and 1.0 <= p_rating <= 10.0)

        is_high_rating = (is_p_rating_valid and p_rating > 3.0)
        if not is_high_rating and not has_allergen_conflict and not has_pattern_conflict:
            return []

        # Determine target category
        curr_cat_val = ""
        cat_item = current_product.get("category", {})
        if isinstance(cat_item, dict):
            curr_cat_val = str(cat_item.get("value", "")).strip().lower()
        else:
            curr_cat_val = str(cat_item or "").strip().lower()

        current_name = ""
        name_item = current_product.get("product_name", {})
        if isinstance(name_item, dict):
            current_name = str(name_item.get("value", "")).strip().lower()
        else:
            current_name = str(name_item or "").strip().lower()

        # Combine candidates with built-in reference products for complete category coverage
        all_candidates = []
        seen_names = set()

        pool = candidate_products if candidate_products else CATEGORY_REFERENCE_PRODUCTS
        for c in pool:
            cand_name = ""
            c_name_item = c.get("product_name", {})
            if isinstance(c_name_item, dict):
                cand_name = str(c_name_item.get("value", "")).strip()
            else:
                cand_name = str(c_name_item or "").strip()

            if not cand_name:
                continue
            name_clean = cand_name.lower()
            if name_clean == current_name or name_clean in seen_names:
                continue
            seen_names.add(name_clean)

            # Filter for same category
            cand_cat = ""
            c_cat_item = c.get("category", {})
            if isinstance(c_cat_item, dict):
                cand_cat = str(c_cat_item.get("value", "")).strip().lower()
            else:
                cand_cat = str(c_cat_item or "").strip().lower()

            # Flexible category comparison
            is_same_category = False
            if curr_cat_val and cand_cat:
                if curr_cat_val in cand_cat or cand_cat in curr_cat_val:
                    is_same_category = True
                elif any(k in curr_cat_val and k in cand_cat for k in ["snack", "noodle", "drink", "beverage", "biscuit", "chip"]):
                    is_same_category = True
            elif not curr_cat_val:
                is_same_category = True

            if is_same_category:
                all_candidates.append(c)

        ranked_results = []

        for candidate in all_candidates:
            c_ing = candidate.get("ingredients", [])
            c_oil_item = candidate.get("oil_listed", {})
            c_oil = c_oil_item.get("value", "") if isinstance(c_oil_item, dict) else str(c_oil_item or "")
            c_nutrition = candidate.get("nutrition", {})
            c_claims = candidate.get("front_pack_claims", [])

            # 1. Allergy check: exclude NOT SAFE FOR YOU
            c_name_item = candidate.get("product_name", {})
            c_name_val = str(c_name_item.get("value", "") if isinstance(c_name_item, dict) else c_name_item or "")
            allergy_res = self.check_allergens(
                ingredients=c_ing,
                oil_declared=c_oil,
                user_allergens=active_allergens,
                product_name=c_name_val,
            )
            if allergy_res["allergy_status"] == "NOT SAFE FOR YOU":
                continue

            # Exclude candidates that conflict with user's dietary pattern
            if dietary_pattern and dietary_pattern != "none":
                pattern_res = self.check_dietary_pattern(
                    ingredients=c_ing,
                    oil_declared=c_oil,
                    dietary_pattern=dietary_pattern,
                    product_name=c_name_val,
                )
                if not pattern_res["is_compliant"]:
                    continue

            # 2. Personalised Rating (depends ONLY on nutrients, health conditions, ingredient risks)
            nutri_r, _ = self.calculate_nutrient_rating(c_nutrition, selected_conditions)
            ing_r, top_ing, worst_fl = self.calculate_ingredient_rating(c_ing, c_oil, selected_conditions)
            prod_r, _, _ = self.calculate_product_rating(nutri_r, ing_r)

            if prod_r is None or not (1.0 <= prod_r <= 10.0):
                continue

            if is_high_rating:
                if not (is_p_rating_valid and prod_r <= (p_rating - 1.0)):
                    continue
            else:
                if not (prod_r <= 3.0):
                    continue

            # 3. Count contradicted / misleading claims for tie-breaking
            flagged_claims_count = sum(
                1 for cl in (c_claims or [])
                if str(cl.get("audit_verdict", "")).upper() in ["CONTRADICTED", "MISLEADING"]
            )

            # 4. Reason in plain words using nutrient and ingredient findings only
            reasons = []
            c_sat_fat = c_nutrition.get("saturated_fat_g", {})
            sat_val = c_sat_fat.get("value", 0.0) if isinstance(c_sat_fat, dict) else float(c_sat_fat or 0.0)
            if sat_val <= 1.5:
                reasons.append(f"Low saturated fat ({sat_val}g/serve)")

            c_sugars = c_nutrition.get("sugars_g", {})
            sug_val = c_sugars.get("value", 0.0) if isinstance(c_sugars, dict) else float(c_sugars or 0.0)
            if sug_val <= 3.0:
                reasons.append(f"Low sugar ({sug_val}g/serve)")

            c_sodium = c_nutrition.get("sodium_mg", {})
            sod_val = c_sodium.get("value", 0.0) if isinstance(c_sodium, dict) else float(c_sodium or 0.0)
            if sod_val <= 300.0:
                reasons.append(f"Controlled sodium ({sod_val}mg/serve)")

            # Ingredient findings
            is_palm = False
            if isinstance(c_oil_item, dict):
                is_palm = c_oil_item.get("is_palm_oil", False)
            if not is_palm and "palm" not in c_oil.lower():
                if c_oil and c_oil.lower() not in ["none declared", "no cooking oil declared"]:
                    reasons.append(f"Uses {c_oil} instead of palmolein")
                else:
                    reasons.append("No palmolein or hydrogenated fat used")

            if not worst_fl.get("is_flagged"):
                reasons.append("Contains no flagged high-risk industrial additives")

            if not reasons:
                reasons.append(f"Personalised rating {prod_r}/10 with {sug_val}g sugar and {sat_val}g saturated fat")

            plain_reason = f"Personalised rating {prod_r}/10. {'; '.join(reasons)}."

            cand_brand = candidate.get("brand", {})
            b_val = cand_brand.get("value", "") if isinstance(cand_brand, dict) else str(cand_brand or "")

            cand_name_val = candidate.get("product_name", {})
            n_val = cand_name_val.get("value", "") if isinstance(cand_name_val, dict) else str(cand_name_val or "")

            ranked_results.append({
                "product_name": n_val,
                "brand": b_val,
                "personalised_rating": prod_r,
                "nutrient_rating": nutri_r,
                "ingredient_rating": ing_r,
                "flagged_claims_count": flagged_claims_count,
                "allergy_status": allergy_res["allergy_status"],
                "recommendation_reason": plain_reason,
                "source_url": candidate.get("product_name", {}).get("source_url", "") if isinstance(candidate.get("product_name"), dict) else "",
            })

        # Rank by Personalised Rating (lowest first), break ties by fewer flagged claims, then name
        ranked_results.sort(key=lambda x: (x["personalised_rating"], x["flagged_claims_count"], x["product_name"].lower()))
        diverse_results = []
        brand_counts = {}
        for r in ranked_results:
            b = r["brand"].strip().lower()
            if brand_counts.get(b, 0) < 2:
                brand_counts[b] = brand_counts.get(b, 0) + 1
                diverse_results.append(r)
                if len(diverse_results) == 5:
                    break
        return diverse_results

    def evaluate(
        self,
        product_data: Dict[str, Any],
        selected_conditions: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None,
        avoid_ingredients: Optional[List[str]] = None,
        dietary_pattern: Optional[str] = "none",
        nutrition_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Master evaluation pipeline implementing Personalised Rating, Allergy Check,
        Avoid Ingredients Check, Dietary Pattern Check, and Nutrition Goals alignment.
        Personalised Rating depends ONLY on:
        - nutrient values vs selected health condition limits and weights
        - ingredient risk values from ingredient_risks.json (including condition-specific values)
        - selected health conditions
        Nothing else may change it: no claim verdicts or secondary signals.
        """
        selected_conditions = selected_conditions or ["general_health"]
        user_allergens = user_allergens or []
        avoid_ingredients = avoid_ingredients or []
        dietary_pattern = dietary_pattern or "none"
        nutrition_goals = nutrition_goals or []

        nutrition = product_data.get("nutrition", {})
        ingredients = product_data.get("ingredients", [])
        oil_info = product_data.get("oil_listed", {})
        oil_declared = oil_info.get("value", "") if isinstance(oil_info, dict) else str(oil_info or "")

        # Gate conditions integration: coeliac_disease -> gluten, lactose_intolerance -> milk/lactose
        active_allergens = list(user_allergens)
        for cond in selected_conditions:
            c_lower = str(cond).lower().strip()
            if any(k in c_lower for k in ["coeliac", "celiac"]):
                if not any(a.lower() in ["gluten", "wheat"] for a in active_allergens):
                    active_allergens.append("gluten")
            elif any(k in c_lower for k in ["lactose"]):
                if not any(a.lower() in ["milk", "dairy", "lactose"] for a in active_allergens):
                    active_allergens.append("milk")

        p_name = ""
        p_name_item = product_data.get("product_name", {})
        if isinstance(p_name_item, dict):
            p_name = str(p_name_item.get("value", ""))
        else:
            p_name = str(p_name_item or "")

        extra_info_parts = []
        for extra_k in ["allergens", "allergen_info", "allergy_advice", "may_contain", "may_contain_allergens", "allergen_statement"]:
            v = product_data.get(extra_k)
            if isinstance(v, list):
                extra_info_parts.extend([str(item) for item in v if item])
            elif isinstance(v, str) and v:
                extra_info_parts.append(v)

        extra_text_joined = " ".join(extra_info_parts)

        # 1. Allergy & Gate Check (Hard Rule: runs before any rating and can hide it)
        allergy_res = self.check_allergens(
            ingredients=ingredients,
            oil_declared=oil_declared,
            user_allergens=active_allergens,
            product_name=p_name,
            extra_text=extra_text_joined,
        )

        # 2. Section 04: Ingredients to Avoid Check
        avoid_res = self.check_avoid_ingredients(
            ingredients=ingredients,
            oil_declared=oil_declared,
            avoid_ingredients=avoid_ingredients,
            product_name=p_name,
            extra_text=extra_text_joined,
        )

        # 3. Section 05: Dietary Pattern Check
        pattern_res = self.check_dietary_pattern(
            ingredients=ingredients,
            oil_declared=oil_declared,
            dietary_pattern=dietary_pattern,
            product_name=p_name,
            extra_text=extra_text_joined,
        )

        # 4. Section 03: Nutrition Goals Check
        goals_res = self.check_nutrition_goals(
            nutrition_data=nutrition,
            nutrition_goals=nutrition_goals,
        )

        # 5. Nutrient Rating (1-10, lower = better)
        nutri_rating, nutri_breakdown = self.calculate_nutrient_rating(nutrition, selected_conditions)

        # 6. Ingredient Rating (1-10, lower = better)
        ing_rating, top_ingredients, worst_flagged = self.calculate_ingredient_rating(
            ingredients=ingredients,
            oil_declared=oil_declared,
            selected_conditions=selected_conditions
        )

        # 7. Overall Product Rating (1-10, 0.6 * nutrient + 0.4 * ingredient)
        prod_rating, is_partial, partial_reason = self.calculate_product_rating(nutri_rating, ing_rating)

        _, condition_name, condition_desc = self.merge_conditions(selected_conditions)

        # Hard Rule: If NOT SAFE FOR YOU, show no rating
        if allergy_res["allergy_status"] == "NOT SAFE FOR YOU":
            return {
                "allergy_check": allergy_res,
                "avoid_ingredients_check": avoid_res,
                "dietary_pattern_check": pattern_res,
                "nutrition_goals_check": goals_res,
                "avoid_ingredients_applied": avoid_ingredients,
                "dietary_pattern_applied": dietary_pattern,
                "nutrition_goals_applied": nutrition_goals,
                "show_scores": False,
                "show_rating": False,
                "product_rating": None,
                "nutrient_rating": None,
                "ingredient_rating": None,
                "selected_conditions": selected_conditions,
                "conditions_title": condition_name,
                "conditions_description": condition_desc,
                "nutrient_breakdown": nutri_breakdown,
                "top_ingredients": top_ingredients,
                "worst_flagged": worst_flagged,
                "is_partial_data": is_partial,
                "partial_data_note": partial_reason,
            }

        return {
            "allergy_check": allergy_res,
            "avoid_ingredients_check": avoid_res,
            "dietary_pattern_check": pattern_res,
            "nutrition_goals_check": goals_res,
            "avoid_ingredients_applied": avoid_ingredients,
            "dietary_pattern_applied": dietary_pattern,
            "nutrition_goals_applied": nutrition_goals,
            "show_scores": True,
            "show_rating": True,
            "product_rating": prod_rating,
            "nutrient_rating": nutri_rating,
            "ingredient_rating": ing_rating,
            "selected_conditions": selected_conditions,
            "conditions_title": condition_name,
            "conditions_description": condition_desc,
            "nutrient_breakdown": nutri_breakdown,
            "top_ingredients": top_ingredients,
            "worst_flagged": worst_flagged,
            "is_partial_data": is_partial,
            "partial_data_note": partial_reason,
        }
