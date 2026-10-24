import pytest
import numpy as np

from app.pipeline.barcode import (
    calculate_gs1_check_digit,
    validate_barcode,
    generate_preprocessing_variants,
    decode_barcode_image,
)


def test_gs1_check_digit_calculation():
    # Known valid EAN-13 barcodes
    # "4006381333931" -> first 12 are "400638133393", check digit is 1
    assert calculate_gs1_check_digit("400638133393") == 1

    # "8901030383748" -> first 12 are "890103038374", check digit is 8
    assert calculate_gs1_check_digit("890103038374") == 8

    # Known valid EAN-8 barcodes
    # "73513537" -> first 7 are "7351353", check digit is 7
    assert calculate_gs1_check_digit("7351353") == 7

    # "96385074" -> first 7 are "9638507", check digit is 4
    assert calculate_gs1_check_digit("9638507") == 4

    # Known valid UPC-A barcodes
    # "036000291452" -> first 11 are "03600029145", check digit is 2
    assert calculate_gs1_check_digit("03600029145") == 2

    # "614141000036" -> first 11 are "61414100003", check digit is 6
    assert calculate_gs1_check_digit("61414100003") == 6


def test_invalid_input_to_check_digit():
    with pytest.raises(ValueError):
        calculate_gs1_check_digit("1234abc")


def test_ean13_validation():
    # Valid EAN-13
    is_valid, fmt = validate_barcode("4006381333931")
    assert is_valid is True
    assert fmt == "EAN-13"

    is_valid, fmt = validate_barcode("8901030383748")
    assert is_valid is True
    assert fmt == "EAN-13"

    # Corrupt check digit for EAN-13
    is_valid, fmt = validate_barcode("4006381333932")
    assert is_valid is False
    assert fmt == "EAN-13"


def test_ean8_validation():
    # Valid EAN-8
    is_valid, fmt = validate_barcode("73513537")
    assert is_valid is True
    assert fmt == "EAN-8"

    # Corrupt check digit for EAN-8
    is_valid, fmt = validate_barcode("73513538")
    assert is_valid is False
    assert fmt == "EAN-8"


def test_upca_validation():
    # Valid UPC-A
    is_valid, fmt = validate_barcode("036000291452")
    assert is_valid is True
    assert fmt == "UPC-A"

    # Corrupt check digit for UPC-A
    is_valid, fmt = validate_barcode("036000291453")
    assert is_valid is False
    assert fmt == "UPC-A"


def test_unsupported_or_malformed_barcodes():
    # Lengths that do not match EAN-13, EAN-8, or UPC-A
    assert validate_barcode("12345")[0] is False
    assert validate_barcode("")[0] is False
    assert validate_barcode(None)[0] is False
    assert validate_barcode("abc1234567890")[0] is False


def test_preprocessing_variants_generation():
    # Create sample image
    img = np.ones((100, 150, 3), dtype=np.uint8) * 128
    variants = generate_preprocessing_variants(img)

    variant_names = [v[0] for v in variants]
    assert "grayscale" in variant_names
    assert "sharpened" in variant_names
    assert "upscale_1.5x" in variant_names
    assert "upscale_2.0x" in variant_names
    assert "otsu_threshold" in variant_names
    assert "adaptive_threshold" in variant_names
    assert "rotate_90" in variant_names
    assert "rotate_180" in variant_names
    assert "rotate_270" in variant_names

    # Check upscale dimensions
    upscale_1_5 = next(v[1] for v in variants if v[0] == "upscale_1.5x")
    assert upscale_1_5.shape[1] == int(150 * 1.5)
    assert upscale_1_5.shape[0] == int(100 * 1.5)


def test_decode_empty_or_blank_image():
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    res = decode_barcode_image(blank)
    assert res is None

