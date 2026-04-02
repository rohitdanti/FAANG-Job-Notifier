from dataclasses import dataclass
from typing import Callable

Job = dict[str, str]
PageMetricExtractor = Callable[[str], int | None]
ParseJobs = Callable[[str], list[Job]]
BuildSearchUrl = Callable[[str, int], str]


@dataclass(frozen=True)
class CompanyDefinition:
    slug: str
    display_name: str
    default_search_url: str
    default_max_pages: int
    default_full_scrape_max_pages: int
    wait_selectors: tuple[str, ...]
    build_search_url: BuildSearchUrl
    parse_jobs: ParseJobs
    get_total_pages: PageMetricExtractor
    get_total_results: PageMetricExtractor
    excluded_role_keywords: tuple[str, ...] = ()
    excluded_title_phrases: tuple[str, ...] = ()