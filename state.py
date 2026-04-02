"""
State management — tracks which jobs have already been seen.
Persists to a JSON file so state survives across runs (including GitHub Actions).
"""

import json
import os
import re
import time
from typing import Any
import config
from config import EXCLUDED_ROLE_KEYWORDS, EXCLUDED_TITLE_PHRASES

# Regex to split combo titles like "SWE II + Senior SWE" or "PM / Director"
_COMBO_SPLIT = re.compile(r"\s*[+/|]\s*")


def load_seen_jobs() -> dict[str, Any]:
    """Load the set of previously seen job keys from disk."""
    if not os.path.exists(config.SEEN_JOBS_FILE):
        return {}
    try:
        with open(config.SEEN_JOBS_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            # Migrate from old list format if needed
            return {key: {"first_seen": time.time()} for key in data}
    except (json.JSONDecodeError, IOError):
        return {}


def save_seen_jobs(seen: dict[str, Any]) -> None:
    """Persist seen jobs to disk, pruning if over the rolling window limit."""
    # Prune oldest entries if we exceed the cap
    if len(seen) > config.MAX_SEEN_JOBS:
        # Sort by first_seen timestamp, keep the newest MAX_SEEN_JOBS entries
        sorted_keys = sorted(seen, key=lambda k: seen[k].get("first_seen", 0))
        excess = len(seen) - config.MAX_SEEN_JOBS
        for key in sorted_keys[:excess]:
            del seen[key]

    with open(config.SEEN_JOBS_FILE, "w") as f:
        json.dump(seen, f, indent=2)


def _part_matches_excluded(part: str) -> bool:
    """Check if a single title part matches any excluded keyword."""
    part_lower = part.strip().lower()
    if not part_lower:
        return False
    for keyword in config.EXCLUDED_ROLE_KEYWORDS:
        if keyword in part_lower:
            return True
    return False


def is_excluded_role(title: str) -> bool:
    """
    Return True if the job title should be excluded.

    Logic: split the title on combo delimiters (+, /, |).  If *every* part
    contains an excluded keyword the role is excluded.  If at least one part
    is clean, the job is kept — this preserves combo postings like
    "Software Engineer II + Senior Software Engineer".
    """
    parts = _COMBO_SPLIT.split(title)
    # If there are no meaningful parts, don't exclude
    if not parts or all(not p.strip() for p in parts):
        return False
    return all(_part_matches_excluded(p) for p in parts if p.strip())

def should_exclude_title(title):
    # Exclude if title matches any keyword exactly (case-insensitive)
    for keyword in EXCLUDED_ROLE_KEYWORDS:
        if title.strip().lower() == keyword.lower():
            return True
    # Exclude if any phrase appears anywhere in the title (case-insensitive)
    for phrase in EXCLUDED_TITLE_PHRASES:
        if phrase.lower() in title.lower():
            return True
    return False
    
def filter_new_jobs(jobs: list[dict]) -> list[dict]:
    """
    Given a list of scraped job dicts, return only the ones not previously seen.
    Each job dict must have a 'role_number' field (unique identifier).
    Also updates and saves the seen-jobs state.
    """
    seen = load_seen_jobs()
    new_jobs = []

    for job in jobs:
        key = job["role_number"]
        if key not in seen:
            new_jobs.append(job)
            seen[key] = {
                "first_seen": time.time(),
                "posted": job.get("posted", ""),
                "title": job.get("title", ""),
                "job_id": job["role_number"],
            }

    if new_jobs:
        save_seen_jobs(seen)

    return new_jobs
