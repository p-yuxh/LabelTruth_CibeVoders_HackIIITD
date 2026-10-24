from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Vision Extraction Schema (Step 2.c)
# ---------------------------------------------------------
PhotoType = Literal["front", "back", "barcode", "ingredient_panel", "other"]


class VisionExtractionResult(BaseModel):
    photo_type: PhotoType = Field(
        ...,
        description="Type of food product photo: front, back, barcode, ingredient_panel, or other"
    )
    brand: Optional[str] = Field(
        None,
        description="Brand name if visible, else null"
    )
    product_name: Optional[str] = Field(
        None,
        description="Product name if visible, else null"
    )
    variant_or_flavour: Optional[str] = Field(
        None,
        description="Variant, flavor, or sub-brand (e.g. 'Cream & Onion', 'Double Chocolate') if visible, else null"
    )
    net_weight_or_volume: Optional[str] = Field(
        None,
        description="Net weight or volume (e.g. '50g', '500ml', '1.2 kg') if visible, else null"
    )
    language: Optional[str] = Field(
        None,
        description="Primary language code of the packaging text (e.g. 'en', 'hi', 'fr'), else null"
    )
    visible_ingredient_text: Optional[str] = Field(
        None,
        description="Raw visible ingredient text if readable on the image, else null"
    )
    legibility: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Legibility score from 0.0 (unreadable) to 1.0 (crystal clear)"
    )


# ---------------------------------------------------------
# Barcode Result Schema (Step 2.a)
# ---------------------------------------------------------
class BarcodeResult(BaseModel):
    code: str = Field(..., description="Decoded barcode value")
    format: str = Field(..., description="Barcode format (e.g., EAN-13, EAN-8, UPC-A)")
    valid_check_digit: bool = Field(True, description="Whether the GS1 check digit passed validation")


# ---------------------------------------------------------
# OCR Result Schema (Step 2.b)
# ---------------------------------------------------------
class OCRTextBlock(BaseModel):
    text: str = Field(..., description="Detected text content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox: Optional[List[List[float]]] = Field(
        None,
        description="Optional bounding box polygon coordinates [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]"
    )


class OCRResult(BaseModel):
    blocks: List[OCRTextBlock] = Field(default_factory=list, description="List of detected text blocks")
    full_text: str = Field("", description="Consolidated text across all blocks")
    avg_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Average confidence score across text blocks")


# ---------------------------------------------------------
# Single Image Triage Result
# ---------------------------------------------------------
class ImageTriageResult(BaseModel):
    image_index: int = Field(..., description="Index of the image in the uploaded list (1-based)")
    barcode: Optional[BarcodeResult] = Field(None, description="Decoded barcode if present")
    ocr: OCRResult = Field(..., description="Extracted OCR text and confidence")
    vision: VisionExtractionResult = Field(..., description="Structured vision extraction result")


# ---------------------------------------------------------
# Merged Extracted Signals Schema (Phase 1 POST /analyze)
# ---------------------------------------------------------
class MergedSignals(BaseModel):
    barcode: Optional[str] = Field(None, description="Valid decoded barcode from any of the images")
    brand: Optional[str] = Field(None, description="Best identified brand name")
    product_name: Optional[str] = Field(None, description="Best identified product name")
    variant_or_flavour: Optional[str] = Field(None, description="Best identified variant or flavour")
    net_weight_or_volume: Optional[str] = Field(None, description="Best identified net weight or volume")
    language: Optional[str] = Field(None, description="Primary packaging language")
    user_ocr_ingredients: Optional[str] = Field(
        None,
        description="OCR text preserved if any image is an ingredient_panel or back photo with legibility >= 0.7"
    )
    images: List[ImageTriageResult] = Field(
        default_factory=list,
        description="Detailed triage breakdown per submitted photo"
    )


# ---------------------------------------------------------
# Candidate Product Schema (Step 3)
# ---------------------------------------------------------
SourceType = Literal["manufacturer", "gs1", "open_food_facts", "retailer"]


class CandidateProduct(BaseModel):
    source: str = Field(..., description="Source name (e.g. Open Food Facts, Manufacturer Website)")
    source_url: Optional[str] = Field(None, description="URL of the source page")
    source_type: SourceType = Field(..., description="Classification of source")
    brand: Optional[str] = Field(None, description="Candidate brand name")
    name: str = Field(..., description="Candidate product name")
    variant: Optional[str] = Field(None, description="Candidate variant or flavour")
    size: Optional[str] = Field(None, description="Candidate pack size / net weight")
    ingredients_text: Optional[str] = Field(None, description="Raw ingredients text from candidate")
    nutrition: Optional[Dict[str, Any]] = Field(None, description="Candidate nutrition key-values")
    barcode: Optional[str] = Field(None, description="Candidate barcode")
    match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="RapidFuzz weighted match score")


# ---------------------------------------------------------
# Final JSON Output Schema (Step 9)
# ---------------------------------------------------------
AuditStatus = Literal["ok", "needs_confirmation", "needs_better_photo"]


class ProductInfo(BaseModel):
    brand: Optional[str] = None
    name: Optional[str] = None
    variant: Optional[str] = None
    size: Optional[str] = None
    barcode: Optional[str] = None


class IngredientDetail(BaseModel):
    name: str
    percentage: Optional[float] = None
    raw: str = ""


class AllergensOutput(BaseModel):
    contains: List[str] = Field(default_factory=list)
    may_contain: List[str] = Field(default_factory=list)


class NutritionPer100g(BaseModel):
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    sugars_g: Optional[float] = None
    fat_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    fibre_g: Optional[float] = None
    sodium_mg: Optional[float] = None


class Provenance(BaseModel):
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None
    match_score: Optional[float] = None
    label_mismatch: bool = False


class FinalProductResponse(BaseModel):
    status: AuditStatus
    product: ProductInfo
    ingredients: Optional[List[IngredientDetail]] = None
    ingredients_raw_text: Optional[str] = ""
    allergens: AllergensOutput = Field(default_factory=AllergensOutput)
    nutrition_per_100g: Optional[NutritionPer100g] = None
    provenance: Optional[Provenance] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    message_to_user: str = ""

