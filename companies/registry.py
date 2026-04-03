from companies.amazon import COMPANY as AMAZON
from companies.apple import COMPANY as APPLE
from companies.base import CompanyDefinition
from companies.goldman_sachs import COMPANY as GOLDMAN_SACHS
from companies.salesforce import COMPANY as SALESFORCE

COMPANIES: dict[str, CompanyDefinition] = {
    AMAZON.slug: AMAZON,
    APPLE.slug: APPLE,
    GOLDMAN_SACHS.slug: GOLDMAN_SACHS,
    SALESFORCE.slug: SALESFORCE,
}


def get_company(slug: str) -> CompanyDefinition:
    normalized_slug = slug.strip().lower()
    try:
        return COMPANIES[normalized_slug]
    except KeyError as exc:
        supported = ", ".join(sorted(COMPANIES))
        raise ValueError(f"Unsupported company '{slug}'. Supported companies: {supported}") from exc


def list_companies() -> list[str]:
    return sorted(COMPANIES)