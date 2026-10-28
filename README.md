# Web automation and scraping lab

Playwright, Crawl4AI and Obscura exercised against real pages (page load times, extracted markdown size).

Author: Lucas Rangel. All numbers below come from `evidence/results.json` (measured runs on rented Vast.ai GPUs, Oct 2026). Rows with failed or install-only status are not included. Every row is a real run on a shared marketplace host: values are single-session medians, outliers are kept (not filtered), and a different host of the same GPU model can differ noticeably.

## Conclusion

Playwright loaded example.com in 24 ms (median of 5), Obscura fetched it in 290 ms and Crawl4AI crawled it to markdown in 0.71 s; Crawl4AI took 0.98 s for a documentation page that became 46,073 characters of markdown. The three numbers measure different things on a trivial page and are not a ranking of the tools.

## Measured rows

| tool | tier | wall (s) | peak RSS (MB) | metrics |
|---|---|---|---|---|
| Playwright | T2 | 70.9 | 532 | goto_ms_median=24.0 |
| Crawl4AI | T2 | 139.7 | 722 | example_com_s=0.71; md_chars=46073.0; docs_python_org_s=0.98 |
| Obscura | T2 | 7.5 | 47 | fetch_ms_median=290.0 |

## What this cost

These were CPU-only runs on small rented instances (cents per run).

Whole campaign: US$ 50.79 (about R$ 249), shared by all repositories of this series. Rental share of the GPUs used in this repo:

| GPU | rentals | hours | rental cost (USD) |
|---|---|---|---|

Rental figures are hourly price x time of each rented instance; marketplace download fees and idle time are in the campaign total, not in this table.

## Reproduce

`bash scripts/run.sh` documents the exact commands used on the rented instance (Ubuntu, CUDA, Python venv). Evidence files are the unmodified measured rows (host location and reliability removed).
