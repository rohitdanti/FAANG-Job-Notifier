from urllib.parse import urlsplit, urlunsplit

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


async def fetch_page_html(page, runtime_config, url: str) -> str:
    parsed = urlsplit(url)
    base_url = urlunsplit(parsed._replace(fragment=""))
    page_num = _page_num_from_url(url)

    print(f"[{runtime_config.slug}] Loading: {base_url} (page {page_num})")
    await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)

    for selector in runtime_config.definition.wait_selectors:
        try:
            await page.wait_for_selector(selector, timeout=8000)
            print(f"[{runtime_config.slug}] Results detected via selector: {selector}")
            break
        except Exception:
            continue

    if page_num > 1:
        show_more_button = page.get_by_role("button", name="Show more openings")
        for _ in range(2, page_num + 1):
            try:
                await show_more_button.wait_for(state="visible", timeout=8000)
            except PlaywrightTimeout as exc:
                raise RuntimeError(f"Uber results page did not expose page {page_num} via Show more openings") from exc

            prior_link_count = await page.locator('a[href*="/careers/list/"]').count()
            await show_more_button.click()
            await page.wait_for_timeout(1500)
            try:
                await page.wait_for_function(
                    "previousCount => document.querySelectorAll('a[href*=\"/careers/list/\"]').length > previousCount",
                    arg=prior_link_count,
                    timeout=10000,
                )
            except PlaywrightTimeout:
                pass

    await page.wait_for_timeout(500)
    return await page.content()


COMPANY = CompanyDefinition(
    slug="uber",
    display_name="Uber",
    default_search_url=UBER_SEARCH_URL,
    default_max_pages=4,
    default_full_scrape_max_pages=200,
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