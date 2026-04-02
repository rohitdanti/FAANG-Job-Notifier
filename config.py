"""
Configuration for the Apple Jobs Notifier.
All settings are centralized here. Secrets come from environment variables.
"""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Apple Jobs search
APPLE_SEARCH_URL = (
    "https://jobs.apple.com/en-us/search"
    "?sort=newest"
    "&location=united-states-USA"
    "&team=apps-and-frameworks-SFTWR-AF+cloud-and-infrastructure-SFTWR-CLD"
    "+core-operating-systems-SFTWR-COS+devops-and-site-reliability-SFTWR-DSR"
    "+engineering-project-management-SFTWR-EPM"
    "+information-systems-and-technology-SFTWR-ISTECH"
    "+machine-learning-and-ai-SFTWR-MCHLN+security-and-privacy-SFTWR-SEC"
    "+software-quality-automation-and-tools-SFTWR-SQAT"
    "+wireless-software-SFTWR-WSFT"
)

SEARCH_URL = os.getenv("APPLE_SEARCH_URL", APPLE_SEARCH_URL)


def build_search_url(page_num: int) -> str:
    """Return the Apple search URL for a 1-based results page."""
    parsed = urlsplit(SEARCH_URL)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["page"] = str(page_num)
    return urlunsplit(parsed._replace(query=urlencode(params, doseq=True)))


# Scraping
MAX_PAGES = int(os.getenv("MAX_PAGES", "2"))  # regular runs: first 2 pages only (~40 jobs)
FULL_SCRAPE_MAX_PAGES = int(os.getenv("FULL_SCRAPE_MAX_PAGES", "90"))  # full scrape: up to 90 pages
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "15000"))
JOB_CARD_TIMEOUT = int(os.getenv("JOB_CARD_TIMEOUT", "8000"))

# Role filtering
EXCLUDED_ROLE_KEYWORDS = [
    "principal",
    "staff",
    "senior",
    "sr.",
    "manager",
    "lead",
    "director",
]

EXCLUDED_TITLE_PHRASES = [
    "machine learning manager",
    "engineering manager",
    "program manager",
]

# State
SEEN_JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_jobs.json")
MAX_SEEN_JOBS = 3000
