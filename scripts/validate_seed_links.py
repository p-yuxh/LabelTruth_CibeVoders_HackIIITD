#!/usr/bin/env python3
"""
Validates all evidence links in data/lab_reports_seed.json against strict link verification rules.
Ensures zero broken or dead links in production fixtures.
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.link_verifier import validate_evidence_url, load_allowed_domains

SEED_FILES = [
    ROOT_DIR / "data" / "lab_reports_seed.json",
    ROOT_DIR / "backend" / "app" / "config_data" / "lab_reports_seed.json",
]


def main():
    print("=== Validating Lab Evidence Seed Fixtures ===")
    allowed_domains = set(load_allowed_domains())
    print(f"Loaded allowed domains: {allowed_domains}")

    total_records = 0
    errors = []

    for seed_path in SEED_FILES:
        if not seed_path.exists():
            print(f"Skipping non-existent seed file: {seed_path}")
            continue

        print(f"\nChecking: {seed_path}")
        with open(seed_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        for rec in records:
            total_records += 1
            rid = rec.get("record_id", "unknown")
            url = rec.get("original_report_url")
            v_by = rec.get("verified_by")
            v_at = rec.get("verified_at")

            # Check verification fields
            if not v_by or not v_at:
                errors.append(f"[{rid}] Missing verified_by or verified_at.")

            if not url:
                errors.append(f"[{rid}] Missing original_report_url.")
                continue

            # Check allowed domains
            host = urlparse(url).netloc.lower().split(":")[0]
            if host not in allowed_domains:
                errors.append(f"[{rid}] Host '{host}' not in allowed_domains.json: {url}")

            # Check strict evidence URL structure
            is_valid, reason = validate_evidence_url(url)
            if not is_valid:
                errors.append(f"[{rid}] Evidence URL invalid: {reason} ({url})")

            # Check dead status in record
            if rec.get("link_status") in ("dead", "error"):
                errors.append(f"[{rid}] Link marked as dead/error in seed data: {rec.get('error_reason')}")

            print(f"  [OK] [{rid}] {host} -> {rec.get('product')}")

    print("\n-------------------------------------------")
    if errors:
        print(f"FAILED: Found {len(errors)} validation errors:")
        for err in errors:
            print(f"  [X] {err}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {total_records} records across seed files validated successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
