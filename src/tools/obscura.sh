#!/usr/bin/env bash
# Test script for: Obscura (tier T2, time limit 600 s)
# Run by src/sandbox/sandbox_suite.py inside an isolated HOME on a small CPU instance.
curl -sLO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz && tar xzf obscura-x86_64-linux.tar.gz && chmod +x obscura
python - <<'PY'
import subprocess,time
ts=[]
for i in range(5):
    t0=time.time(); o=subprocess.run(["./obscura","fetch","https://example.com","--eval","document.title"],capture_output=True,text=True,timeout=60); ts.append(time.time()-t0)
print("OUT",o.stdout.strip()[:80],o.stderr.strip()[:120])
print("METRIC fetch_ms_median=%d"%(sorted(ts)[2]*1000))
PY
