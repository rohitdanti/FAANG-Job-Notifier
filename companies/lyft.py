from companies.base import CompanyDefinition
from lyft_parser import get_total_pages, get_total_results, parse_jobs

LYFT_SEARCH_URL = (
    "https://app.careerpuck.com/job-board/lyft"
    "?locationId=cYcPOWC-"
    "&departmentId=qcV0nZaT"
)

EXCLUDED_ROLE_KEYWORDS = (
    "engineering manager",
    "gestionnaire en ingénierie",
    "head of",
    "senior",
    "staff",
)


def build_search_url(search_url: str, page_num: int) -> str:
    return search_url


COMPANY = CompanyDefinition(
    slug="lyft",
    display_name="Lyft",
    default_search_url=LYFT_SEARCH_URL,
    default_max_pages=1,
    default_full_scrape_max_pages=1,
    wait_selectors=(
        'a[href*="/job-board/lyft/job/"]',
        'text=job postings found',
        'text=Software Engineering',
    ),
    build_search_url=build_search_url,
    parse_jobs=parse_jobs,
    get_total_pages=get_total_pages,
    get_total_results=get_total_results,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
)
