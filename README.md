# FAANG+ Jobs Notifier

Scrapes job boards for FAANG+ companies, tracks previously seen openings per company, and sends Telegram alerts when new matches appear.
The workflow is set to run every 10 minutes, ensuring that I don’t miss out on applying to new job opportunities.

The project is now structured around company adapters. Apple, Amazon, Goldman Sachs, Google, Meta, Salesforce, and Uber are bundled, and additional companies can be added without creating a new repo.

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
