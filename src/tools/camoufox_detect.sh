#!/usr/bin/env bash
# Test script for: Camofox browser (tier T2, time limit 1500 s)
# Run by src/sandbox/sandbox_suite.py inside an isolated HOME on a small CPU instance.
pip install -q camoufox playwright >/dev/null 2>&1; python -m camoufox fetch >/dev/null 2>&1; python -m playwright install --with-deps chromium >/dev/null 2>&1
python - <<'PY'
import re
from camoufox.sync_api import Camoufox
with Camoufox(headless=True) as b:
    p=b.new_page(); p.goto("https://bot.sannysoft.com/",timeout=60000); p.wait_for_timeout(4000)
    t=p.inner_text("body")
print("METRIC detector_page_chars=%d failed_mentions=%d"%(len(t),len(re.findall(r'(?i)failed',t))))
print(t[:300].replace("\n"," | "))
PY
python - <<'PY'
from playwright.sync_api import sync_playwright
import re
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto("https://bot.sannysoft.com/",timeout=60000); pg.wait_for_timeout(4000); t=pg.inner_text("body")
print("METRIC baseline_playwright_failed_mentions=%d"%len(re.findall(r'(?i)failed',t)))
PY
