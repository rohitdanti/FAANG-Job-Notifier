import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

LYFT_BASE_URL = "https://app.careerpuck.com"
LYFT_JOB_LINK_RE = re.compile(r"/job-board/lyft/job/(?P<job_id>\d+)")
LYFT_TOTAL_RESULTS_RE = re.compile(r"(?P<count>\d+)\s+job postings found", re.IGNORECASE)
EXCLUDED_LOCATION_PHRASE = "toronto coworking"


def parse_jobs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    seen_ids = set()

    for link in soup.find_all("a", href=LYFT_JOB_LINK_RE):
        href = (link.get("href") or "").strip()
        match = LYFT_JOB_LINK_RE.search(href)
        if not match:
            continue

        job_id = match.group("job_id")
        if job_id in seen_ids:
            continue

        title, location, team = _extract_card_fields(link.get_text("\n", strip=True))
        if not title or _should_exclude_location(location):
            continue

        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "team": team,
                "location": location,
                "posted": "",
                "description": "",
                "url": urljoin(LYFT_BASE_URL, href),
            }
        )
        seen_ids.add(job_id)

    return jobs


def _extract_card_fields(card_text: str) -> tuple[str, str, str]:
    lines = [" ".join(line.split()) for line in card_text.splitlines() if line.strip()]
    if not lines:
        return "", "", ""

    title = lines[0]
    details_line = next((line for line in lines[1:] if line.lower() != "learn more"), "")
    if not details_line:
        return title, "", ""

    location, separator, team = details_line.partition(" - ")
    if not separator:
        return title, details_line, ""
    return title, location.strip(), team.strip()


def _should_exclude_location(location: str) -> bool:
    return EXCLUDED_LOCATION_PHRASE in location.strip().lower()


def get_total_results(html: str) -> int | None:
    match = LYFT_TOTAL_RESULTS_RE.search(BeautifulSoup(html, "lxml").get_text(" ", strip=True))
    if not match:
        return None
    return int(match.group("count"))


def get_total_pages(html: str) -> int | None:
    total_results = get_total_results(html)
    if total_results is None:
        return 1 if parse_jobs(html) else 0
    return 1 if total_results > 0 else 0
