#!/bin/bash
cd /workspace/eco
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq python3-pip python3-venv >/dev/null 2>&1
python3 -m pip install -q psutil --break-system-packages >/dev/null 2>&1 || python3 -m pip install -q psutil >/dev/null 2>&1
python3 sandbox_suite.py > out/sandbox_runner.log 2>&1
echo SCRIPT_DONE
