import json
import math
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
_FILTERED_JOBS_CACHE: dict[str, list[dict]] = {}


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

    payload = {
        "limit": RESULTS_PER_PAGE,
        "page": max(0, page_num - 1),
    }

    params = {}
    if locations:
        params["location"] = locations
    if departments:
        params["department"] = departments
    if params:
        payload["params"] = params

    return payload


def _extract_search_filters(search_url: str) -> tuple[list[dict], list[str]]:
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
    return locations, departments


def _build_relaxed_api_payload(page_num: int) -> dict:
    return {
        "limit": RESULTS_PER_PAGE,
        "page": max(0, page_num - 1),
    }


def _extract_result_count(payload: str) -> int | None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    results = data.get("data", {}).get("results")
    if isinstance(results, list):
        return len(results)
    if isinstance(results, dict):
        items = results.get("items")
        if isinstance(items, list):
            return len(items)

    top_level_results = data.get("results")
    if isinstance(top_level_results, list):
        return len(top_level_results)

    return None


def _extract_total_results(payload: str) -> int | None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    total_results = data.get("data", {}).get("totalResults")
    if isinstance(total_results, int):
        return total_results
    if isinstance(total_results, dict):
        low = total_results.get("low")
        if isinstance(low, int):
            return low

    return None


def _extract_raw_results(payload: str) -> list[dict]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    nested_data = data.get("data", {})
    if isinstance(nested_data, dict):
        nested_results = nested_data.get("results")
        if isinstance(nested_results, list):
            return [item for item in nested_results if isinstance(item, dict)]
        if isinstance(nested_results, dict):
            nested_items = nested_results.get("items")
            if isinstance(nested_items, list):
                return [item for item in nested_items if isinstance(item, dict)]

        nested_jobs = nested_data.get("jobs")
        if isinstance(nested_jobs, list):
            return [item for item in nested_jobs if isinstance(item, dict)]

    top_level_results = data.get("results")
    if isinstance(top_level_results, list):
        return [item for item in top_level_results if isinstance(item, dict)]

    top_level_jobs = data.get("jobs")
    if isinstance(top_level_jobs, list):
        return [item for item in top_level_jobs if isinstance(item, dict)]

    return []


def _matches_department(raw_job: dict, departments: list[str]) -> bool:
    if not departments:
        return True

    haystack = " ".join(
        str(raw_job.get(key) or "") for key in ("department", "programAndPlatform", "team")
    ).lower()
    if not haystack:
        return False

    for department in departments:
        candidate = department.strip().lower()
        if not candidate:
            continue
        if candidate in haystack:
            return True
        if candidate == "engineering" and "engineer" in haystack:
            return True

    return False


def _matches_location(raw_job: dict, locations: list[dict]) -> bool:
    if not locations:
        return True

    raw_locations = raw_job.get("allLocations") or [raw_job.get("location")]
    for raw_location in raw_locations:
        if not isinstance(raw_location, dict):
            continue

        raw_country = str(raw_location.get("country") or raw_location.get("countryName") or "").strip().lower()
        raw_country_name = str(raw_location.get("countryName") or "").strip().lower()
        raw_city = str(raw_location.get("city") or "").strip().lower()
        raw_region = str(raw_location.get("region") or "").strip().lower()

        for expected in locations:
            expected_country = str(expected.get("country") or "").strip().lower()
            expected_city = str(expected.get("city") or "").strip().lower()
            if expected_country and expected_country not in {raw_country, raw_country_name}:
                continue
            if expected_city and expected_city not in {raw_city, raw_region}:
                continue
            return True

    return False


def _filter_raw_jobs(raw_jobs: list[dict], locations: list[dict], departments: list[str]) -> list[dict]:
    filtered_jobs = []
    seen_ids = set()

    for raw_job in raw_jobs:
        job_id = str(raw_job.get("id") or "").strip()
        if not job_id or job_id in seen_ids:
            continue
        if not _matches_department(raw_job, departments):
            continue
        if not _matches_location(raw_job, locations):
            continue

        seen_ids.add(job_id)
        filtered_jobs.append(raw_job)

    return filtered_jobs


async def _post_api_request(page, runtime_config, payload: dict) -> str:
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


async def _build_filtered_jobs_cache(page, runtime_config) -> list[dict]:
    cache_key = runtime_config.search_url
    if cache_key in _FILTERED_JOBS_CACHE:
        return _FILTERED_JOBS_CACHE[cache_key]

    locations, departments = _extract_search_filters(runtime_config.search_url)
    first_page_payload = await _post_api_request(page, runtime_config, _build_relaxed_api_payload(1))
    total_results = max(_extract_total_results(first_page_payload) or 0, 0)
    total_pages = max(1, math.ceil(total_results / RESULTS_PER_PAGE)) if total_results else 1

    filtered_jobs = []
    seen_ids = set()

    for raw_page_num in range(1, total_pages + 1):
        payload_text = (
            first_page_payload
            if raw_page_num == 1
            else await _post_api_request(page, runtime_config, _build_relaxed_api_payload(raw_page_num))
        )
        raw_jobs = _extract_raw_results(payload_text)
        page_jobs = _filter_raw_jobs(raw_jobs, locations, departments)
        for raw_job in page_jobs:
            job_id = str(raw_job.get("id") or "").strip()
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            filtered_jobs.append(raw_job)

    _FILTERED_JOBS_CACHE[cache_key] = filtered_jobs
    print(
        f"[{runtime_config.slug}] Filtered {len(filtered_jobs)} matching jobs "
        f"from {total_results or 'unknown'} raw Uber listings."
    )
    return filtered_jobs


def _build_filtered_results_payload(filtered_jobs: list[dict], page_num: int) -> str:
    start_index = max(0, page_num - 1) * RESULTS_PER_PAGE
    end_index = start_index + RESULTS_PER_PAGE
    page_jobs = filtered_jobs[start_index:end_index]
    payload = {
        "status": "success",
        "data": {
            "results": page_jobs,
            "totalResults": {
                "low": len(filtered_jobs),
                "high": 0,
                "unsigned": False,
            },
        },
    }
    return json.dumps(payload)


async def _fetch_search_page_html(page, runtime_config) -> str:
    print(f"[{runtime_config.slug}] Falling back to browser HTML scraping")

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            await page.goto(runtime_config.search_url, wait_until="domcontentloaded", timeout=30000)
            break
        except PlaywrightTimeout:
            if attempt == max_attempts:
                raise
            await page.wait_for_timeout(1500)

    for selector in runtime_config.definition.wait_selectors:
        try:
            await page.wait_for_selector(selector, timeout=8000)
            break
        except PlaywrightTimeout:
            continue

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    return await page.content()


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = _page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading API page {page_num}: {UBER_API_URL}")

    cached_jobs = _FILTERED_JOBS_CACHE.get(runtime_config.search_url)
    if cached_jobs is not None:
        return _build_filtered_results_payload(cached_jobs, page_num)

    filtered_payload = await _post_api_request(
        page,
        runtime_config,
        _build_api_payload(runtime_config.search_url, page_num),
    )
    filtered_count = _extract_result_count(filtered_payload)
    if filtered_count and filtered_count > 0:
        return filtered_payload

    print(
        f"[{runtime_config.slug}] Filtered API query returned no jobs. "
        "Retrying with relaxed query plus client-side filtering."
    )
    filtered_jobs = await _build_filtered_jobs_cache(page, runtime_config)
    if filtered_jobs:
        return _build_filtered_results_payload(filtered_jobs, page_num)

    return await _fetch_search_page_html(page, runtime_config)


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
    allow_empty_results=True,
)