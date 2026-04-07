from companies.amazon import COMPANY as AMAZON
from companies.apple import COMPANY as APPLE
from companies.base import CompanyDefinition
from companies.goldman_sachs import COMPANY as GOLDMAN_SACHS
from companies.google import COMPANY as GOOGLE
from companies.lyft import COMPANY as LYFT
from companies.meta import COMPANY as META
from companies.salesforce import COMPANY as SALESFORCE
from companies.uber import COMPANY as UBER

COMPANIES: dict[str, CompanyDefinition] = {
    AMAZON.slug: AMAZON,
    APPLE.slug: APPLE,
    GOLDMAN_SACHS.slug: GOLDMAN_SACHS,
    GOOGLE.slug: GOOGLE,
    LYFT.slug: LYFT,
    META.slug: META,
    SALESFORCE.slug: SALESFORCE,
    UBER.slug: UBER,
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