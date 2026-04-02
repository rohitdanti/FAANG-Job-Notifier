from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from companies.base import CompanyDefinition
from goldman_sachs_parser import get_total_pages, get_total_results, parse_jobs

GOLDMAN_SACHS_SEARCH_URL = (
    "https://higher.gs.com/results"
    "?EXPERIENCE_LEVEL=Analyst|Associate"
    "&JOB_FUNCTION=Software%20Engineering"
    "&LOCATION=Albany|New%20York|Atlanta|Boston|Chicago|Dallas|Houston|Irving"
    "|Richardson|Denver|Detroit|Troy|Draper|Salt%20Lake%20City|Jersey%20City"
    "|Morristown|Los%20Angeles|Menlo%20Park|Newport%20Beach|San%20Francisco"
    "|Miami|West%20Palm%20Beach|Minneapolis|Philadelphia|Pittsburgh|Seattle"
    "|Washington|Wilmington"
    "&page=1"
    "&sort=POSTED_DATE"
)

EXCLUDED_ROLE_KEYWORDS = (
    "vice president",
    "executive director",
    "managing director",
    "partner",
)


def build_search_url(search_url: str, page_num: int) -> str:
    parsed = urlsplit(search_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["page"] = str(page_num)
    params.setdefault("sort", "POSTED_DATE")
    return urlunsplit(parsed._replace(query=urlencode(params, doseq=True)))


COMPANY = CompanyDefinition(
    slug="goldman-sachs",
    display_name="Goldman Sachs",
    default_search_url=GOLDMAN_SACHS_SEARCH_URL,
    default_max_pages=2,
    default_full_scrape_max_pages=30,
    wait_selectors=(
        "text=Showing",
        "text=matches",
        "a[href*='/roles/']",
    ),
    build_search_url=build_search_url,
    parse_jobs=parse_jobs,
    get_total_pages=get_total_pages,
    get_total_results=get_total_results,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
)