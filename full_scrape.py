#!/usr/bin/env python3
"""
One-time script: scrape Apple search results and seed seen_jobs.json.
Run this locally once if you want future notifier runs to alert only on new roles.
"""

import asyncio
import json
import time

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

import config
from parser import get_total_results, get_total_pages, parse_jobs

SEEN_JOBS_FILE = config.SEEN_JOBS_FILE


async def scrape_all_jobs() -> None:
    print("=" * 60)
    print("[full-scrape] Scraping Apple search results")
    print(f"[full-scrape] URL: {config.SEARCH_URL}")
    print("=" * 60)

    with open(SEEN_JOBS_FILE, "w") as handle:
        json.dump({}, handle)
    print("[full-scrape] Reset seen_jobs.json")

    all_jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 1200},
        )
        page = await context.new_page()

        first_url = config.build_search_url(1)
        print(f"\n[full-scrape] Loading page 1: {first_url}")
        await page.goto(first_url, wait_until="domcontentloaded", timeout=config.PAGE_LOAD_TIMEOUT)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)
        html = await page.content()
        jobs = parse_jobs(html)
        all_jobs.extend(jobs)

        total_pages_from_ui = get_total_pages(html)
        if total_pages_from_ui:
            total_pages = min(config.FULL_SCRAPE_MAX_PAGES, max(1, total_pages_from_ui))
            print(f"[full-scrape] Total pages from UI: {total_pages_from_ui}")
        else:
            total = get_total_results(html)
            if total and jobs:
                total_pages = min(config.FULL_SCRAPE_MAX_PAGES, max(1, (total + len(jobs) - 1) // len(jobs)))
                print(f"[full-scrape] Total jobs on site: {total}")
            else:
                total_pages = config.FULL_SCRAPE_MAX_PAGES
                print("[full-scrape] Could not infer total page count; using FULL_SCRAPE_MAX_PAGES safety cap")

        print(f"[full-scrape] Page 1: {len(jobs)} jobs")

        for page_num in range(2, total_pages + 1):
            url = config.build_search_url(page_num)
            print(f"[full-scrape] Page {page_num}/{total_pages}...", end=" ", flush=True)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=config.PAGE_LOAD_TIMEOUT)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)
                html = await page.content()
                jobs = parse_jobs(html)
                print(f"{len(jobs)} jobs")

                if not jobs:
                    print("[full-scrape] No jobs on this page; stopping.")
                    break

                all_jobs.extend(jobs)
                await page.wait_for_timeout(500)
            except Exception as exc:
                print(f"ERROR: {exc}")
                break

        await browser.close()

    unique_jobs = []
    seen_keys = set()
    for job in all_jobs:
        if job["key"] not in seen_keys:
            seen_keys.add(job["key"])
            unique_jobs.append(job)

    print(f"\n[full-scrape] Total raw jobs scraped: {len(all_jobs)}")
    print(f"[full-scrape] Unique jobs after dedup: {len(unique_jobs)}")

    seen = {}
    for job in unique_jobs:
        seen[job["key"]] = {
            "first_seen": time.time(),
            "posted": job.get("posted", ""),
            "title": job.get("title", ""),
            "job_id": job["role_number"],
        }

    with open(SEEN_JOBS_FILE, "w") as handle:
        json.dump(seen, handle, indent=2)

    print(f"[full-scrape] Saved {len(seen)} entries to {SEEN_JOBS_FILE}")
    print("[full-scrape] Done.")


if __name__ == "__main__":
    asyncio.run(scrape_all_jobs())
