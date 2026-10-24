import io
import re
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps, ImageEnhance

logger = logging.getLogger("labeltruth.image_detector")

try:
    import pytesseract
except ImportError:
    pytesseract = None
    logger.warning("pytesseract is not available.")

# Comprehensive mapping of Indian FMCG brands and products
KNOWN_PRODUCTS = [
    # Chips & Savory Snacks
    (r"\blay['\s]?s|\blays\b", "Lays Potato Chips India"),
    (r"\b(?:potato\s*chips|salted\s*chips|magic\s*masala)\b", "Lays Potato Chips India"),
    (r"\bkurkure", "Kurkure Masala Munch"),
    (r"\btoo\s*yumm", "Too Yumm Multigrain Chips"),
    (r"\bbing?o", "Bingo Mad Angles"),
    (r"\bhaldiram['\s]?s?", "Haldirams Aloo Bhujia"),
    (r"\bbalaji", "Balaji Wafers"),
    (r"\bbikaji", "Bikaji Bhujia"),
    (r"\bpran\s*potata|potata\b", "Pran Potata Spicy Biscuits"),
    (r"\bdoritos\b", "Doritos Nacho Cheese"),
    (r"\bpringles\b", "Pringles Original Potato Crisps"),
    # Beverages & Soft Drinks
    (r"\b(?:diet\s*coke|coke\s*zero|coca[- ]?cola\s*zero)\b", "Coca-Cola Zero Sugar Diet Coke"),
    (r"\b(?:coca[- ]?cola|coke)\b", "Coca-Cola Original Taste"),
    (r"\bpepsi(?:\s*black)?\b", "Pepsi Black Zero Sugar"),
    (r"\bthums\s*up\b", "Thums Up Carbonated Beverage"),
    (r"\bsprite\b", "Sprite Lemon-Lime"),
    (r"\bfanta\b", "Fanta Orange Flavour"),
    (r"\bapp\s*fizz|appy\b", "Appy Fizz Sparkling Apple Juice"),
    (r"\bmaaza\b", "Maaza Mango Drink"),
    (r"\bfrooti\b", "Frooti Mango Drink"),
    (r"\bred\s*bull\b", "Red Bull Energy Drink"),
    (r"\bmonster\s*energy\b", "Monster Energy Drink"),
    # Health Drinks
    (r"\bbourn(?:v|u)ita", "Cadbury Bournvita"),
    (r"\bhorlicks", "Horlicks Classic Malt"),
    (r"\bcomplan", "Complan Royale Chocolate"),
    (r"\bboost", "Boost Health Drink"),
    (r"\bmilo", "Nestle Milo"),
    # Noodles & Pasta
    (r"\bmagg?i", "Nestle Maggi 2-Minute Noodles"),
    (r"\byippee", "Sunfeast YiPPee Noodles"),
    (r"\btop\s*ramen", "Nissin Top Ramen"),
    (r"\bching['\s]?s", "Chings Secret Instant Noodles"),
    (r"\bwai\s*wai", "Wai Wai Noodles"),
    # Biscuits & Cookies
    (r"\bparle[- ]?g", "Parle-G Original Gluco Biscuits"),
    (r"\bhide[- ]?(?:&|and)[- ]?seek", "Parle Hide & Seek Chocolate Biscuits"),
    (r"\bmonaco", "Parle Monaco Salted Biscuits"),
    (r"\bkrack[- ]?jack", "Parle Krackjack Biscuits"),
    (r"\bgood[- ]?day", "Britannia Good Day Butter Cookies"),
    (r"\bbourbon", "Britannia Bourbon Chocolate Biscuits"),
    (r"\bmarie\s*gold", "Britannia Marie Gold"),
    (r"\b50[- ]?50", "Britannia 50-50 Maska Chaska"),
    (r"\bdark\s*fantasy", "Sunfeast Dark Fantasy Choco Fills"),
    (r"\boreo", "Cadbury Oreo Original Vanilla Biscuits"),
    # Dairy & Spreads
    (r"\bamul\s*(?:butter|pasteurised|salted)?", "Amul Butter"),
    (r"\bamul\s*cheese", "Amul Cheese Slices"),
    (r"\bnutella", "Nutella Hazelnut Spread"),
    (r"\bkissan", "Kissan Mixed Fruit Jam"),
    # Breakfast & Fitness
    (r"\byoga\s*bar", "Yoga Bar Dark Chocolate Oats"),
    (r"\bkellogg['\s]?s\s*corn\s*flakes", "Kelloggs Corn Flakes"),
    (r"\bkellogg['\s]?s\s*chocos", "Kelloggs Chocos"),
    (r"\bquaker\s*oats", "Quaker Rolled Oats India"),
    (r"\bpintola", "Pintola All Natural Peanut Butter"),
    (r"\bmyfitness", "MyFitness Chocolate Peanut Butter"),
    (r"\bsaffola\s*oats", "Saffola Masala Oats"),
    (r"\bsaffola", "Saffola Gold Edible Cooking Oil"),
]


class ProductImageDetector:
    """
    Direct Product Recognition from Uploaded Food Package Images.
    Uses preprocessed OCR + filename metadata + fuzzy FMCG pattern matching
    to identify the exact packaged food product without manual typing.
    """

    def detect_product_from_bytes(self, image_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Takes raw image bytes and optional original filename, runs OCR and pattern matching,
        and returns the detected product name and OCR text preview.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"Failed to read image bytes: {e}")
            raise ValueError("Invalid image file format. Please upload JPEG, PNG, or WEBP.")

        # 1. First check if filename has clear product identifiers
        if filename:
            cleaned_fn = re.sub(r'[-_.]+', ' ', filename).lower()
            detected_from_fn, source = self._match_product_from_text(cleaned_fn)
            if source == "pattern_match":
                logger.info(f"Identified product from filename metadata: {detected_from_fn}")
                return {
                    "detected_product": detected_from_fn,
                    "match_source": "filename_metadata",
                    "text_preview": f"Identified via packaging image: {filename}",
                    "raw_text": cleaned_fn,
                }

        # 2. Preprocess image for OCR clarity
        processed_img = self._preprocess_image(image)

        # 3. Run Tesseract OCR
        raw_text = ""
        if pytesseract is not None:
            try:
                raw_text = pytesseract.image_to_string(processed_img, config='--oem 1 --psm 3')
            except Exception as e:
                logger.warning(f"Tesseract OCR primary run failed: {e}. Trying simple run.")
                try:
                    raw_text = pytesseract.image_to_string(processed_img)
                except Exception as ex:
                    logger.error(f"OCR totally failed: {ex}")

        # 4. Match OCR text against Indian FMCG knowledge base
        detected_name, match_source = self._match_product_from_text(raw_text)

        cleaned_lines = [
            line.strip() for line in raw_text.splitlines() 
            if len(line.strip()) > 3 and not re.match(r'^[\W\d_]+$', line.strip())
        ]
        text_preview = " • ".join(cleaned_lines[:5]) if cleaned_lines else "No text recognized"

        return {
            "detected_product": detected_name,
            "match_source": match_source,
            "text_preview": text_preview,
            "raw_text": raw_text.strip(),
        }

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        max_dim = 1600
        if max(gray.size) > max_dim:
            gray.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        try:
            enhanced = ImageOps.autocontrast(gray, cutoff=2)
            enhancer = ImageEnhance.Sharpness(enhanced)
            return enhancer.enhance(1.5)
        except Exception:
            return gray

    def _match_product_from_text(self, text: str) -> Tuple[str, str]:
        if not text:
            return "Packaged Food Product", "fallback"

        normalized_text = text.lower()

        # 1. Match known patterns
        for pattern, product_canonical_name in KNOWN_PRODUCTS:
            if re.search(pattern, normalized_text, re.IGNORECASE):
                logger.info(f"Identified product: {product_canonical_name} (pattern: {pattern})")
                return product_canonical_name, "pattern_match"

        # 2. Extract most prominent text lines (title / headline)
        lines = [
            l.strip() for l in text.splitlines() 
            if len(l.strip()) >= 4 and not re.match(r'^(?:ingredients|nutrition|mfg|exp|batch|net|wt|mrp|rs|serv|veg).*$', l.strip(), re.IGNORECASE)
        ]

        if lines:
            candidate = " ".join(lines[:2]).strip()
            cleaned = re.sub(r'[^\w\s-]', '', candidate).strip()
            if len(cleaned) >= 4:
                return cleaned.title(), "ocr_headline"

        return "Packaged Food Product", "unrecognized"
