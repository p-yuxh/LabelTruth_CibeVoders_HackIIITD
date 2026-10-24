from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = Field(..., description="Product name or brand to audit", min_length=2)
    force_refresh: bool = Field(False, description="Bypass cache and force fresh web extraction")
    conditions: Optional[List[str]] = Field(default_factory=lambda: ["general_health"], description="List of health profiles / conditions (e.g. general_health, diabetes, hypertension, protein_conscious)")
    profile: Optional[str] = Field("general_health", description="Selected single health condition (legacy alias)")
    user_allergens: Optional[List[str]] = Field(default_factory=list, description="User declared allergens (e.g. peanut, milk, gluten, soy)")


class PersonalizeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_data: Dict[str, Any] = Field(..., description="Audited product data dictionary")
    conditions: Optional[List[str]] = Field(default_factory=lambda: ["general_health"], description="List of health profiles / conditions")
    profile: Optional[str] = Field("general_health", description="Legacy single profile key")
    user_allergens: Optional[List[str]] = Field(default_factory=list, description="User declared allergens")


class ValueWithSource(BaseModel):
    value: Any
    source_url: str


class NutritionMetric(BaseModel):
    value: Optional[float] = None
    unit: str = "g"
    source_url: str


class NutritionPerServing(BaseModel):
    serving_size: ValueWithSource
    kcal: Optional[NutritionMetric] = None
    carbs_g: Optional[NutritionMetric] = None
    sugars_g: Optional[NutritionMetric] = None
    added_sugars_g: Optional[NutritionMetric] = None
    protein_g: Optional[NutritionMetric] = None
    fat_g: Optional[NutritionMetric] = None
    saturated_fat_g: Optional[NutritionMetric] = None
    sodium_mg: Optional[NutritionMetric] = None


class IngredientItem(BaseModel):
    name: str
    is_palm_oil_or_derivative: bool = False
    is_allergen: bool = False
    is_additive: bool = False
    source_url: str


class OilListed(BaseModel):
    value: str
    is_palm_oil: bool = False
    source_url: str


class FrontPackClaim(BaseModel):
    claim: str
    category: str
    audit_verdict: str  # ONLY: "VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"
    verdict_reason: str
    source_url: str


class LabTestCoverage(BaseModel):
    has_lab_tests: bool = False
    summary: Optional[str] = None
    source_url: Optional[str] = None


class ProductAuditData(BaseModel):
    product_name: ValueWithSource
    brand: ValueWithSource
    category: ValueWithSource
    nutrition: NutritionPerServing
    ingredients: List[IngredientItem] = []
    oil_listed: OilListed
    front_pack_claims: List[FrontPackClaim] = []
    lab_test_coverage: LabTestCoverage = LabTestCoverage()
    summary: str
    personalized_scoring: Optional[Dict[str, Any]] = None
    reference_standards: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None


class AuditResponse(BaseModel):
    query: str
    is_cached: bool
    evidence_log_id: int
    created_at: str
    source_urls: List[str]
    data: ProductAuditData
    tinyfish_agent_raw: Optional[Dict[str, Any]] = None


class EvidenceLogItem(BaseModel):
    id: int
    query: str
    product_name: Optional[str]
    brand: Optional[str]
    source_urls: List[str]
    created_at: str
    updated_at: str
    product_data: Dict[str, Any]
