# Multi-Company Jobs Notifier

Scrapes job boards for one or more companies, tracks previously seen openings per company, and sends Telegram alerts when new matches appear.

The project is now structured around company adapters. Apple, Amazon, Goldman Sachs, and Salesforce are bundled, and additional companies can be added without creating a new repo.

## How it works

```text
Run scraper
  |
  |- Launch headless Chromium with Playwright
  |- Loop through configured company adapters
  |- Open each company's configured search results page
  |- Parse visible result cards and extract normalized job metadata
  |- Compare each company's job IDs against its own file in seen_jobs/
  |- Send Telegram alerts for newly seen jobs
  '- Persist updated state for the next run
```

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the bot token
4. Start a chat with your bot
5. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy your chat ID

### 2. Run locally

```bash
cd /path/to/this/repo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
python scraper.py
```

Fill in `.env` with:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Optional shared overrides:

```bash
COMPANIES=apple,amazon,goldman-sachs,salesforce
PAGE_LOAD_TIMEOUT=15000
JOB_CARD_TIMEOUT=8000
MAX_SEEN_JOBS=3000
```

Per-company overrides follow the pattern `<COMPANY>_<SETTING>`. For Apple:

```bash
APPLE_SEARCH_URL="https://jobs.apple.com/en-us/search?location=united-states-USA&team=apps-and-frameworks-SFTWR-AF+cloud-and-infrastructure-SFTWR-CLD+core-operating-systems-SFTWR-COS+devops-and-site-reliability-SFTWR-DSR+engineering-project-management-SFTWR-EPM+information-systems-and-technology-SFTWR-ISTECH+machine-learning-and-ai-SFTWR-MCHLN+security-and-privacy-SFTWR-SEC+software-quality-automation-and-tools-SFTWR-SQAT+wireless-software-SFTWR-WSFT"
APPLE_MAX_PAGES=2
APPLE_FULL_SCRAPE_MAX_PAGES=90
```

For Amazon:

```bash
AMAZON_SEARCH_URL="https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=recent&category%5B%5D=software-development&job_type%5B%5D=Full-Time&country%5B%5D=USA&distanceType=Mi&radius=24km&industry_experience=one_to_three_years&is_manager%5B%5D=0&latitude=&longitude=&loc_group_id=&loc_query=&base_query=&city=&country=&region=&county=&query_options=&"
AMAZON_MAX_PAGES=4
AMAZON_FULL_SCRAPE_MAX_PAGES=40
```

For Goldman Sachs:

```bash
GOLDMAN_SACHS_SEARCH_URL="https://higher.gs.com/results?EXPERIENCE_LEVEL=Analyst|Associate&JOB_FUNCTION=Software%20Engineering&LOCATION=Albany|New%20York|Atlanta|Boston|Chicago|Dallas|Houston|Irving|Richardson|Denver|Detroit|Troy|Draper|Salt%20Lake%20City|Jersey%20City|Morristown|Los%20Angeles|Menlo%20Park|Newport%20Beach|San%20Francisco|Miami|West%20Palm%20Beach|Minneapolis|Philadelphia|Pittsburgh|Seattle|Washington|Wilmington&page=1&sort=POSTED_DATE"
GOLDMAN_SACHS_MAX_PAGES=2
GOLDMAN_SACHS_FULL_SCRAPE_MAX_PAGES=30
```

For Salesforce:

```bash
SALESFORCE_SEARCH_URL="https://salesforce.wd12.myworkdayjobs.com/en-US/external_career_site?redirect=/en-US/external_career_site/userHome&CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended=bc33aa3152ec42d4995f4791a106ed09&timeType=0e28126347c3100fe3b402cf26290000&jobFamilyGroup=14fa3452ec7c1011f90d0002a2100000&workerSubType=3a910852b2c31010f48d2bbc8b020000"
SALESFORCE_MAX_PAGES=2
SALESFORCE_FULL_SCRAPE_MAX_PAGES=6
```

Run a subset of companies from the CLI:

```bash
python scraper.py --company apple
python full_scrape.py --company apple
```

Once you add more adapters, you can pass a comma-separated list such as `--company apple,netflix`.

## Seed the state file

If you do not want the first real run to notify on every currently visible posting, seed the state first:

```bash
python full_scrape.py
```

That will populate one file per company under `seen_jobs/`, for example `seen_jobs/apple.json` and `seen_jobs/amazon.json`.

## Company adapters

Each company adapter is responsible for:

- building paginated search URLs
- declaring which selectors indicate a loaded results page
- parsing the rendered HTML into normalized job records
- reporting total results or page counts when available
- providing company-specific title filters

The shared runner handles browser setup, pagination, deduplication, state persistence, and Telegram notifications.

To add a new company, create a module under `companies/` and register it in `companies/registry.py`.

Each parsed job should normalize into this shape:

```python
{
  "key": "stable-company-specific-id",
  "job_id": "display-id-if-different",
  "title": "Software Engineer",
  "team": "Infrastructure",
  "location": "Seattle, WA",
  "posted": "Apr 1, 2026",
  "description": "Short preview",
  "url": "https://careers.example.com/jobs/123",
}
```

## GitHub Actions

The included workflows run either the notifier or the full-state seed and commit the updated files under `seen_jobs/`. Add these repository secrets before enabling them:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Both workflows accept a comma-separated `companies` input so you can choose which adapters to run.

## Project structure

```text
scraper.py                  Main notifier entry point
full_scrape.py              One-time state seeding script
config.py                   Shared runtime config and company selection
runner.py                   Shared Playwright scraping loop
parser.py                   Apple search result parsing
notifier.py                 Telegram integration
state.py                    Multi-company seen-job persistence
companies/                  Company adapter registry and implementations
amazon_parser.py            Amazon search result parsing
goldman_sachs_parser.py     Goldman Sachs search result parsing
seen_jobs/                  One state file per company
.github/workflows/scrape.yml  Automation workflow
```

## Notes

- The repository now supports multiple companies in a single run, with Apple, Amazon, Goldman Sachs, and Salesforce bundled today.
- State is stored as separate files per company under `seen_jobs/`.
- Apple search pagination still uses the `page=` query param and Apple parsing remains based on visible card text such as `Role Number`, `Location`, and `Weekly Hours`.
- Amazon uses paginated search offsets and extracts result cards via `/en/jobs/<id>/...` links plus nearby `Job ID` metadata.
- Goldman Sachs uses `page=` pagination and parses `/roles/<id>` result cards plus the `Showing ... of ... matches` result count.
