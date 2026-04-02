from .base import CompanyAdapter
from parser import parse_jobs
import config


class AppleAdapter(CompanyAdapter):
    name = "apple"
    max_pages = int(config.MAX_PAGES)
    full_max_pages = int(config.FULL_SCRAPE_MAX_PAGES)

    def build_search_url(self, page_num: int) -> str:
        return config.build_search_url(page_num)

    def extract_jobs(self, html: str) -> list[dict]:
        return parse_jobs(html)


adapter = AppleAdapter()
