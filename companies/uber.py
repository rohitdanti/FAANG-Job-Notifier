import json
from urllib.parse import parse_qs, urlsplit, urlunsplit

from playwright.async_api import TimeoutError as PlaywrightTimeout

from companies.base import CompanyDefinition
from uber_parser import get_total_pages, get_total_results, parse_jobs

UBER_SEARCH_URL = (
    "https://www.uber.com/us/en/careers/list/"
    "?department=Engineering"
    "&location=USA-California-San%20Francisco"
    "&location=USA-California-Sunnyvale"
    "&location=USA-California-Los%20Angeles"
    "&location=USA-New%20York-New%20York"
    "&location=USA-Illinois-Chicago"
    "&location=USA-Washington-Seattle"
    "&location=USA-Florida-Miami"
    "&location=USA-Arizona-Phoenix"
    "&location=USA-Texas-Dallas"
    "&location=USA-Massachusetts-Boston"
    "&location=USA-District%20of%20Columbia-Washington"
    "&location=USA-Tennessee-Nashville"
    "&location=USA-Colorado-Denver"
    "&location=USA-Georgia-Atlanta"
)

EXCLUDED_ROLE_KEYWORDS = (
    "principal",
    "senior",
    "staff",
    "lead",
    "director",
    "manager",
    "sr.",
    "sr ",
)

RESULTS_PER_PAGE = 10
UBER_API_URL = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"


def build_search_url(search_url: str, page_num: int) -> str:
    parsed = urlsplit(search_url)
    return urlunsplit(parsed._replace(fragment=f"page={page_num}"))


def _page_num_from_url(url: str) -> int:
    fragment = urlsplit(url).fragment
    if fragment.startswith("page="):
        try:
            return max(1, int(fragment.split("=", 1)[1]))
        except ValueError:
            return 1
    return 1


def _build_api_payload(search_url: str, page_num: int) -> dict:
    parsed = urlsplit(search_url)
    params = parse_qs(parsed.query)

    locations = []
    for raw_location in params.get("location", []):
        parts = raw_location.split("-")
        if len(parts) < 3:
            continue

        country, region, city_parts = parts[0], parts[1], parts[2:]
        locations.append(
            {
                "country": country,
                "region": region.replace("%20", " "),
                "city": "-".join(city_parts).replace("%20", " "),
            }
        )

    departments = [value.replace("%20", " ") for value in params.get("department", [])]

    return {
        "limit": RESULTS_PER_PAGE,
        "page": max(0, page_num - 1),
        "params": {
            "location": locations,
            "department": departments,
        },
    }


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = _page_num_from_url(url)
    payload = _build_api_payload(runtime_config.search_url, page_num)

    print(f"[{runtime_config.slug}] Loading API page {page_num}: {UBER_API_URL}")
    response = await page.context.request.post(
        UBER_API_URL,
        headers={
            "content-type": "application/json",
            "referer": runtime_config.search_url,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-csrf-token": "x",
            "x-uber-sites-page-edge-cache-enabled": "true",
        },
        data=json.dumps(payload),
        timeout=30000,
    )
    if not response.ok:
        raise RuntimeError(f"Uber API request failed with status {response.status}")
    return await response.text()


COMPANY = CompanyDefinition(
    slug="uber",
    display_name="Uber",
    default_search_url=UBER_SEARCH_URL,
    # Uber listings are loaded incrementally ("Show more openings") and are not sorted
    # by recency, so regular runs should cover the full filtered result set.
    default_max_pages=50,
    default_full_scrape_max_pages=50,
    wait_selectors=(
        'a[href*="/careers/list/"]',
        'text=open roles',
        'text=Find open roles',
    ),
    build_search_url=build_search_url,
    parse_jobs=parse_jobs,
    get_total_pages=get_total_pages,
    get_total_results=get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
)