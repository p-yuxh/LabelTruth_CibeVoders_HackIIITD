import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, quote

import httpx

logger = logging.getLogger("labeltruth.link_verifier")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

DEFAULT_ALLOWED_DOMAINS = [
    "consumer-voice.org",
    "join.consumer-voice.org",
    "consumeraffairs.nic.in",
    "www.fssai.gov.in",
    "fssai.gov.in",
    "mail.fssai.gov.in",
    "nabl-india.org",
    "www.nin.res.in",
    "nin.res.in",
    "amul.com",
    "yogabars.in",
]

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
}


def load_allowed_domains() -> List[str]:
    """Loads allowed domains list from config/allowed_domains.json."""
    paths = [
        os.path.join(ROOT_DIR, "config", "allowed_domains.json"),
        os.path.join(BASE_DIR, "config_data", "allowed_domains.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    domains = data.get("allowed_domains", [])
                    if domains:
                        return [d.lower().strip() for d in domains]
            except Exception as e:
                logger.warning(f"Error reading allowed_domains from {p}: {e}")
    return DEFAULT_ALLOWED_DOMAINS


def load_source_directory() -> Dict[str, Any]:
    """Loads category browse directory from config/source_directory.json."""
    paths = [
        os.path.join(ROOT_DIR, "config", "source_directory.json"),
        os.path.join(BASE_DIR, "config_data", "source_directory.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading source_directory from {p}: {e}")
    return {"categories": {}, "special_directories": {}}


def normalize_and_sanitize_url(
    raw_url: str,
    allowed_domains: Optional[List[str]] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Provenance & URL Sanity Rule:
    - Strips surrounding whitespace, quotes, brackets, and trailing punctuation.
    - Preserves real filenames and typos (never fix spelling in paths).
    - Preserves host exactly (NO host swapping, no adding/removing 'www.').
    - Discards relative URLs (must start with https://).
    - If no scheme, prepends https://.
    - Percent-encodes spaces in path (e.g. 'Packaged%20Toned%20Milk.pdf').
    - Verifies host against allowed_domains.json.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None, "empty or missing URL"

    url = raw_url.strip().strip("'\"<>[](){}")
    # Strip trailing punctuation often appended from markdown/prose (e.g. '.', ';', ',')
    url = re.sub(r'[\.,;:]+$', '', url)

    if not url:
        return None, "empty URL after cleaning"

    # Reject relative hrefs
    if url.startswith('/'):
        return None, "relative hrefs are never allowed; every rendered link must start with https://"

    # Prepend https:// if no scheme
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+-.]*://', url):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return None, f"invalid URL syntax: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return None, f"unsupported scheme: {parsed.scheme}"

    host = parsed.netloc.lower().split(":")[0]
    if not host:
        return None, "missing host in URL"

    allowed = allowed_domains if allowed_domains is not None else load_allowed_domains()
    if host not in allowed:
        logger.warning(f"URL rejected: Host '{host}' is not listed in allowed_domains.json.")
        return None, f"host '{host}' not listed in allowed_domains.json"

    # Percent-encode spaces in path while preserving existing % encodings
    path = parsed.path
    if " " in path:
        path = path.replace(" ", "%20")

    # Reconstruct URL preserving exact host casing and real filename
    cleaned = parsed._replace(path=path).geturl()
    return cleaned, None


def extract_report_date(text: str) -> Optional[str]:
    """
    Extracts publication or test date from text or HTML snippet.
    Examples:
    - 'September 2021' -> '2021-09-01'
    - '15 March 2024' -> '2024-03-15'
    - '2024-04-02' -> '2024-04-02'
    """
    if not text or not isinstance(text, str):
        return None

    # 1. Day Month Year: e.g. '15 March 2024', '15-Mar-2024'
    m_dmy = re.search(
        r'\b([0-2]?\d|3[01])[-\s/]+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[-\s/]+(20\d\d|19\d\d)\b',
        text,
        re.IGNORECASE
    )
    if m_dmy:
        day = int(m_dmy.group(1))
        month_str = m_dmy.group(2).lower()
        year = int(m_dmy.group(3))
        month = MONTH_MAP.get(month_str, 1)
        return f"{year:04d}-{month:02d}-{day:02d}"

    # 2. ISO format: '2024-04-02'
    m_iso = re.search(r'\b(20\d\d|19\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b', text)
    if m_iso:
        return m_iso.group(0)

    # 3. Month Year: e.g. 'September 2021', 'September, 2021'
    m_my = re.search(
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[,\s]+(20\d\d|19\d\d)\b',
        text,
        re.IGNORECASE
    )
    if m_my:
        month_str = m_my.group(1).lower()
        year_str = m_my.group(2)
        month = MONTH_MAP.get(month_str, 1)
        return f"{year_str}-{month:02d}-01"

    # 4. Standard Slash Date: DD/MM/YYYY or MM/DD/YYYY
    m_slash = re.search(r'\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d\d|19\d\d)\b', text)
    if m_slash:
        return f"{m_slash.group(3)}-{m_slash.group(2)}-{m_slash.group(1)}"

    return None


class DiagnosticsRegistry:
    """Internal diagnostic tracker for link retrieval, verification, and failures."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DiagnosticsRegistry, cls).__new__(cls)
            cls._instance.source_metrics = {}
            cls._instance.failed_links = []
        return cls._instance

    def log_link_outcome(
        self,
        source_name: str,
        source_id: Optional[int],
        url: str,
        status: str,  # 'accepted', 'reachable', 'dead', 'restricted', 'error'
        reason: Optional[str] = None
    ):
        s_key = source_name or "unknown"
        if s_key not in self.source_metrics:
            self.source_metrics[s_key] = {
                "retrieved": 0,
                "accepted": 0,
                "reachable": 0,
                "dead": 0,
                "restricted": 0,
                "error": 0,
            }
        self.source_metrics[s_key]["retrieved"] += 1
        if status in self.source_metrics[s_key]:
            self.source_metrics[s_key][status] += 1

        if status in ("dead", "restricted", "error") or (reason and "not" in reason.lower()):
            self.failed_links.append({
                "source_id": source_id,
                "retrieved_url": url,
                "status": status,
                "reason": reason or "Verification check failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "source_metrics": self.source_metrics,
            "failed_links": self.failed_links[-100:],  # last 100 failed links
            "total_failed_count": len(self.failed_links),
        }


class LinkVerifier:
    """
    Server-side Link Verifier with 7-day caching, redirect following,
    soft-404 detection, and strict status categorisation:
    - reachable: HTTP 200-299 AND content matches brand/product or report title / PDF.
    - dead: 404, 410, DNS failure, connection refused, soft 404.
    - restricted: 401, 403, 429, login redirect, or subscription gate (join.consumer-voice.org).
    - error: timeout or 5xx; retried once before failing.
    """

    def __init__(self, cache_ttl_days: int = 7, timeout_seconds: float = 10.0):
        self.cache_ttl_days = cache_ttl_days
        self.timeout_seconds = timeout_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.diagnostics = DiagnosticsRegistry()

    def verify_link(
        self,
        url: str,
        product_name: str = "",
        brand: str = "",
        report_title: str = "",
        source_id: Optional[int] = None,
        source_name: str = "Independent Lab Source",
        client: Optional[httpx.Client] = None,
    ) -> Dict[str, Any]:
        """
        Verifies a URL, checking cache first (7-day TTL).
        """
        now = datetime.now(timezone.utc)
        normalized_url, sanitization_error = normalize_and_sanitize_url(url)

        if sanitization_error:
            result = {
                "link_status": "dead",
                "http_status": None,
                "final_url": url,
                "checked_at": now.isoformat(),
                "error_reason": sanitization_error,
                "archived_url": f"https://web.archive.org/web/{url}",
                "is_restricted": False,
            }
            self.diagnostics.log_link_outcome(source_name, source_id, url, "dead", sanitization_error)
            return result

        cache_key = normalized_url
        cached = self.cache.get(cache_key)
        if cached:
            checked_at_dt = datetime.fromisoformat(cached["checked_at"])
            if now - checked_at_dt < timedelta(days=self.cache_ttl_days):
                return cached

        # Check subscription-gated domains before network
        parsed = urlparse(normalized_url)
        host = parsed.netloc.lower().split(":")[0]
        if host == "join.consumer-voice.org":
            result = {
                "link_status": "restricted",
                "http_status": 403,
                "final_url": normalized_url,
                "checked_at": now.isoformat(),
                "error_reason": "Detailed results may require a subscription",
                "archived_url": f"https://web.archive.org/web/{normalized_url}",
                "is_restricted": True,
            }
            self.cache[cache_key] = result
            self.diagnostics.log_link_outcome(source_name, source_id, normalized_url, "restricted", "Subscription gated domain")
            return result

        # Perform HTTP check with 1 retry on timeout/5xx
        result = self._execute_http_check(
            normalized_url,
            product_name=product_name,
            brand=brand,
            report_title=report_title,
            client=client,
        )
        self.cache[cache_key] = result
        self.diagnostics.log_link_outcome(
            source_name, source_id, normalized_url, result["link_status"], result.get("error_reason")
        )
        return result

    def _execute_http_check(
        self,
        url: str,
        product_name: str,
        brand: str,
        report_title: str,
        client: Optional[httpx.Client] = None,
    ) -> Dict[str, Any]:
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        }
        now_str = datetime.now(timezone.utc).isoformat()

        def _do_request():
            if client:
                # Follow redirects up to 5
                try:
                    resp = client.head(url, headers=headers, follow_redirects=True, timeout=self.timeout_seconds)
                    if resp.status_code in (405, 403, 400):
                        resp = client.get(url, headers=headers, follow_redirects=True, timeout=self.timeout_seconds)
                except Exception:
                    resp = client.get(url, headers=headers, follow_redirects=True, timeout=self.timeout_seconds)
                return resp
            else:
                with httpx.Client(follow_redirects=True, timeout=self.timeout_seconds, max_redirects=5) as c:
                    try:
                        resp = c.head(url, headers=headers)
                        if resp.status_code in (405, 403, 400):
                            resp = c.get(url, headers=headers)
                    except Exception:
                        resp = c.get(url, headers=headers)
                    return resp

        # Attempt 1
        resp = None
        last_exc = None
        for attempt in range(2):
            try:
                resp = _do_request()
                # If 5xx, retry once
                if resp.status_code >= 500 and attempt == 0:
                    time.sleep(0.5)
                    continue
                break
            except (httpx.TimeoutException, httpx.ConnectTimeout) as e:
                last_exc = e
                if attempt == 0:
                    time.sleep(0.5)
                    continue
            except (httpx.ConnectError, httpx.NetworkError) as e:
                # DNS failure or connection refused -> dead
                return {
                    "link_status": "dead",
                    "http_status": None,
                    "final_url": url,
                    "checked_at": now_str,
                    "error_reason": f"Connection refused or DNS resolution failed: {e}",
                    "archived_url": f"https://web.archive.org/web/{url}",
                    "is_restricted": False,
                }
            except Exception as e:
                last_exc = e
                break

        if resp is None:
            return {
                "link_status": "error",
                "http_status": None,
                "final_url": url,
                "checked_at": now_str,
                "error_reason": f"Request failed after retry: {last_exc}",
                "archived_url": f"https://web.archive.org/web/{url}",
                "is_restricted": False,
            }

        status_code = resp.status_code
        final_url = str(resp.url)

        # 404, 410 -> dead
        if status_code in (404, 410):
            return {
                "link_status": "dead",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": f"HTTP {status_code} Not Found",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": False,
            }

        # 401, 403, 429, or login redirect -> restricted
        if status_code in (401, 403, 429) or "login" in final_url.lower() or "signin" in final_url.lower():
            return {
                "link_status": "restricted",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": "Detailed results may require a subscription",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": True,
            }

        # 5xx -> error
        if status_code >= 500:
            return {
                "link_status": "error",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": f"HTTP {status_code} Server Error",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": False,
            }

        # 200..299 -> Verify content and soft 404
        content_type = resp.headers.get("Content-Type", "").lower()
        is_pdf = "application/pdf" in content_type or final_url.lower().endswith(".pdf")

        body_text = ""
        try:
            body_text = resp.text.lower()
        except Exception:
            body_text = ""

        # Soft 404 check
        soft_404_markers = [
            "page not found", "404 not found", "error 404", "article not found",
            "we can't find that page", "the requested url was not found"
        ]
        if any(marker in body_text for marker in soft_404_markers):
            return {
                "link_status": "dead",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": "Soft 404 detected in page body",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": False,
            }

        # Check homepage redirect: if requested URL had a specific path, but redirected to root '/'
        req_path = urlparse(url).path.strip('/')
        final_path = urlparse(final_url).path.strip('/')
        if req_path and not final_path:
            return {
                "link_status": "dead",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": "Redirected to generic homepage root (soft 404)",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": False,
            }

        # Check content match if HTML
        match_found = False
        if is_pdf:
            # PDF responses are verified
            match_found = True
        else:
            # Check brand, product or report title keywords
            tokens_to_check = []
            if brand:
                tokens_to_check.extend([t for t in re.findall(r'\b\w{3,}\b', brand.lower()) if t not in ("the", "ltd", "and")])
            if product_name:
                tokens_to_check.extend([t for t in re.findall(r'\b\w{4,}\b', product_name.lower()) if t not in ("pack", "with", "food")])
            if report_title:
                tokens_to_check.extend([t for t in re.findall(r'\b\w{4,}\b', report_title.lower()) if t not in ("report", "test", "comparative")])

            if tokens_to_check:
                match_found = any(token in body_text for token in tokens_to_check)
            else:
                match_found = True

        if not match_found and body_text:
            return {
                "link_status": "dead",
                "http_status": status_code,
                "final_url": final_url,
                "checked_at": now_str,
                "error_reason": "Content mismatch: Target brand or product not mentioned on page",
                "archived_url": f"https://web.archive.org/web/{final_url}",
                "is_restricted": False,
            }

        return {
            "link_status": "reachable",
            "http_status": status_code,
            "final_url": final_url,
            "checked_at": now_str,
            "error_reason": None,
            "archived_url": None,
            "is_restricted": False,
        }


# Global singleton instance
link_verifier = LinkVerifier()

