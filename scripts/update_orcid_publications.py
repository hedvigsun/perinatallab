#!/usr/bin/env python3
"""Refresh Jekyll's ORCID publications data from public ORCID works.

Usage: python scripts/update_orcid_publications.py
Environment: ORCID_CLIENT_ID and ORCID_CLIENT_SECRET (public API credentials)

Deliberately fails before writing if even one ORCID request fails. This prevents a
transient API outage from silently removing people or publications from the site.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
RESEARCHERS_PATH = ROOT / "_data" / "orcid_researchers.json"
OUTPUT_PATH = ROOT / "_data" / "orcid_publications.json"
API_ROOT = "https://pub.orcid.org/v3.0"
TOKEN_URL = "https://orcid.org/oauth/token"
ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$")


def valid_orcid(value: str) -> bool:
    if not ORCID_PATTERN.fullmatch(value):
        return False
    digits = value.replace("-", "")
    total = 0
    for digit in digits[:15]:
        total = (total + int(digit)) * 2
    check = (12 - (total % 11)) % 11
    return ("X" if check == 10 else str(check)) == digits[15]


def normalize_orcid(value: str) -> str:
    value = str(value).strip().removeprefix("https://orcid.org/").upper()
    if not valid_orcid(value):
        raise ValueError(f"Invalid ORCID iD: {value!r}")
    return value


def request_json(url: str, headers: dict[str, str], data: bytes | None = None) -> dict:
    """Retry transient server/rate-limit failures; never retry invalid auth."""
    for attempt in range(4):
        req = request.Request(url, data=data, headers=headers)
        try:
            with request.urlopen(req, timeout=35) as response:
                return json.load(response)
        except error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"ORCID API returned HTTP {exc.code} for {url}") from exc
        except (error.URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Could not reach ORCID API at {url}: {exc}") from exc
        time.sleep(2 ** attempt)
    raise AssertionError("Unreachable retry state")


def access_token() -> str:
    client_id = os.environ.get("ORCID_CLIENT_ID")
    client_secret = os.environ.get("ORCID_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Set ORCID_CLIENT_ID and ORCID_CLIENT_SECRET as GitHub Actions secrets")
    payload = parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "/read-public",
    }).encode("utf-8")
    result = request_json(TOKEN_URL, {"Accept": "application/json"}, payload)
    token = result.get("access_token")
    if not token:
        raise RuntimeError("ORCID did not return a public API access token")
    return token


def text_value(node) -> str:
    if isinstance(node, dict):
        return str(node.get("value") or "").strip()
    return str(node or "").strip()


def canonical_doi(value: str) -> str:
    value = parse.unquote(value.strip()).lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.strip().rstrip(".,; ")


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def extract_work(summary: dict, researcher: dict) -> dict | None:
    title = text_value((summary.get("title") or {}).get("title"))
    if not title:
        return None
    date = summary.get("publication-date") or {}
    year_text = text_value(date.get("year"))
    year = int(year_text) if year_text.isdigit() else None
    month_text = text_value(date.get("month"))
    day_text = text_value(date.get("day"))
    doi = ""
    external_ids = (summary.get("external-ids") or {}).get("external-id") or []
    for item in external_ids:
        if str(item.get("external-id-type", "")).lower() == "doi":
            candidate = canonical_doi(str(item.get("external-id-value") or ""))
            if candidate:
                doi = candidate
                if item.get("external-id-relationship") == "self":
                    break
    raw_url = text_value(summary.get("url"))
    if not raw_url.startswith(("https://", "http://")):
        raw_url = ""  # ORCID-supplied URLs must not become unsafe href schemes.
    journal = text_value(summary.get("journal-title"))
    kind = str(summary.get("type") or "other").strip()
    return {
        "title": title,
        "year": year,
        "month": int(month_text) if month_text.isdigit() else None,
        "day": int(day_text) if day_text.isdigit() else None,
        "type": kind,
        "journal": journal,
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else (raw_url or f"https://orcid.org/{researcher['orcid']}"),
        "researchers": [{"name": researcher["name"], "orcid": researcher["orcid"]}],
    }


def merge_publications(items: list[dict]) -> list[dict]:
    merged: list[dict] = []
    by_doi: dict[str, int] = {}
    by_title: dict[tuple, list[int]] = {}
    for item in items:
        doi = item["doi"]
        # Preprint and journal-article records with different DOIs stay separate.
        title_key = (normalized_title(item["title"]), item["year"], item["type"])
        idx = by_doi.get(doi) if doi else None
        if idx is None:
            # Only title-merge if at least one record lacks a DOI.
            for candidate in by_title.get(title_key, []):
                other_doi = merged[candidate]["doi"]
                if not doi or not other_doi or doi == other_doi:
                    idx = candidate
                    break
        if idx is None:
            idx = len(merged)
            merged.append(item.copy())
            merged[idx]["researchers"] = item["researchers"].copy()
            by_title.setdefault(title_key, []).append(idx)
        else:
            existing = merged[idx]
            for person in item["researchers"]:
                if person["orcid"] not in {p["orcid"] for p in existing["researchers"]}:
                    existing["researchers"].append(person)
            for field in ("journal", "year", "month", "day"):
                if not existing[field] and item[field]:
                    existing[field] = item[field]
            if not existing["doi"] and doi:
                existing["doi"] = doi
                existing["url"] = f"https://doi.org/{doi}"
        if doi:
            by_doi[doi] = idx
    for item in merged:
        item["researchers"].sort(key=lambda p: p["name"].lower())
    merged.sort(key=lambda p: (
        p["year"] or 0, p["month"] or 0, p["day"] or 0,
        p["title"].lower()), reverse=True)
    return merged


def main() -> None:
    researchers = json.loads(RESEARCHERS_PATH.read_text(encoding="utf-8"))
    if not researchers or not isinstance(researchers, list):
        raise ValueError("_data/orcid_researchers.json needs at least one researcher")
    seen = set()
    for person in researchers:
        person["name"] = str(person["name"]).strip()
        person["orcid"] = normalize_orcid(person["orcid"])
        if not person["name"] or person["orcid"] in seen:
            raise ValueError("Each researcher needs a name and a unique ORCID iD")
        seen.add(person["orcid"])

    token = access_token()
    headers = {"Accept": "application/vnd.orcid+json", "Authorization": f"Bearer {token}"}
    works: list[dict] = []
    for person in researchers:
        url = f"{API_ROOT}/{person['orcid']}/works"
        response = request_json(url, headers)
        if not isinstance(response.get("group"), list):
            raise RuntimeError(f"Unexpected works response for {person['orcid']}")
        count_before = len(works)
        for group in response["group"]:
            for summary in group.get("work-summary") or []:
                work = extract_work(summary, person)
                if work:
                    works.append(work)
        print(f"{person['name']}: {len(works) - count_before} public ORCID work records")

    final = merge_publications(works)
    rendered = json.dumps(final, indent=2, ensure_ascii=False) + "\n"
    if OUTPUT_PATH.exists() and OUTPUT_PATH.read_text(encoding="utf-8") == rendered:
        print(f"No publication changes ({len(final)} unique works)")
        return
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Updated {OUTPUT_PATH.relative_to(ROOT)}: {len(final)} unique works")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
