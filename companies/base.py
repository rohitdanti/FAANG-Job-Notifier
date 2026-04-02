from abc import ABC, abstractmethod


class CompanyAdapter(ABC):
    """Adapter interface for a single company job index search site."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def max_pages(self) -> int:
        ...

    @property
    @abstractmethod
    def full_max_pages(self) -> int:
        ...

    @abstractmethod
    def build_search_url(self, page_num: int) -> str:
        ...

    @abstractmethod
    def extract_jobs(self, html: str) -> list[dict]:
        ...

    def normalize_job(self, job: dict) -> dict:
        """Optional normalization from raw parsed job to canonical fields."""
        return job
