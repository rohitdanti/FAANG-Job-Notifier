"""State management for seen jobs across multiple company-specific files."""

import json
import os
import re
import time
from datetime import date
from typing import Any, Sequence

import config

STATE_VERSION = 3

# Regex to split combo titles like "SWE II + Senior SWE" or "PM / Director"
_COMBO_SPLIT = re.compile(r"\s*[+/|]\s*")


def _company_state_file(company_slug: str) -> str:
    return os.path.join(config.SEEN_JOBS_DIR, f"{company_slug}.json")


def _ensure_state_dir() -> None:
    os.makedirs(config.SEEN_JOBS_DIR, exist_ok=True)


def _empty_company_state(company_slug: str) -> dict[str, Any]:
    return {
        "_meta": {"version": STATE_VERSION, "company": company_slug},
        "jobs": {},
    }


def _normalize_company_state(company_slug: str, data: Any) -> dict[str, Any]:
    state = _empty_company_state(company_slug)
    if not isinstance(data, dict):
        return state

    if isinstance(data.get("jobs"), dict):
        state["jobs"] = data["jobs"]
        return state

    state["jobs"] = data
    return state


def _load_company_state(company_slug: str) -> dict[str, Any]:
    state_file = _company_state_file(company_slug)
    if not os.path.exists(state_file):
        return _empty_company_state(company_slug)

    try:
        with open(state_file, "r") as handle:
            return _normalize_company_state(company_slug, json.load(handle))
    except (json.JSONDecodeError, IOError):
        return _empty_company_state(company_slug)


def _prune_seen_jobs(seen: dict[str, Any]) -> dict[str, Any]:
    if len(seen) <= config.MAX_SEEN_JOBS:
        return seen

    sorted_keys = sorted(seen, key=lambda key: seen[key].get("first_seen", 0))
    excess = len(seen) - config.MAX_SEEN_JOBS
    for key in sorted_keys[:excess]:
        del seen[key]
    return seen


def load_seen_jobs(company_slug: str) -> dict[str, Any]:
    return _load_company_state(company_slug)["jobs"]


def save_seen_jobs(company_slug: str, seen: dict[str, Any]) -> None:
    _ensure_state_dir()
    state = _empty_company_state(company_slug)
    state["jobs"] = _prune_seen_jobs(dict(seen))
    with open(_company_state_file(company_slug), "w") as handle:
        json.dump(state, handle, indent=2)


def _part_matches_excluded(part: str, excluded_role_keywords: Sequence[str]) -> bool:
    """Check if a single title part matches any excluded keyword."""
    part_lower = part.strip().lower()
    if not part_lower:
        return False
    return any(keyword.lower() in part_lower for keyword in excluded_role_keywords)


def is_excluded_role(title: str, excluded_role_keywords: Sequence[str]) -> bool:
    """
    Return True if the job title should be excluded.

    Logic: split the title on combo delimiters (+, /, |).  If *every* part
    contains an excluded keyword the role is excluded.  If at least one part
    is clean, the job is kept — this preserves combo postings like
    "Software Engineer II + Senior Software Engineer".
    """
    parts = _COMBO_SPLIT.split(title)
    if not parts or all(not p.strip() for p in parts):
        return False
    return all(_part_matches_excluded(part, excluded_role_keywords) for part in parts if part.strip())

def should_exclude_title(
    title: str,
    excluded_role_keywords: Sequence[str],
    excluded_title_phrases: Sequence[str],
) -> bool:
    title_lower = title.strip().lower()
    if not title_lower:
        return False

    if any(title_lower == keyword.lower() for keyword in excluded_role_keywords):
        return True

    return any(phrase.lower() in title_lower for phrase in excluded_title_phrases)


def _today_date_string() -> str:
    return date.today().isoformat()


def _job_state_payload(job: dict, posted_override: str | None = None) -> dict[str, Any]:
    return {
        "first_seen": time.time(),
        "posted": posted_override if posted_override is not None else job.get("posted", ""),
        "title": job.get("title", ""),
        "job_id": job.get("job_id") or job.get("role_number") or job.get("key", ""),
        "url": job.get("url", ""),
    }


def filter_new_jobs(company_slug: str, jobs: list[dict]) -> list[dict]:
    seen = load_seen_jobs(company_slug)
    new_jobs = []
    discovered_on = _today_date_string()

    for job in jobs:
        key = job.get("key") or job.get("job_id") or job.get("role_number")
        if not key:
            continue
        if key not in seen:
            new_jobs.append(job)
            seen[key] = _job_state_payload(job, posted_override=discovered_on)

    if new_jobs:
        save_seen_jobs(company_slug, seen)

    return new_jobs


def replace_seen_jobs(company_slug: str, jobs: list[dict]) -> None:
    seen = {}
    for job in jobs:
        key = job.get("key") or job.get("job_id") or job.get("role_number")
        if not key:
            continue
        seen[key] = _job_state_payload(job)
    save_seen_jobs(company_slug, seen)
