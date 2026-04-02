#!/usr/bin/env python3
"""Generic scraper runner for a single company.

Example:
  python scraper.py --company apple --mode regular
"""

import argparse
import asyncio
import sys
import time

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from companies import get_adapter
from notifier import send_error, send_job_alert, send_summary, verify_bot
from parser import get_total_results
from state import filter_new_jobs, is_excluded_role, should_exclude_title


async def scrape_page(page, url: str, page_load_timeout: int, job_card_timeout: int) -> str:
    print(f"[scraper] Loading: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=page_load_timeout)

    selectors = ["text=Role Number", "text=Weekly Hours", "h2", "li"]

    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=job_card_timeout)
            print(f"[scraper] Results detected via selector: {selector}")
            break
        except PlaywrightTimeout:
            continue
    else:
        print("[scraper] Result selectors did not appear in time; capturing page anyway.")

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1200)
    return await page.content()


async def run_scraper(company_name: str, mode: str = "regular") -> None:
    adapter = get_adapter(company_name)
    max_pages = adapter.full_max_pages if mode == "full" else adapter.max_pages

    start_time = time.time()
    print("=" * 60)
    print(f"[scraper] {company_name} notifier starting (mode={mode})")
    print("=" * 60)

    bot_ok = await verify_bot()
    if not bot_ok:
        print("[scraper] WARNING: Telegram bot verification failed. Notifications may not work.")

    all_jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36",
            ),
            viewport={"width": 1440, "height": 1200},
        )
        page = await context.new_page()

        try:
            page_limit = max_pages
            for page_num in range(1, page_limit + 1):
                url = adapter.build_search_url(page_num)
                try:
                    html = await scrape_page(page, url, 15000, 8000)
                    raw_jobs = adapter.extract_jobs(html)
                    jobs = [adapter.normalize_job(job) for job in raw_jobs]

                    print(f"[scraper] Page {page_num}: found {len(jobs)} jobs")

                    if page_num == 1:
                        total = get_total_results(html)
                        if total and jobs:
                            inferred_page_count = max(1, (total + len(jobs) - 1) // len(jobs))
                            page_limit = min(max_pages, inferred_page_count)
                            print(f"[scraper] Total matching jobs on site: {total}")
                            print(f"[scraper] Scraping up to {page_limit} page(s) this run")

                    if not jobs:
                        print(f"[scraper] No jobs found on page {page_num}; stopping.")
                        break

                    all_jobs.extend(jobs)

                    if page_num >= page_limit:
                        break

                    await page.wait_for_timeout(500)

                except PlaywrightTimeout as exc:
                    print(f"[scraper] Timeout on page {page_num}: {exc}")
                    break
                except Exception as exc:
                    print(f"[scraper] Error on page {page_num}: {exc}")
                    break
        finally:
            await browser.close()

    if not all_jobs:
        print("[scraper] No jobs were extracted from any page.")
        await send_error("No jobs were extracted. The page structure may have changed.")
        sys.exit(1)

    unique_jobs = []
    seen_keys = set()
    for job in all_jobs:
        key = job.get("key") or job.get("role_number")
        if not key:
            continue
        if key not in seen_keys:
            seen_keys.add(key)
            unique_jobs.append(job)

    print(f"\n[scraper] Total unique jobs scraped: {len(unique_jobs)}")

    new_jobs = filter_new_jobs(unique_jobs)
    print(f"[scraper] New jobs (not seen before): {len(new_jobs)}")

    before = len(new_jobs)
    new_jobs = [job for job in new_jobs if not should_exclude_title(job.get("title", ""))]
    new_jobs = [job for job in new_jobs if not is_excluded_role(job.get("title", ""))]
    excluded = before - len(new_jobs)
    if excluded:
        print(f"[scraper] Excluded {excluded} job(s) by title filter")

    if new_jobs:
        print(f"\n[scraper] Sending {len(new_jobs)} Telegram notifications...")
        for index, job in enumerate(new_jobs, 1):
            print(f"  [{index}/{len(new_jobs)}] {job.get('title', 'unknown')}")
            success = await send_job_alert(job)
            if not success:
                print("    [scraper] Failed to send notification")
            if index < len(new_jobs):
                await asyncio.sleep(0.5)
        await send_summary(len(new_jobs), len(unique_jobs))
    else:
        print("[scraper] No new jobs to notify.")

    print(f"[scraper] Run completed in {time.time() - start_time:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Run company job scraper")
    parser.add_argument("--company", default="apple", help="company adapter name (apple, ...)")
    parser.add_argument("--mode", default="regular", choices=["regular", "full"], help="regular or full scrape")
    args = parser.parse_args()

    asyncio.run(run_scraper(args.company, args.mode))


if __name__ == "__main__":
    main()

    elapsed = time.time() - start_time
    print(f"\n[scraper] Run completed in {elapsed:.1f}s")
    print(f"[scraper] Seen jobs database: {len(load_seen_jobs())} entries")


def main() -> None:
    asyncio.run(run_scraper())


if __name__ == "__main__":
    main()
