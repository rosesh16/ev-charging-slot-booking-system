#!/usr/bin/env python3
"""
Docker Registry Readiness Check
Polls http://127.0.0.1:5000/v2/_catalog until healthy or timeout expires.
"""

import sys
import time
import urllib.error
import urllib.request

REGISTRY_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/v2/_catalog"
TIMEOUT_SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 15

deadline = time.time() + TIMEOUT_SECONDS
last_err = None

print(f"Checking Docker registry readiness at {REGISTRY_URL} (timeout: {TIMEOUT_SECONDS}s)...")
while time.time() < deadline:
    try:
        req = urllib.request.Request(REGISTRY_URL, headers={"User-Agent": "Jenkins-Registry-Check"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print(f"[READY] Docker registry is responding with HTTP 200.")
                sys.exit(0)
    except Exception as e:
        last_err = e
        time.sleep(1)

print(
    f"[ERROR] Docker registry at {REGISTRY_URL} failed readiness check after {TIMEOUT_SECONDS}s: {last_err}",
    file=sys.stderr,
)
sys.exit(1)
