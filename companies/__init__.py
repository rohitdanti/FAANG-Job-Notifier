from importlib import import_module


def get_adapter(company_name: str):
    """Load and return the adapter for a given company."""
    try:
        module = import_module(f"companies.{company_name}")
        return getattr(module, "adapter")
    except (ImportError, AttributeError) as exc:
        raise ValueError(f"No adapter found for company '{company_name}': {exc}")
