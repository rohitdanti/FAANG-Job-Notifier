#!/usr/bin/env python3
"""
One-time script to seed seen_jobs.json for one or more configured companies.
Run this locally once if you want future notifier runs to alert only on newly posted roles.
"""

import argparse
import asyncio
import time

from playwright.async_api import async_playwright

import config
from runner import collect_jobs
from state import replace_seen_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the seen-job state for configured companies.")
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="Company slug to seed. Repeat or pass a comma-separated list.",
    )
    return parser.parse_args()


async def scrape_all_jobs(selected_companies: list[str] | None = None) -> None:
    requested_companies = config.get_selected_company_slugs(selected_companies)

    print("=" * 60)
    print("[full-scrape] Seeding seen-job state")
    print(f"[full-scrape] Companies: {', '.join(requested_companies)}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for slug in requested_companies:
                runtime_config = config.get_company_runtime(slug)
                unique_jobs = await collect_jobs(browser, runtime_config, runtime_config.full_scrape_max_pages)
                replace_seen_jobs(runtime_config.slug, unique_jobs)
                print(
                    f"[full-scrape] Saved {len(unique_jobs)} entries for "
                    f"{runtime_config.display_name} to {config.SEEN_JOBS_DIR}"
                )
        finally:
            await browser.close()

    print("[full-scrape] Done.")


if __name__ == "__main__":
    started_at = time.time()
    args = parse_args()
    asyncio.run(scrape_all_jobs(args.companies))
    print(f"[full-scrape] Completed in {time.time() - started_at:.1f}s")
