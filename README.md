# AO3 Pulse Sync

This folder is the external collection layer for the AO3 Pulse dashboard.

## What it does

- Uses the unofficial `ao3_api` Python package.
- Derives the numeric work ID from `AO3_WORK_URL`.
- Makes one fresh metadata request with `Work.reload(False)`.
- Does not load chapter text or crawl comment pages.
- Appends public metadata to `ao3-snapshots.json`.
- Preserves the six Aug. 3–22 historical observations.
- Omits private work-subscription and user-subscription fields on automated rows; historical manual observations remain preserved.
- Runs every 12 hours through GitHub Actions and also supports manual runs.

## One-time setup

1. Create a GitHub repository and put these files at its root.
2. In the repository, open **Settings → Secrets and variables → Actions → Variables**.
3. Create a repository variable named `AO3_WORK_URL`.
4. Set it to the normal AO3 work URL for *The Crew of Dracule Mihawk: A Cross Guild Romance*.
5. In **Actions**, run **AO3 Pulse Sync** manually once.
6. Confirm `ao3-snapshots.json` gains a new row whose `source` is `ao3_api`.
7. Copy the raw GitHub URL for the JSON file:
   `https://raw.githubusercontent.com/YOUR-USER/YOUR-REPO/main/ao3-snapshots.json`
8. Give that raw URL to ChatGPT so the AO3 Pulse dashboard can be pointed at the live feed.

The dashboard already falls back to its historical seed data if the feed is missing or unavailable.

## Why there are no AO3 credentials

The collector uses `AO3.GuestSession()`. This keeps the job limited to public metadata and avoids storing your AO3 password. Private subscription totals remain manual.
