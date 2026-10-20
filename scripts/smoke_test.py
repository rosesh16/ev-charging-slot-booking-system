#!/usr/bin/env python3
"""
Production Deployment Smoke Test Script
EV Charging Slot Booking System

Validates:
1. Frontend response (GET / -> 200 OK, HTML, contains React root element)
2. Static assets (dynamically parsed JS and CSS bundles -> 200 OK, proper MIME types)
3. SPA routing fallback (GET /stations -> 200 OK, React HTML, no API rewrite)
4. Health endpoint (GET /health/ -> 200 OK, status: healthy, database: connected)
5. Backend API routing (GET /api/stations/ & GET /api/chargers/ -> 200 OK, JSON list)
6. API error handling (GET /api/nonexistent-endpoint/ -> 404 Not Found, not SPA fallback)
7. Database-backed operation (database connection verified via health check and API)
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def make_request(url, headers=None, method="GET"):
    """Execute an HTTP request and return (status_code, headers_dict, body_bytes)."""
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            res_headers = dict(response.headers)
            body = response.read()
            return status_code, res_headers, body
    except urllib.error.HTTPError as e:
        res_headers = dict(e.headers)
        body = e.read()
        return e.code, res_headers, body
    except Exception as e:
        raise RuntimeError(f"Connection failed for {url}: {e}") from e


def wait_for_ready(base_url, timeout=30):
    """Poll health endpoint until healthy or timeout expires."""
    health_url = urllib.parse.urljoin(base_url, "/health/")
    deadline = time.time() + timeout
    last_err = None

    print(f"Waiting for deployment readiness at {health_url} (timeout: {timeout}s)...")
    while time.time() < deadline:
        try:
            status, _, body = make_request(health_url)
            if status == 200:
                data = json.loads(body.decode("utf-8"))
                if data.get("status") == "healthy" and data.get("database") == "connected":
                    print(f"[READY] Deployment is healthy and database is connected.")
                    return True
        except Exception as e:
            last_err = e
        time.sleep(1)

    print(f"[TIMEOUT] Deployment was not ready within {timeout}s. Last error: {last_err}")
    return False


def run_smoke_tests(base_url):
    """Run production smoke tests against the deployed Nginx entry point."""
    print("=" * 70)
    print(f"Running Production Deployment Smoke Tests against: {base_url}")
    print("=" * 70)

    failures = []
    base_url = base_url.rstrip("/")

    # -------------------------------------------------------------------------
    # Test 1: Frontend response
    # -------------------------------------------------------------------------
    test_name = "1. Frontend response (GET /)"
    try:
        status, headers, body = make_request(f"{base_url}/")
        body_text = body.decode("utf-8", errors="replace")
        content_type = headers.get("Content-Type", "")

        assert status == 200, f"Expected HTTP 200, got {status}"
        assert "text/html" in content_type, f"Expected text/html, got {content_type}"
        assert '<div id="root">' in body_text, "Missing React entry point '<div id=\"root\">' in HTML response"
        assert "<title>" in body_text, "Missing '<title>' tag in HTML response"
        print(f"[PASS] {test_name}: HTTP 200 HTML with React root entry point")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")
        return failures

    # -------------------------------------------------------------------------
    # Test 2: Static assets (dynamic JS and CSS extraction)
    # -------------------------------------------------------------------------
    test_name = "2. Static assets (dynamically parsed JS & CSS)"
    try:
        # Extract script src
        js_matches = re.findall(r'<script[^>]+src=["\']([^"\']+\.js)["\']', body_text)
        assert js_matches, "Could not find any script tags with .js source in HTML"
        js_rel_url = js_matches[0]
        js_url = urllib.parse.urljoin(f"{base_url}/", js_rel_url)

        js_status, js_headers, js_body = make_request(js_url)
        js_ct = js_headers.get("Content-Type", "")
        assert js_status == 200, f"JS asset {js_url} returned HTTP {js_status}"
        assert any(t in js_ct for t in ("javascript", "application/x-javascript")), (
            f"Expected JS content-type for {js_url}, got '{js_ct}'"
        )
        assert len(js_body) > 0, f"Empty JS asset body for {js_url}"
        print(f"[PASS] {test_name} - JavaScript: HTTP 200 ({js_ct}, {len(js_body)} bytes) at {js_rel_url}")

        # Extract stylesheet href
        css_matches = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+\.css)["\']', body_text)
        if not css_matches:
            # Also try href before rel
            css_matches = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\'][^>]+rel=["\']stylesheet["\']', body_text)
        assert css_matches, "Could not find any stylesheet link tags with .css href in HTML"
        css_rel_url = css_matches[0]
        css_url = urllib.parse.urljoin(f"{base_url}/", css_rel_url)

        css_status, css_headers, css_body = make_request(css_url)
        css_ct = css_headers.get("Content-Type", "")
        assert css_status == 200, f"CSS asset {css_url} returned HTTP {css_status}"
        assert "text/css" in css_ct, f"Expected text/css for {css_url}, got '{css_ct}'"
        assert len(css_body) > 0, f"Empty CSS asset body for {css_url}"
        print(f"[PASS] {test_name} - Stylesheet: HTTP 200 ({css_ct}, {len(css_body)} bytes) at {css_rel_url}")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    # -------------------------------------------------------------------------
    # Test 3: Single-page application routing (SPA fallback)
    # -------------------------------------------------------------------------
    test_name = "3. Single-page application routing (GET /stations)"
    try:
        spa_url = f"{base_url}/stations"
        status, headers, body = make_request(spa_url)
        body_text_spa = body.decode("utf-8", errors="replace")
        content_type = headers.get("Content-Type", "")

        assert status == 200, f"Expected HTTP 200 for SPA route {spa_url}, got {status}"
        assert "text/html" in content_type, f"Expected text/html, got {content_type}"
        assert '<div id="root">' in body_text_spa, "SPA fallback did not return React HTML entry point"
        print(f"[PASS] {test_name}: HTTP 200 HTML served via Nginx try_files SPA fallback")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    # -------------------------------------------------------------------------
    # Test 4: Health endpoint (GET /health/)
    # -------------------------------------------------------------------------
    test_name = "4. Backend health endpoint (GET /health/)"
    try:
        health_url = f"{base_url}/health/"
        status, headers, body = make_request(health_url)
        assert status == 200, f"Expected HTTP 200, got {status}"
        data = json.loads(body.decode("utf-8"))
        assert data.get("status") == "healthy", f"Expected status 'healthy', got '{data.get('status')}'"
        assert data.get("database") == "connected", f"Expected database 'connected', got '{data.get('database')}'"
        print(f"[PASS] {test_name}: HTTP 200 with schema: {data}")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    # -------------------------------------------------------------------------
    # Test 5: Backend API routing (GET /api/stations/ & GET /api/chargers/)
    # -------------------------------------------------------------------------
    test_name = "5. Backend API routing (GET /api/stations/)"
    try:
        stations_url = f"{base_url}/api/stations/"
        status, headers, body = make_request(stations_url)
        content_type = headers.get("Content-Type", "")

        assert status == 200, f"Expected HTTP 200 for {stations_url}, got {status}"
        assert "application/json" in content_type, f"Expected application/json, got {content_type}"
        data = json.loads(body.decode("utf-8"))
        assert isinstance(data, list), f"Expected JSON array, got {type(data).__name__}"
        print(f"[PASS] {test_name}: HTTP 200 JSON array with {len(data)} stations")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    test_name_chargers = "5b. Backend API routing (GET /api/chargers/)"
    try:
        chargers_url = f"{base_url}/api/chargers/"
        status, headers, body = make_request(chargers_url)
        content_type = headers.get("Content-Type", "")

        assert status == 200, f"Expected HTTP 200 for {chargers_url}, got {status}"
        assert "application/json" in content_type, f"Expected application/json, got {content_type}"
        data = json.loads(body.decode("utf-8"))
        assert isinstance(data, list), f"Expected JSON array, got {type(data).__name__}"
        print(f"[PASS] {test_name_chargers}: HTTP 200 JSON array with {len(data)} chargers")
    except Exception as e:
        failures.append((test_name_chargers, str(e)))
        print(f"[FAIL] {test_name_chargers}: {e}")

    # -------------------------------------------------------------------------
    # Test 6: API error handling (GET /api/nonexistent-endpoint-smoke-test/)
    # -------------------------------------------------------------------------
    test_name = "6. API error handling (GET /api/nonexistent-endpoint-smoke-test/)"
    try:
        bad_api_url = f"{base_url}/api/nonexistent-endpoint-smoke-test/"
        status, headers, body = make_request(bad_api_url)
        body_text_bad = body.decode("utf-8", errors="replace")

        assert status == 404, f"Expected HTTP 404 for nonexistent API endpoint, got {status}"
        assert '<div id="root">' not in body_text_bad, (
            "API 404 was incorrectly routed to React SPA fallback instead of Django 404 handler!"
        )
        print(f"[PASS] {test_name}: HTTP 404 handled by Django upstream (not React SPA fallback)")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    # -------------------------------------------------------------------------
    # Test 7: Database-backed operation validation
    # -------------------------------------------------------------------------
    test_name = "7. Database-backed operation validation"
    try:
        # Verify read-only database connectivity is confirmed without altering dev data or creating bookings
        health_url = f"{base_url}/health/"
        status, _, body = make_request(health_url)
        data = json.loads(body.decode("utf-8"))
        assert status == 200 and data.get("database") == "connected", "Database is not connected"
        print(f"[PASS] {test_name}: Database connectivity verified via live connection query")
    except Exception as e:
        failures.append((test_name, str(e)))
        print(f"[FAIL] {test_name}: {e}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("=" * 70)
    if failures:
        print(f"FAILED: {len(failures)} smoke test(s) failed.")
        for name, err in failures:
            print(f" - {name}: {err}")
        return failures
    else:
        print("SUCCESS: All production deployment smoke tests passed!")
        return []


def main():
    parser = argparse.ArgumentParser(description="Production Deployment Smoke Tests")
    parser.add_argument(
        "--url",
        "--base-url",
        dest="base_url",
        default="http://127.0.0.1:8085",
        help="Base URL of the deployed Nginx entry point (default: http://127.0.0.1:8085)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Seconds to wait for service readiness (default: 30)",
    )
    args = parser.parse_args()

    ready = wait_for_ready(args.base_url, timeout=args.timeout)
    if not ready:
        print("[ERROR] Service failed readiness check before tests could begin.")
        sys.exit(1)

    failures = run_smoke_tests(args.base_url)
    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
