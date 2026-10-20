"""
Selenium Test Configuration and Pytest Fixtures
EV Charging Slot Booking System
"""

import os
import time
import uuid
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


# Configure output directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "test-reports")
SCREENSHOTS_DIR = os.path.join(REPORTS_DIR, "screenshots")


@pytest.fixture(scope="session")
def base_url():
    """Return the base URL of the deployed application under test."""
    return os.environ.get("BASE_URL", "http://127.0.0.1:8081").rstrip("/")


@pytest.fixture(scope="session")
def driver():
    """Create and configure a Selenium WebDriver instance for the test session."""
    browser_name = os.environ.get("BROWSER", "chrome").lower()
    headless_env = os.environ.get("HEADLESS", "true").lower()
    is_headless = headless_env in ("true", "1", "yes")

    if browser_name == "chrome":
        opts = ChromeOptions()
        if is_headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-extensions")
        driver_instance = webdriver.Chrome(options=opts)
    elif browser_name == "edge":
        opts = EdgeOptions()
        if is_headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        driver_instance = webdriver.Edge(options=opts)
    else:
        raise ValueError(f"Unsupported browser: {browser_name}. Use 'chrome' or 'edge'.")

    driver_instance.implicitly_wait(2)
    driver_instance.set_page_load_timeout(30)

    yield driver_instance

    driver_instance.quit()


@pytest.fixture(scope="class")
def test_driver_data():
    """Generate unique and deterministic test credentials for the driver session."""
    unique_suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"driver_sel_{unique_suffix}",
        "email": f"sel_{unique_suffix}@example.com",
        "password": "PassWord123!",
        "phone": "+15551234567",
    }


@pytest.fixture(scope="class")
def test_vehicle_data():
    """Generate unique and deterministic test vehicle details."""
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return {
        "reg_number": f"SEL-{unique_suffix}",
        "make": "Hyundai",
        "model": "Ioniq 5",
        "battery_capacity": "77.40",
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture a screenshot automatically if a test step fails."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver_fixture = item.funcargs.get("driver")
        if driver_fixture:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            sanitized_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in item.name)
            filename = f"failure_{sanitized_name}_{timestamp}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)
            try:
                driver_fixture.save_screenshot(filepath)
                print(f"\n[FAILURE SCREENSHOT SAVED] {filepath}")
            except Exception as e:
                print(f"\n[FAILED TO CAPTURE SCREENSHOT] {e}")
