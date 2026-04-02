# Apple Jobs Notifier

Monitors Apple’s jobs search for newly posted U.S. software-oriented roles and sends Telegram alerts when matching openings appear.

The default search is already wired to your Apple filter URL:

[Apple Jobs Search](https://jobs.apple.com/en-us/search?sort=newest&location=united-states-USA&team=apps-and-frameworks-SFTWR-AF+cloud-and-infrastructure-SFTWR-CLD+core-operating-systems-SFTWR-COS+devops-and-site-reliability-SFTWR-DSR+engineering-project-management-SFTWR-EPM+information-systems-and-technology-SFTWR-ISTECH+machine-learning-and-ai-SFTWR-MCHLN+security-and-privacy-SFTWR-SEC+software-quality-automation-and-tools-SFTWR-SQAT+wireless-software-SFTWR-WSFT)

## How it works

```text
Run scraper
  |
  |- Launch headless Chromium with Playwright
  |- Open the Apple jobs search results page
  |- Parse visible result cards and extract role metadata
  |- Compare role IDs against seen_jobs.json
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

Optional overrides:

```bash
APPLE_SEARCH_URL="https://jobs.apple.com/en-us/search?..."
MAX_PAGES=10
PAGE_LOAD_TIMEOUT=15000
JOB_CARD_TIMEOUT=8000
```

## Seed the state file

If you do not want the first real run to notify on every currently visible Apple posting, seed the state first:

```bash
python full_scrape.py
```

That will populate [seen_jobs.json](/Users/rohith/Downloads/ms-careers-bot-master/seen_jobs.json) with the jobs currently returned by the configured Apple search.

## GitHub Actions

The workflow in [.github/workflows/scrape.yml](/Users/rohith/Downloads/ms-careers-bot-master/.github/workflows/scrape.yml) runs the scraper and commits an updated [seen_jobs.json](/Users/rohith/Downloads/ms-careers-bot-master/seen_jobs.json). Add these repository secrets before enabling it:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

You can trigger it manually from GitHub Actions, or attach your own scheduler to call the workflow.

## Project structure

```text
scraper.py                  Main notifier entry point
full_scrape.py              One-time state seeding script
parser.py                   Apple search result parsing
config.py                   Search URL, timeouts, and filters
notifier.py                 Telegram integration
state.py                    Seen-job persistence
seen_jobs.json              Stored role IDs already observed
.github/workflows/scrape.yml  Automation workflow
```

## Notes

- Apple search pagination uses `page=` query params, so the scraper walks numbered result pages instead of Microsoft-style offsets.
- Result parsing is based on visible card text such as `Role Number`, `Location`, and `Weekly Hours`, which makes it resilient to moderate markup changes.
- Senior and management roles are filtered by title keywords in [config.py](/Users/rohith/Downloads/ms-careers-bot-master/config.py). Adjust them if you want broader coverage.
