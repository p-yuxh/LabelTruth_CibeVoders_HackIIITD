import logging
from typing import Optional, Tuple, List
import cv2
import numpy as np

from app.schemas import BarcodeResult

logger = logging.getLogger("labeltruth.barcode")

# Safely check pyzbar availability once
_pyzbar_attempted = False
_PYZBAR_AVAILABLE = False
_pyzbar_module = None

def _init_pyzbar():
    global _PYZBAR_AVAILABLE, _pyzbar_module, _pyzbar_attempted
    if _pyzbar_attempted:
        return _PYZBAR_AVAILABLE
    _pyzbar_attempted = True
    try:
        from pyzbar import pyzbar as pz
        _pyzbar_module = pz
        _PYZBAR_AVAILABLE = True
    except (ImportError, FileNotFoundError, OSError) as e:
        _PYZBAR_AVAILABLE = False
        logger.debug(f"pyzbar unavailable: {e}. Using cv2.barcode.BarcodeDetector.")
    return _PYZBAR_AVAILABLE


def calculate_gs1_check_digit(digits_str: str) -> int:
    """
    Calculate GS1 standard check digit for a string of numeric digits (excluding the check digit).
    GS1 algorithm: Moving right-to-left, alternate weights 3 and 1, sum the products,
    and find (10 - (sum % 10)) % 10.
    """
    if not digits_str.isdigit():
        raise ValueError(f"Input string must contain only digits, got '{digits_str}'")
    digits = [int(c) for c in digits_str]
    # Alternating weights starting with 3 on the rightmost digit
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - (total % 10)) % 10


def validate_barcode(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a barcode string against GS1 standards for EAN-13, EAN-8, and UPC-A.
    Returns (is_valid, detected_format).
    """
    if not code or not isinstance(code, str):
        return False, None
    clean = code.strip()
    if not clean.isdigit():
        return False, None

    length = len(clean)

    if length == 13:
        # EAN-13: 12 data digits + 1 check digit
        expected = calculate_gs1_check_digit(clean[:12])
        if int(clean[12]) == expected:
            return True, "EAN-13"
        return False, "EAN-13"

    elif length == 12:
        # UPC-A: 11 data digits + 1 check digit
        expected = calculate_gs1_check_digit(clean[:11])
        if int(clean[11]) == expected:
            return True, "UPC-A"
        return False, "UPC-A"

    elif length == 8:
        # EAN-8: 7 data digits + 1 check digit
        expected = calculate_gs1_check_digit(clean[:7])
        if int(clean[7]) == expected:
            return True, "EAN-8"
        return False, "EAN-8"

    return False, None


_cached_detector: Optional[cv2.barcode.BarcodeDetector] = None

def _get_opencv_detector() -> Optional[cv2.barcode.BarcodeDetector]:
    """Instantiate or reuse OpenCV BarcodeDetector."""
    global _cached_detector
    if _cached_detector is None:
        try:
            _cached_detector = cv2.barcode.BarcodeDetector()
        except Exception as e:
            logger.warning(f"Could not instantiate cv2.barcode.BarcodeDetector: {e}")
    return _cached_detector


def _decode_with_pyzbar(image: np.ndarray) -> List[Tuple[str, str]]:
    """Decode barcodes using pyzbar if available."""
    if not _init_pyzbar() or _pyzbar_module is None:
        return []
    results = []
    try:
        decoded_objs = _pyzbar_module.decode(image)
        for obj in decoded_objs:
            code = obj.data.decode("utf-8", errors="ignore").strip()
            fmt = obj.type
            if code:
                results.append((code, fmt))
    except Exception as e:
        logger.debug(f"pyzbar decode exception: {e}")
    return results


def _decode_with_opencv(image: np.ndarray, detector: cv2.barcode.BarcodeDetector) -> List[Tuple[str, str]]:
    """Decode barcodes using OpenCV BarcodeDetector."""
    results = []
    try:
        retval, decoded_info, decoded_type, points = detector.detectAndDecodeMulti(image)
        if retval and decoded_info:
            for i, info in enumerate(decoded_info):
                code = info.strip()
                if code:
                    fmt = decoded_type[i] if decoded_type is not None and i < len(decoded_type) else "BARCODE"
                    results.append((code, str(fmt)))
    except Exception as e:
        logger.debug(f"OpenCV BarcodeDetector exception: {e}")
    return results


def generate_preprocessing_variants(image_bgr: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """
    Generate image transformation pipeline before giving up:
    grayscale, rotation (90, 180, 270), sharpening, upscale, adaptive/otsu thresholding.
    """
    variants: List[Tuple[str, np.ndarray]] = []

    # 1. Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if len(image_bgr.shape) == 3 else image_bgr
    variants.append(("grayscale", gray))

    # 2. Sharpening filter
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(gray, -1, sharpen_kernel)
    variants.append(("sharpened", sharpened))

    # 3. Upscale (1.5x and 2.0x)
    h, w = gray.shape[:2]
    if max(h, w) < 1500:
        upscaled_1_5 = cv2.resize(gray, (int(w * 1.5), int(h * 1.5)), interpolation=cv2.INTER_CUBIC)
        variants.append(("upscale_1.5x", upscaled_1_5))
        upscaled_2 = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        variants.append(("upscale_2.0x", upscaled_2))

    # 4. Otsu thresholding
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu_threshold", otsu))

    # 5. Adaptive thresholding
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    variants.append(("adaptive_threshold", adaptive))

    # 5. Rotations: 90, 180, 270 degrees
    variants.append(("rotate_90", cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)))
    variants.append(("rotate_180", cv2.rotate(image_bgr, cv2.ROTATE_180)))
    variants.append(("rotate_270", cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)))

    return variants


def decode_barcode_image(image_bgr: np.ndarray) -> Optional[BarcodeResult]:
    """
    Attempt barcode decoding on an image using pyzbar and OpenCV BarcodeDetector,
    exhausting preprocessing transformations before giving up.
    Returns BarcodeResult only if check digit is valid.
    """
    if image_bgr is None or image_bgr.size == 0:
        return None

    cv_detector = _get_opencv_detector()

    def try_decode(img: np.ndarray) -> Optional[BarcodeResult]:
        candidates = _decode_with_pyzbar(img)
        if not candidates and cv_detector is not None:
            candidates = _decode_with_opencv(img, cv_detector)

        for raw_code, raw_fmt in candidates:
            digits_only = "".join(ch for ch in raw_code if ch.isdigit())
            valid, fmt = validate_barcode(digits_only)
            if valid and fmt:
                return BarcodeResult(
                    code=digits_only,
                    format=fmt,
                    valid_check_digit=True,
                )
        return None

    # Step A: Try directly on the original image
    result = try_decode(image_bgr)
    if result:
        return result

    # Step B: Exhaust preprocessing variants (grayscale, sharpen, upscale, threshold, rotation)
    variants = generate_preprocessing_variants(image_bgr)
    for variant_name, transformed_img in variants:
        result = try_decode(transformed_img)
        if result:
            logger.info(f"Barcode decoded successfully after preprocessing: '{variant_name}'")
            return result

    return None


def decode_barcode_bytes(image_bytes: bytes) -> Optional[BarcodeResult]:
    """Convert raw image bytes to BGR numpy array and run decode_barcode_image."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None
    return decode_barcode_image(img_bgr)
