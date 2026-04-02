#!/usr/bin/env python3
"""Run scrapers for multiple companies."""

import argparse
import asyncio

from scraper import run_scraper


def main():
    parser = argparse.ArgumentParser(description="Run all company scrapers")
    parser.add_argument("--companies", default="apple", help="Comma-separated company names")
    parser.add_argument("--mode", default="regular", choices=["regular", "full"], help="regular or full")
    args = parser.parse_args()

    company_list = [c.strip() for c in args.companies.split(",") if c.strip()]

    async def run_all():
        for company in company_list:
            await run_scraper(company, args.mode)

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
