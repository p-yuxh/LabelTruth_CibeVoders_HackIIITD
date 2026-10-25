import json
import logging
import math
import os
import re
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

from app.services.link_verifier import (
    load_allowed_domains,
    load_source_directory,
    normalize_and_sanitize_url,
    validate_evidence_url,
    extract_report_date,
    link_verifier,
    LinkVerifier,
    DiagnosticsRegistry,
)

logger = logging.getLogger("labeltruth.evidence")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config_data"
ROOT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
ROOT_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config"

DISABLED_SOURCES = {
    "consumer_voice",
    "consumer-voice",
    "ministry_of_consumer_affairs",
    "ministry of consumer affairs",
    "fssai_lab",
    "fssai as a lab source",
    "youtube",
    "social_media",
    "social",
}


class IndependentEvidenceService:
    """
    Independent Evidence Service for LabelTruth.
    Limited strictly to two independent lab evidence sources:
      1. Trustified (www.trustified.in)
      2. Unbox Health (www.unboxhealth.in, unboxhealth-production.s3.amazonaws.com)
    All other lab evidence sources are disabled.
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        data_dir: Optional[Path] = None,
        reference_date: Optional[date] = None,
    ):
        self.config_dir = config_dir or CONFIG_DIR
        self.data_dir = data_dir or (ROOT_DATA_DIR if ROOT_DATA_DIR.exists() else self.config_dir)
        self.reference_date = reference_date

        self.allowed_domains = load_allowed_domains()
        self.source_directory = load_source_directory()
        self.link_verifier = link_verifier
        self.diagnostics = DiagnosticsRegistry()

        self.sources_config = self._load_json(self.config_dir / "evidence_sources.json", default={})
        self.age_config = self._load_json(self.config_dir / "report_age.json", default={})
        self.lab_seeds = self._load_json_list([
            self.data_dir / "lab_reports_seed.json",
            self.config_dir / "lab_reports_seed.json",
        ])

        # Pre-seed cache for verified seed items with verified_by / verified_at
        now_iso = datetime.now(timezone.utc).isoformat()
        for seed in self.lab_seeds:
            url = seed.get("original_report_url")
            if url and seed.get("verified_by") and seed.get("verified_at"):
                clean_url, _ = normalize_and_sanitize_url(url, self.allowed_domains)
                if clean_url:
                    self.link_verifier.cache[clean_url] = {
                        "link_status": "reachable",
                        "http_status": 200,
                        "final_url": clean_url,
                        "checked_at": now_iso,
                        "last_verified": now_iso[:10],
                        "error_reason": None,
                        "archived_url": None,
                        "is_restricted": False,
                    }

        # Config switches
        thresholds = self.age_config.get("thresholds_years", {})
        self.recent_max_years = float(thresholds.get("recent_max_years", 2.0))
        self.ageing_max_years = float(thresholds.get("ageing_max_years", 5.0))

        verdict_rules = self.age_config.get("verdict_rules", {})
        self.allow_old_for_verdict = bool(verdict_rules.get("allow_old_for_verdict", False))
        self.tolerance_pct = float(verdict_rules.get("tolerance_pct", 15.0))

        self.standard_disclaimer = self.age_config.get(
            "standard_disclaimer",
            "Reported evidence for the tested batch, not proof of wrongdoing."
        )
        self.batch_note = self.age_config.get(
            "batch_note",
            "Results apply to the batch tested; the product may have changed since."
        )

    def _load_json(self, file_path: Path, default: Any) -> Any:
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config file {file_path}: {e}")
        return default

    def _load_json_list(self, candidate_paths: List[Path]) -> List[Dict[str, Any]]:
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return data
                except Exception as e:
                    logger.warning(f"Error loading {p}: {e}")
        return []

    # -------------------------------------------------------------------------
    # 1. Report Age Computation
    # -------------------------------------------------------------------------
    def compute_report_age(
        self,
        test_date_str: Optional[str],
        publication_date_str: Optional[str] = None,
        ref_date: Optional[date] = None,
    ) -> Tuple[Optional[float], str, str]:
        """
        Computes the age of a report in years relative to current date (or reference date).
        Thresholds:
        - <= 2 years: "recent"
        - > 2 and <= 5 years: "ageing"
        - > 5 years: "old"
        - no date: "unknown" (treated as Old)
        Returns: (age_years, age_status, age_display_text)
        """
        target_str = test_date_str or publication_date_str
        if not target_str or not isinstance(target_str, str) or not target_str.strip():
            return None, "unknown", "Date unknown"

        parsed_date = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m", "%Y"):
            try:
                parsed_date = datetime.strptime(target_str.strip(), fmt).date()
                break
            except ValueError:
                continue

        if not parsed_date:
            extracted = extract_report_date(target_str)
            if extracted:
                try:
                    parsed_date = datetime.strptime(extracted, "%Y-%m-%d").date()
                except ValueError:
                    pass

        if not parsed_date:
            return None, "unknown", "Date unknown"

        effective_ref = ref_date or self.reference_date or datetime.now(timezone.utc).date()
        days_diff = (effective_ref - parsed_date).days
        if days_diff < 0:
            age_years = 0.0
        else:
            age_years = round(days_diff / 365.25, 2)

        if age_years <= self.recent_max_years:
            age_status = "recent"
        elif age_years <= self.ageing_max_years:
            age_status = "ageing"
        else:
            age_status = "old"

        date_label = "Tested" if test_date_str else "Published"
        if age_years < 1.0:
            months = max(1, round(age_years * 12))
            display_text = f"{date_label}: {parsed_date.isoformat()} ({months} mo ago)"
        else:
            years_int = int(round(age_years)) if abs(age_years - round(age_years)) < 0.1 else f"{age_years:.1f}"
            display_text = f"{date_label}: {parsed_date.isoformat()} ({years_int} yr{'s' if str(years_int) != '1' else ''} ago)"

        return age_years, age_status, display_text

    # -------------------------------------------------------------------------
    # 2. Acceptance Rules Evaluation
    # -------------------------------------------------------------------------
    def evaluate_acceptance_rules(
        self,
        record: Dict[str, Any],
        query: str = "",
        product_name: str = "",
        brand: str = "",
        retrieved_urls_map: Optional[Dict[int, str]] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Evaluates strict acceptance rules for Section 1:
        1. Source must be Trustified or Unbox Health. Disabled sources are rejected.
        2. Same brand, product, and variant as viewed.
        3. Same metric as the claim/product checked.
        4. Original report is accessible (reachable, verified URL), not a news summary.
        5. Lab is named, and accreditation is stated.
        6. URLs must match strict allowed host/path patterns.
        """
        source_name = (record.get("source_name") or "").lower()
        source_type = (record.get("source_type") or "").lower()
        original_url = (record.get("original_report_url") or "").strip()

        # Check disabled sources
        clean_src = re.sub(r'[^a-z0-9]', '', source_name)
        clean_type = re.sub(r'[^a-z0-9]', '', source_type)
        for disabled in DISABLED_SOURCES:
            clean_dis = re.sub(r'[^a-z0-9]', '', disabled)
            if clean_dis in clean_src or clean_dis in clean_type or disabled in source_name or disabled in source_type:
                return "reported_not_verified", "Source disabled: Only Trustified and Unbox Health are enabled for independent lab evidence."

        # Rule 0: Seed verification integrity check
        if record.get("record_id", "").startswith("lab_") and not record.get("is_live_discovery"):
            v_by = record.get("verified_by")
            v_at = record.get("verified_at")
            if not v_by or not v_at:
                return "reported_not_verified", "Seed entry rejected: missing mandatory verified_by or verified_at."

        match = record.get("match", {})
        same_product = match.get("same_product", True)
        same_metric = match.get("same_metric", True)

        p_brand = (record.get("brand") or "").lower()
        p_name = (record.get("product") or "").lower()
        target_brand = brand.lower()
        target_name = (product_name or query).lower()

        # Rule 1: Product & Brand mismatch
        if not same_product:
            return "reported_not_verified", "Product and variant mismatch (Rule 1): The report tests a different product or category."

        if target_brand and p_brand:
            p_tokens = set(re.findall(r'\b\w{3,}\b', p_brand)) - {"the", "and", "ltd", "pvt", "limited", "company", "india"}
            t_tokens = set(re.findall(r'\b\w{3,}\b', target_brand)) - {"the", "and", "ltd", "pvt", "limited", "company", "india"}
            if p_tokens and t_tokens and not (p_tokens & t_tokens):
                return "reported_not_verified", f"Product and brand mismatch (Rule 1): Laboratory analysis tested {record.get('brand')}, but viewed product is {brand}."

        # Rule 2: Metric mismatch
        if not same_metric:
            return "reported_not_verified", "Metric mismatch (Rule 2): Tested analytical parameter does not match the product or claim being audited."

        if "butter" in target_name and ("milk" in p_name or "raw milk" in str(record.get("parameter", "")).lower()):
            if "butter" not in p_name:
                return "reported_not_verified", "Product mismatch (Rule 1 & 2): Raw fluid milk surveillance cannot evaluate pasteurised table butter."

        # Rule 3: Link Provenance & Server-side Verification
        if not original_url:
            if "trustified" in source_name or "trustified" in source_type:
                return "reported_not_verified", "Trustified report lacks original laboratory report attachment (Rule 3)."
            return "reported_not_verified", "Original laboratory report not accessible (Rule 3); secondary citation only."

        # Link Provenance: Check if numeric source_id is required
        source_id = record.get("source_id")
        if retrieved_urls_map is not None:
            if source_id is None or source_id not in retrieved_urls_map:
                self.diagnostics.log_link_outcome(source_name, source_id, original_url, "dead", "link not traceable")
                return "reported_not_verified", "link not traceable (Rule 3): source_id is missing or unknown."
            expected_url = retrieved_urls_map[source_id]
            if original_url != expected_url:
                self.diagnostics.log_link_outcome(source_name, source_id, original_url, "dead", "link not traceable")
                return "reported_not_verified", "link not traceable (Rule 3): URL in output does not match retrieved result."

        # URL Sanitization and Allowed Domains Check
        clean_url, url_err = normalize_and_sanitize_url(original_url, self.allowed_domains)
        if url_err:
            self.diagnostics.log_link_outcome(source_name, source_id, original_url, "dead", url_err)
            return "reported_not_verified", f"Original report URL invalid (Rule 3): {url_err}."

        # Strict evidence URL structure check
        is_evidence_valid, evidence_err = validate_evidence_url(clean_url)
        if not is_evidence_valid:
            self.diagnostics.log_link_outcome(source_name, source_id, clean_url, "dead", evidence_err)
            return "reported_not_verified", f"Evidence link rejected (Rule 3): {evidence_err}."

        record["original_report_url"] = clean_url
        record["final_url"] = clean_url

        # Check Link Verification status
        if "link_status" not in record or not record.get("checked_at"):
            v_res = self.link_verifier.verify_link(
                url=clean_url,
                product_name=product_name or record.get("product", ""),
                brand=brand or record.get("brand", ""),
                report_title=record.get("parameter", ""),
                source_id=source_id,
                source_name=record.get("source_name", "Lab Report"),
                strict_evidence_rules=True,
            )
            record["link_status"] = v_res["link_status"]
            record["http_status"] = v_res.get("http_status")
            record["final_url"] = v_res.get("final_url") or clean_url
            record["checked_at"] = v_res.get("checked_at")
            record["last_verified"] = v_res.get("last_verified") or (record.get("checked_at") or "")[:10]
            record["proof_snapshot"] = v_res.get("proof_snapshot")
            record["archived_url"] = v_res.get("archived_url")
            record["is_restricted"] = v_res.get("is_restricted", False)

        link_status = record.get("link_status", "reachable")
        checked_date = (record.get("checked_at") or datetime.now(timezone.utc).isoformat())[:10]

        if link_status in ("dead", "error"):
            record["original_report_url"] = None
            err_reason = record.get("error_reason") or "Link unreachable"
            return "reported_not_verified", f"Link unavailable (checked {checked_date}): {err_reason}."

        if link_status == "restricted":
            record["is_restricted"] = True
            return "reported_not_verified", "Detailed results may require a subscription or login."

        # Rule 4: Lab named and accreditation stated
        lab_name = (record.get("lab_name") or "").strip().lower()
        if not lab_name or lab_name in ["not stated", "unnamed testing facility", "unknown", "undisclosed independent laboratory"]:
            return "reported_not_verified", "Analytical laboratory is not named or identified (Rule 4)."

        if "accreditation_checked" not in record:
            record["accreditation_checked"] = False

        if not record.get("accreditation_checked") or record.get("accreditation_no") in ("not stated", "none", "", None):
            record["non_accredited_note"] = "non-accredited test"

        # Flags & notes
        if record.get("labs_disagree"):
            record["disagree_note"] = "labs disagree"
        if record.get("page_vs_pdf_mismatch"):
            record["mismatch_note"] = "page vs PDF mismatch"
        if record.get("batch_mapping_not_confirmed"):
            record["batch_mapping_note"] = "batch mapping not confirmed"

        # Rule 5: Normalize method/sample/batch strings
        if not record.get("method"):
            record["method"] = "not stated"
        if record.get("sample_count") is None or record.get("sample_count") == "":
            record["sample_count"] = "not stated"
        if not record.get("batch"):
            record["batch"] = "not stated"

        # Rule 6: Normalize brand response & regulator action strings
        if not record.get("brand_response"):
            record["brand_response"] = "None on record."
        if not record.get("regulator_action"):
            record["regulator_action"] = "None on record."

        # Rule 7: Standard disclaimer
        record["disclaimer"] = self.standard_disclaimer

        conf = float(record.get("confidence", 1.0))
        if conf < 0.6 or record.get("needs_review") is True:
            return "reported_not_verified", "Low extraction confidence or incomplete report extraction; requires manual review."

        return "accepted", None

    # -------------------------------------------------------------------------
    # 3. Select Candidate Reports
    # -------------------------------------------------------------------------
    def select_best_report_candidate(
        self,
        candidates: List[Dict[str, Any]],
        product_name: str,
        brand: str,
        metric: str,
        retrieved_urls_map: Optional[Dict[int, str]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        accepted_candidates = []
        rejected_log = []

        brand_clean = (brand or "").lower().strip()
        prod_clean = (product_name or "").lower().strip()
        metric_clean = (metric or "").lower().strip()

        tier_weights = {"A": 1, "B": 2, "C": 3, "D": 4}

        for idx, item in enumerate(candidates[:10], start=1):
            title = (item.get("title") or "").lower()
            snippet = (item.get("snippet") or item.get("text") or item.get("body") or "").lower()
            combined_text = f"{title} {snippet}"
            item_url = (item.get("url") or item.get("original_report_url") or "").strip()
            source_id = item.get("source_id", idx)

            if retrieved_urls_map is not None:
                if source_id not in retrieved_urls_map or retrieved_urls_map[source_id] != item_url:
                    rejected_log.append({
                        "source_id": source_id,
                        "url": item_url,
                        "reason": "link not traceable: URL is not in retrieved results set",
                    })
                    continue

            brand_in_text = brand_clean in combined_text if brand_clean else True
            prod_tokens = [w for w in re.findall(r'\b\w{3,}\b', prod_clean) if w not in ("with", "pack", "food")]
            prod_in_text = any(t in combined_text for t in prod_tokens) if prod_tokens else True

            if not (brand_in_text and prod_in_text):
                rejected_log.append({
                    "source_id": source_id,
                    "url": item_url,
                    "reason": f"Brand '{brand}' or product '{product_name}' not found in candidate content",
                })
                continue

            if metric_clean and metric_clean not in combined_text:
                synonyms = {
                    "sugar": ["sugar", "sugars", "sweetener", "sucrose", "glucose"],
                    "sodium": ["sodium", "salt", "nacl"],
                    "fat": ["fat", "palmolein", "palm oil", "oil", "lipid", "saturated fat"],
                    "protein": ["protein", "whey", "nitrogen"],
                }
                found_syn = False
                for syn_k, syn_list in synonyms.items():
                    if syn_k in metric_clean or any(s in metric_clean for s in syn_list):
                        if any(s in combined_text for s in syn_list):
                            found_syn = True
                            break
                if not found_syn:
                    rejected_log.append({
                        "source_id": source_id,
                        "url": item_url,
                        "reason": f"Target metric '{metric}' does not appear in candidate text",
                    })
                    continue

            is_news = item.get("is_news_summary", False) or any(
                n in combined_text for n in ("news summary", "breaking news", "reported by times of india", "ndtv news")
            )
            has_original_report = bool(item.get("original_report_url") or item_url.endswith(".pdf") or "report" in title)
            if is_news and not has_original_report:
                rejected_log.append({
                    "source_id": source_id,
                    "url": item_url,
                    "reason": "Secondary news article without original report link attached",
                })
                continue

            extracted_date = extract_report_date(combined_text) or item.get("publication_date") or item.get("test_date")
            if not extracted_date:
                rejected_log.append({
                    "source_id": source_id,
                    "url": item_url,
                    "reason": "Date could not be extracted from candidate report",
                })
                continue

            age_years, age_status, age_display = self.compute_report_age(extracted_date)
            tier = str(item.get("tier") or "C").upper()
            tier_rank = tier_weights.get(tier, 3)

            relevance_strength = 0
            if brand_clean and brand_clean in title:
                relevance_strength += 2
            if any(t in title for t in prod_tokens):
                relevance_strength += 2
            if metric_clean and metric_clean in title:
                relevance_strength += 2

            cand_entry = dict(item)
            cand_entry["source_id"] = source_id
            cand_entry["extracted_date"] = extracted_date
            cand_entry["age_years"] = age_years if age_years is not None else 99.0
            cand_entry["age_status"] = age_status
            cand_entry["age_display"] = age_display
            cand_entry["tier"] = tier
            cand_entry["tier_rank"] = tier_rank
            cand_entry["relevance_strength"] = relevance_strength
            accepted_candidates.append(cand_entry)

        if not accepted_candidates:
            logger.info(f"NO_MATCH: None of the {len(candidates)} candidates qualified for '{product_name}' - '{metric}'.")
            return None, rejected_log

        accepted_candidates.sort(key=lambda x: (x["tier_rank"], x["age_years"], -x["relevance_strength"]))
        best = accepted_candidates[0]
        return best, rejected_log

    # -------------------------------------------------------------------------
    # 4. Category Browse Link Mapping
    # -------------------------------------------------------------------------
    def get_category_browse_link(
        self,
        category: str,
        product_name: str = "",
        query: str = ""
    ) -> Optional[Dict[str, Any]]:
        cat_clean = (category or "").strip().lower()
        prod_clean = f"{(product_name or '').lower()} {(query or '').lower()}"
        cat_dict = self.source_directory.get("categories", {})

        if cat_clean and cat_clean in cat_dict:
            entry = cat_dict[cat_clean]
            label = f"Browse Consumer Voice {entry.get('category_label', cat_clean)} reviews (not evidence for this product)"
            return {
                "url": entry.get("url"),
                "text": label,
                "verified_at": entry.get("verified_at"),
                "verified_by": entry.get("verified_by"),
            }

        if cat_clean:
            for key, entry in cat_dict.items():
                if key in cat_clean or cat_clean in key:
                    label = f"Browse Consumer Voice {entry.get('category_label', key)} reviews (not evidence for this product)"
                    return {
                        "url": entry.get("url"),
                        "text": label,
                        "verified_at": entry.get("verified_at"),
                        "verified_by": entry.get("verified_by"),
                    }

        for key in sorted(cat_dict.keys(), key=len, reverse=True):
            if re.search(rf'\b{re.escape(key)}\b', prod_clean):
                entry = cat_dict[key]
                label = f"Browse Consumer Voice {entry.get('category_label', key)} reviews (not evidence for this product)"
                return {
                    "url": entry.get("url"),
                    "text": label,
                    "verified_at": entry.get("verified_at"),
                    "verified_by": entry.get("verified_by"),
                }

        return None

    # -------------------------------------------------------------------------
    # 5. Match Records to Current Product
    # -------------------------------------------------------------------------
    def get_evidence_for_product(
        self,
        query: str,
        product_name: str,
        brand: str,
        category: str = "",
        claims: Optional[List[Dict[str, Any]]] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        ref_date: Optional[date] = None,
        retrieved_urls_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves Independent Lab evidence strictly from Trustified and Unbox Health.
        If neither has an accepted record, returns empty list with exact empty-state text.
        """
        q_clean = (query or "").lower().strip()
        p_clean = (product_name or "").lower().strip()
        b_clean = (brand or "").lower().strip()
        combined_text = f"{q_clean} {p_clean} {b_clean}"

        effective_date = ref_date or self.reference_date or datetime.now(timezone.utc).date()
        date_str_formatted = effective_date.strftime("%d %b %Y")

        def has_word(pattern: str, text: str) -> bool:
            return bool(re.search(pattern, text, re.IGNORECASE))

        def is_match(item_dict: Dict[str, Any]) -> bool:
            p_seed = (item_dict.get("product") or "").lower()
            b_seed = (item_dict.get("brand") or "").lower()
            k_seed = (item_dict.get("product_key") or "").lower()
            c_seed = (item_dict.get("category") or "").lower()
            combined_seed = f"{p_seed} {b_seed} {k_seed} {c_seed}"

            product_patterns = [
                (r'\b(ghee|cow\s+ghee|ashirvaad|svasti)\b', r'\b(ghee|cow\s+ghee|ashirvaad|svasti)\b'),
                (r'\b(honey|patanjali)\b', r'\b(honey|patanjali)\b'),
                (r'\b(whey|protein|nakpro|isolate)\b', r'\b(whey|protein|nakpro|isolate)\b'),
                (r'\bbournvita\b', r'\bbournvita\b'),
                (r'\bmaggi\b', r'\bmaggi\b'),
                (r'\b(lays?|lay\'s)\b', r'\b(lays?|lay\'s)\b'),
                (r'\b(butter|amul\s+butter)\b', r'\b(butter|amul\s+butter)\b'),
            ]

            for q_pat, s_pat in product_patterns:
                if has_word(q_pat, combined_text) and has_word(s_pat, combined_seed):
                    return True

            p_tokens = [w for w in re.findall(r'\b\w{4,}\b', p_seed) if w not in {"with", "from", "pack", "india", "flavor", "flavour"}]
            if p_tokens and all(has_word(rf'\b{re.escape(w)}\b', combined_text) for w in p_tokens):
                return True

            return False

        accepted_lab: List[Dict[str, Any]] = []
        unverified_lab: List[Dict[str, Any]] = []

        for seed in self.lab_seeds:
            item = dict(seed)

            # Strict filtering: Exclude disabled sources completely
            src_name = (item.get("source_name") or "").lower()
            src_type = (item.get("source_type") or "").lower()
            if any(disabled in src_name or disabled in src_type for disabled in DISABLED_SOURCES):
                continue

            if not is_match(item):
                continue

            # Compute age dynamically
            age_years, age_status, age_display = self.compute_report_age(
                test_date_str=item.get("test_date"),
                publication_date_str=item.get("publication_date"),
                ref_date=ref_date,
            )
            item["age_years"] = age_years
            item["age_status"] = age_status
            item["age_display"] = age_display
            item["batch_note"] = self.batch_note

            # Compute gap percentage if label and lab values are valid numbers
            l_val = item.get("label_value")
            lab_val = item.get("lab_value")
            if l_val is not None and lab_val is not None:
                try:
                    l_num = float(l_val)
                    lab_num = float(lab_val)
                    if l_num > 0:
                        item["lab_gap_pct"] = round(((lab_num - l_num) / l_num) * 100.0, 2)
                    elif l_num == 0 and lab_num == 0:
                        item["lab_gap_pct"] = 0.0
                    else:
                        item["lab_gap_pct"] = None
                except (ValueError, TypeError):
                    item["lab_gap_pct"] = None

            # Evaluate acceptance rules with URL verification and provenance
            status, reason = self.evaluate_acceptance_rules(
                item,
                query=query,
                product_name=product_name,
                brand=brand,
                retrieved_urls_map=retrieved_urls_map,
            )
            item["status"] = status
            item["not_verified_reason"] = reason

            if status == "accepted":
                accepted_lab.append(item)
            else:
                unverified_lab.append(item)

        # Log search query
        try:
            log_path = self.data_dir / "lab_search_log.json"
            logs = []
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as lf:
                        logs = json.load(lf)
                        if not isinstance(logs, list):
                            logs = []
                except Exception:
                    logs = []
            logs.append({
                "query": query,
                "product_name": product_name,
                "brand": brand,
                "category": category,
                "searched_hosts": [
                    "www.trustified.in",
                    "www.unboxhealth.in",
                    "unboxhealth-production.s3.amazonaws.com"
                ],
                "searched_at": date_str_formatted,
                "accepted_count": len(accepted_lab),
                "unverified_count": len(unverified_lab),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            with open(log_path, "w", encoding="utf-8") as lf:
                json.dump(logs[-500:], lf, indent=2)
        except Exception as e:
            logger.debug(f"Could not write lab_search_log: {e}")

        # Exact empty-state message required by Section 1:
        empty_state_text = (
            f"No lab report found for this product on Trustified or Unbox Health (searched {date_str_formatted}). "
            f"This does not mean the product is safe or unsafe."
        )

        total_checked = len(accepted_lab) + len(unverified_lab)
        coverage_status = "FOUND" if accepted_lab else "SEARCHED_NONE_FOUND"
        coverage_badge_text = f"FOUND ({len(accepted_lab)} report{'s' if len(accepted_lab) > 1 else ''})" if accepted_lab else "SEARCHED_NONE_FOUND"

        browse_info = self.get_category_browse_link(category, product_name=product_name, query=query)
        category_browse_url = browse_info["url"] if browse_info else None
        category_browse_text = browse_info["text"] if browse_info else None

        return {
            "section_1": {
                "heading": "Independent lab evidence (Trustified, Unbox Health)",
                "accepted": accepted_lab,
                "reported_not_verified": unverified_lab,
                "empty_state_text": empty_state_text,
                "coverage_badge": {
                    "status": coverage_status,
                    "badge_text": coverage_badge_text,
                    "message": empty_state_text if not accepted_lab else f"Found {len(accepted_lab)} verified report(s)",
                },
                "summary_view": f"Lab evidence available for {len(accepted_lab)} of {max(1, total_checked)} products",
                "category_browse_url": category_browse_url,
                "category_browse_text": category_browse_text,
            }
        }

    # -------------------------------------------------------------------------
    # 6. Claim Verdict Updating with Section 1 Evidence
    # -------------------------------------------------------------------------
    def apply_evidence_to_claim_verdicts(
        self,
        claims: List[Dict[str, Any]],
        evidence: Dict[str, Any],
        allow_old_for_verdict: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Informs claim verdicts strictly using accepted Section 1 evidence:
        - Material lab disagreements: When two labs disagree materially (e.g. fat 2.21 vs 3.86),
          withhold CONTRADICTED, set NO EVIDENCE with reason 'labs disagree', showing both values.
        - Non-accredited tests: cannot set CONTRADICTED; label 'non-accredited test'.
        - Page vs PDF mismatch: PDF values win.
        - Informational values: Trustified overall Testing Status, Trustified NMR interpretation text,
          and Unbox letter rating/score NEVER set a claim verdict.
        - Allowed verdicts strictly remain: VERIFIED, MISLEADING, CONTRADICTED, NO EVIDENCE.
        - Personalised Rating and allergy checks are NEVER modified.
        """
        allow_old = self.allow_old_for_verdict if allow_old_for_verdict is None else allow_old_for_verdict
        accepted_reports = evidence.get("section_1", {}).get("accepted", [])

        updated_claims = []
        for claim in claims:
            c = dict(claim)
            c_text = (c.get("claim") or c.get("text") or "").lower()

            matching_report = None
            for rep in accepted_reports:
                if not rep.get("original_report_url") or rep.get("link_status") in ("dead", "error", "restricted"):
                    continue

                param = (rep.get("parameter") or "").lower()
                if any(w in c_text for w in ["sugar", "sweet", "glucose"]) and any(w in param for w in ["sugar", "sweetener"]):
                    matching_report = rep
                    break
                elif any(w in c_text for w in ["salt", "sodium", "bp"]) and any(w in param for w in ["sodium", "salt"]):
                    matching_report = rep
                    break
                elif any(w in c_text for w in ["fat", "trans fat", "palm oil", "palmolein"]) and any(w in param for w in ["fat", "oil", "palmolein", "lipid"]):
                    matching_report = rep
                    break
                elif any(w in c_text for w in ["protein", "muscle", "strength"]) and any(w in param for w in ["protein", "amino"]):
                    matching_report = rep
                    break
                elif any(w in c_text for w in ["health drink", "energy", "active brain"]) and "health drink" in param:
                    matching_report = rep
                    break
                elif any(w in c_text for w in ["pure", "purity", "fresh"]) and any(w in param for w in ["fat", "moisture", "standard", "purity"]):
                    matching_report = rep
                    break

            if matching_report:
                gap = matching_report.get("lab_gap_pct")
                age_status = matching_report.get("age_status", "unknown")
                source_name = matching_report.get("source_name", "Accredited Lab")
                tier = matching_report.get("tier", "C")
                rep_url = matching_report.get("final_url") or matching_report.get("original_report_url")
                report_type = matching_report.get("report_type", "")
                is_accredited = bool(matching_report.get("accreditation_checked", False))
                labs_disagree = bool(matching_report.get("labs_disagree", False))
                page_pdf_mismatch = bool(matching_report.get("page_vs_pdf_mismatch", False))

                # Handle page vs PDF mismatch: PDF values win
                if page_pdf_mismatch and "pdf_lab_value" in matching_report and matching_report["pdf_lab_value"] is not None:
                    gap = matching_report.get("pdf_lab_gap_pct", gap)

                # Attach evidence reference
                c["independent_evidence_ref"] = {
                    "record_id": matching_report.get("record_id"),
                    "source_name": source_name,
                    "tier": tier,
                    "age_status": age_status,
                    "lab_gap_pct": gap,
                    "original_report_url": rep_url,
                    "labs_disagree": labs_disagree,
                    "accreditation_checked": is_accredited,
                }

                # Rule A: Informational-only reports never set a verdict
                if report_type == "nmr" or matching_report.get("is_letter_rating") or matching_report.get("parameter") in ("Unbox Rating", "Overall Status", "Testing Status"):
                    # Leave verdict unchanged or NO EVIDENCE
                    if c.get("audit_verdict") not in ["VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"]:
                        c["audit_verdict"] = "NO EVIDENCE"
                    c["reason"] = f"Reported by {source_name}: Informational finding ({matching_report.get('interpretation') or matching_report.get('testing_status') or 'test interpretation'}); does not alter statutory claim verdict."

                # Rule B: Material lab disagreements -> withhold CONTRADICTED, set NO EVIDENCE with reason 'labs disagree'
                elif labs_disagree:
                    c["audit_verdict"] = "NO EVIDENCE"
                    disagree_summary = matching_report.get("disagreement_summary") or "labs disagree on measured values"
                    c["reason"] = f"No evidence: labs disagree ({disagree_summary}). Both values displayed."

                # Rule C: Non-accredited tests cannot produce CONTRADICTED
                elif not is_accredited:
                    c["audit_verdict"] = "NO EVIDENCE"
                    if gap is not None:
                        c["reason"] = f"Non-accredited test: {source_name} measured variance ({gap:+.1f}%), but non-accredited tests cannot set claim verdicts."
                    else:
                        c["reason"] = f"Non-accredited test: {source_name} finding noted for context only."

                # Rule D: Accredited test evaluations
                elif tier == "A" and matching_report.get("regulator_action") and any(w in c_text for w in ["health", "active", "strong"]):
                    if age_status == "recent" or allow_old:
                        c["audit_verdict"] = "CONTRADICTED"
                        c["reason"] = f"Contradicted by {source_name}: FSSAI directive confirmed no statutory category exists for 'Health Drink' in malted beverages."
                    else:
                        c["audit_verdict"] = "MISLEADING"
                        c["reason"] = f"Historical {source_name} finding; batch results apply to tested period."

                elif gap is not None and gap > self.tolerance_pct:
                    if age_status == "recent" or allow_old:
                        c["audit_verdict"] = "CONTRADICTED"
                        c["reason"] = f"Contradicted by {source_name}: Tested lab value exceeded declared label value by +{gap:.1f}% (above {self.tolerance_pct}% tolerance)."
                    else:
                        if c.get("audit_verdict") == "VERIFIED":
                            c["audit_verdict"] = "MISLEADING"
                        c["reason"] = (
                            f"Historical context ({matching_report.get('age_display')}): Lab test found +{gap:.1f}% variance, "
                            f"but cannot produce CONTRADICTED on its own due to report age ({age_status}). {self.batch_note}"
                        )

                elif gap is not None and abs(gap) <= self.tolerance_pct:
                    if c.get("audit_verdict") in ["VERIFIED", "NO EVIDENCE"]:
                        c["audit_verdict"] = "VERIFIED"
                        c["reason"] = f"Verified by {source_name}: Tested parameter verified within {self.tolerance_pct}% statutory tolerance (gap: {gap:+.1f}%)."

            if c.get("audit_verdict") not in ["VERIFIED", "MISLEADING", "CONTRADICTED", "NO EVIDENCE"]:
                c["audit_verdict"] = "NO EVIDENCE"

            updated_claims.append(c)

        return updated_claims

    # -------------------------------------------------------------------------
    # 7. Extraction Pipeline
    # -------------------------------------------------------------------------
    def extract_and_validate_record(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        record_id = raw_input.get("record_id") or f"ext_{int(datetime.now(timezone.utc).timestamp())}"
        raw_text = raw_input.get("raw_text_snippet") or raw_input.get("text", "")
        confidence = float(raw_input.get("confidence", 0.9))
        needs_review = bool(raw_input.get("needs_review", False))

        section = raw_input.get("section")
        if section == "social":
            raise ValueError(
                "Invalid evidence section: 'social'. Social content is not supported; "
                "evidence records must strictly belong to 'lab_regulatory'."
            )
        if section and section != "lab_regulatory":
            raise ValueError(
                f"Invalid evidence section: '{section}'. Evidence records must strictly belong to 'lab_regulatory'."
            )

        def parse_num(val: Any) -> Optional[float]:
            if val is None or val == "" or str(val).strip().lower() in ["not stated", "null", "none", "na", "-"]:
                return None
            try:
                num = float(val)
                return num if num >= 0 else None
            except (ValueError, TypeError):
                m = re.search(r'([0-9]+(?:\.[0-9]+)?)', str(val))
                if m:
                    num = float(m.group(1))
                    return num if num >= 0 else None
                return None

        label_val = parse_num(raw_input.get("label_value"))
        lab_val = parse_num(raw_input.get("lab_value"))

        unit = str(raw_input.get("unit") or "g/100g").strip()
        basis = str(raw_input.get("basis") or "per 100 g").strip()
        if not basis or basis.lower() in ["unknown", "not stated"]:
            basis = "per 100 g"

        lab_gap = None
        if label_val is not None and lab_val is not None:
            if label_val > 0:
                lab_gap = round(((lab_val - label_val) / label_val) * 100.0, 2)
            elif label_val == 0 and lab_val == 0:
                lab_gap = 0.0

        test_date = raw_input.get("test_date") or extract_report_date(raw_text)
        pub_date = raw_input.get("publication_date") or extract_report_date(raw_text)
        age_years, age_status, age_display = self.compute_report_age(test_date, pub_date)

        if confidence < 0.6:
            needs_review = True

        status = "accepted" if not needs_review else "reported_not_verified"
        not_verified_reason = None
        if needs_review:
            not_verified_reason = "Extraction confidence below threshold (< 0.60); marked for manual review."

        raw_url = str(raw_input.get("original_report_url") or "")
        clean_url, _ = normalize_and_sanitize_url(raw_url, self.allowed_domains)

        structured_record = {
            "record_id": record_id,
            "section": "lab_regulatory",
            "source_name": str(raw_input.get("source_name") or "Analytical Report"),
            "source_type": str(raw_input.get("source_type") or "lab_report"),
            "tier": str(raw_input.get("tier") or "C").upper(),
            "discovery_url": str(raw_input.get("discovery_url") or ""),
            "original_report_url": clean_url or raw_url,
            "final_url": clean_url or raw_url,
            "publication_date": pub_date,
            "test_date": test_date,
            "lab_name": str(raw_input.get("lab_name") or "not stated"),
            "accreditation_no": str(raw_input.get("accreditation_no") or "not stated"),
            "accreditation_checked": bool(raw_input.get("accreditation_checked", False)),
            "accreditation_source_url": str(raw_input.get("accreditation_source_url") or ""),
            "method": str(raw_input.get("method") or "not stated"),
            "sample_count": raw_input.get("sample_count") if raw_input.get("sample_count") is not None else "not stated",
            "batch": str(raw_input.get("batch") or "not stated"),
            "brand": str(raw_input.get("brand") or "not stated"),
            "product": str(raw_input.get("product") or "not stated"),
            "variant": str(raw_input.get("variant") or "not stated"),
            "pack_size": str(raw_input.get("pack_size") or "not stated"),
            "parameter": str(raw_input.get("parameter") or "not stated"),
            "label_value": label_val,
            "lab_value": lab_val,
            "unit": unit,
            "basis": basis,
            "lab_gap_pct": lab_gap,
            "brand_response": str(raw_input.get("brand_response") or "None on record."),
            "regulator_action": str(raw_input.get("regulator_action") or "None on record."),
            "age_years": age_years,
            "age_status": age_status,
            "age_display": age_display,
            "match": raw_input.get("match", {"same_product": True, "same_metric": True}),
            "status": status,
            "not_verified_reason": not_verified_reason,
            "confidence": confidence,
            "needs_review": needs_review,
            "raw_text_snippet": raw_text[:500] if raw_text else "No raw text snippet attached.",
            "fetched_at": raw_input.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
            "disclaimer": self.standard_disclaimer,
            "batch_note": self.batch_note,
            "verified_by": raw_input.get("verified_by"),
            "verified_at": raw_input.get("verified_at"),
        }

        return structured_record
