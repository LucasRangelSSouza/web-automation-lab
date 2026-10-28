#!/usr/bin/env bash
# Test script for: Playwright (tier T2, time limit 900 s)
# Run by src/sandbox/sandbox_suite.py inside an isolated HOME on a small CPU instance.
pip install -q playwright && playwright install --with-deps chromium >/dev/null 2>&1
python - <<'PY'
import time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); ts=[]
    for i in range(5):
        t0=time.time(); pg.goto("https://example.com"); pg.title(); ts.append(time.time()-t0)
    print("METRIC goto_ms_median=%d"%(sorted(ts)[2]*1000)); b.close()
PY
