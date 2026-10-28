#!/usr/bin/env bash
# Test script for: Crawl4AI (tier T2, time limit 1200 s)
# Run by src/sandbox/sandbox_suite.py inside an isolated HOME on a small CPU instance.
pip install -q crawl4ai && crawl4ai-setup >/dev/null 2>&1
python - <<'PY'
import asyncio,time
from crawl4ai import AsyncWebCrawler
async def main():
    async with AsyncWebCrawler() as c:
        for u in ("https://example.com","https://docs.python.org/3/library/json.html"):
            t0=time.time(); r=await c.arun(url=u); dt=time.time()-t0
            print("METRIC %s_s=%.2f md_chars=%d"%(u.split('/')[2].replace('.','_'),dt,len(r.markdown or "")))
asyncio.run(main())
PY
