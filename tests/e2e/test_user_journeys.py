"""
End-to-End Selenium WebDriver User Journey Test Suite
EV Charging Slot Booking System

Critical User Journeys:
1. Journey 1: User Registration, Login & Authentication State
2. Journey 2: Station and Charger Discovery (Live Data & Filters)
3. Journey 3: Vehicle Registration (Manage EV Fleet)
4. Journey 4: Slot Reservation / Booking Creation (30-Minute Interval)
5. Journey 5: Booking Cancellation & Status Update
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select


def scroll_and_click(driver, element):
    """Scroll element into the center of the viewport and click it."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
    time.sleep(0.2)
    element.click()


@pytest.mark.usefixtures("driver", "base_url", "test_driver_data", "test_vehicle_data")
class TestEVBookingJourneys:
    """Ordered test suite executing 5 critical user journeys across the application."""

    def test_01_user_registration_and_auth_state(self, driver, base_url, test_driver_data):
        """Journey 1: Register a new driver and verify authentication state and UI changes."""
        driver.get(base_url)
        wait = WebDriverWait(driver, 15)

        # 1. Verify landing page
        wait.until(lambda d: "VoltSlot" in d.title)
        assert "VoltSlot" in driver.title, f"Unexpected title: {driver.title}"

        # 2. Check unauthenticated guest state
        reg_btn = wait.until(EC.element_to_be_clickable((By.ID, "top-nav-register-btn")))
        assert reg_btn.is_displayed(), "Register button should be visible for guest"

        footer_text = driver.find_element(By.CLASS_NAME, "dashboard-footer").text
        assert "Guest Session" in footer_text, f"Footer did not indicate guest session: {footer_text}"

        # 3. Open registration modal
        scroll_and_click(driver, reg_btn)
        auth_dialog = wait.until(EC.visibility_of_element_located((By.ID, "auth-modal-dialog")))
        modal_title = auth_dialog.find_element(By.ID, "auth-modal-title").text
        assert "Create a VoltSlot Account" in modal_title or "VoltSlot" in modal_title

        # 4. Fill registration form with deterministic test data
        username_input = auth_dialog.find_element(By.ID, "reg-username")
        email_input = auth_dialog.find_element(By.ID, "auth-email")
        password_input = auth_dialog.find_element(By.ID, "auth-password")
        phone_input = auth_dialog.find_element(By.ID, "reg-phone")

        username_input.clear()
        username_input.send_keys(test_driver_data["username"])
        email_input.clear()
        email_input.send_keys(test_driver_data["email"])
        password_input.clear()
        password_input.send_keys(test_driver_data["password"])
        phone_input.clear()
        phone_input.send_keys(test_driver_data["phone"])

        # 5. Submit registration
        submit_btn = auth_dialog.find_element(By.CSS_SELECTOR, "button[type='submit'].auth-submit-btn")
        scroll_and_click(driver, submit_btn)

        # 6. Wait for modal to close upon successful authentication
        wait.until(EC.invisibility_of_element_located((By.ID, "auth-modal-dialog")))

        # 7. Assert authenticated UI state
        user_name_elem = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "user-name")))
        assert test_driver_data["username"] in user_name_elem.text, (
            f"Expected user {test_driver_data['username']} in topnav, found {user_name_elem.text}"
        )

        user_role_elem = driver.find_element(By.CLASS_NAME, "user-role")
        assert "DRIVER" in user_role_elem.text, f"Expected role DRIVER, found {user_role_elem.text}"

        logout_btn = driver.find_element(By.CLASS_NAME, "logout-nav-btn")
        assert logout_btn.is_displayed(), "Sign out button should be visible when authenticated"

        footer_elem = driver.find_element(By.CLASS_NAME, "dashboard-footer")
        assert test_driver_data["username"] in footer_elem.text, "Footer should display driver username"

    def test_02_station_and_charger_discovery(self, driver, base_url):
        """Journey 2: Discover charging stations and chargers, test search and connector filters."""
        wait = WebDriverWait(driver, 15)

        # 1. Navigate to 'Find Stations' view via Sidebar
        stations_nav_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//nav[contains(@class,'sidebar-nav')]//button[contains(., 'Find Stations')]")
            )
        )
        scroll_and_click(driver, stations_nav_btn)

        # 2. Wait for live stations section and station cards
        station_section = wait.until(
            EC.visibility_of_element_located((By.CLASS_NAME, "station-discovery-section"))
        )
        station_cards = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "station-card"))
        )
        assert len(station_cards) >= 1, "Expected at least one charging station in discovery view"

        # Verify live station content
        first_station_name = station_cards[0].find_element(By.CLASS_NAME, "station-name").text
        assert len(first_station_name) > 0, "Station card has empty name"

        chargers_chips = station_cards[0].find_elements(By.CLASS_NAME, "charger-chip")
        assert len(chargers_chips) >= 1, "Expected at least one installed charger chip in station card"

        # 3. Test search filter
        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".search-bar input")))
        search_input.clear()
        search_input.send_keys("Westside")
        time.sleep(0.5)

        filtered_cards = driver.find_elements(By.CLASS_NAME, "station-card")
        for card in filtered_cards:
            assert "Westside" in card.text, "Search for 'Westside' did not filter stations correctly"

        # Clear search
        search_input.clear()
        search_input.send_keys(" ")
        time.sleep(0.2)
        search_input.clear()
        time.sleep(0.5)

        # 4. Test connector type filter buttons
        ccs2_filter_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'filter-pill') and text()='CCS2']"))
        )
        scroll_and_click(driver, ccs2_filter_btn)
        time.sleep(0.5)
        assert "active" in ccs2_filter_btn.get_attribute("class"), "CCS2 filter pill should be active"

        all_filter_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class,'filter-pill') and contains(text(), 'All Connectors')]")
            )
        )
        scroll_and_click(driver, all_filter_btn)
        time.sleep(0.5)
        assert "active" in all_filter_btn.get_attribute("class"), "All Connectors pill should be active"

    def test_03_vehicle_registration(self, driver, base_url, test_vehicle_data):
        """Journey 3: Navigate to My Vehicles and register a new electric vehicle."""
        wait = WebDriverWait(driver, 15)

        # 1. Navigate to 'My Vehicles' view via Sidebar
        vehicles_nav_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//nav[contains(@class,'sidebar-nav')]//button[contains(., 'My Vehicles')]")
            )
        )
        scroll_and_click(driver, vehicles_nav_btn)

        # 2. Verify vehicles view loaded
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "vehicles-view-container")))

        # 3. Open 'Register New EV' modal
        register_ev_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), '+ Register New EV') or contains(text(), 'Register Your First EV')]")
            )
        )
        scroll_and_click(driver, register_ev_btn)

        modal_card = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "modal-card")))
        assert "Register Electric Vehicle" in modal_card.text

        # 4. Fill vehicle details
        reg_input = modal_card.find_element(By.ID, "veh-reg-number")
        make_input = modal_card.find_element(By.ID, "veh-make")
        model_input = modal_card.find_element(By.ID, "veh-model")
        battery_input = modal_card.find_element(By.ID, "veh-battery")

        reg_input.clear()
        reg_input.send_keys(test_vehicle_data["reg_number"])
        make_input.clear()
        make_input.send_keys(test_vehicle_data["make"])
        model_input.clear()
        model_input.send_keys(test_vehicle_data["model"])
        battery_input.clear()
        battery_input.send_keys(test_vehicle_data["battery_capacity"])

        # 5. Submit vehicle registration
        submit_btn = modal_card.find_element(By.CSS_SELECTOR, "button[type='submit'].auth-submit-btn")
        scroll_and_click(driver, submit_btn)

        # 6. Verify success alert in modal and wait for modal close
        wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-card .auth-alert.success"))
        )
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "modal-card")))

        # 7. Verify vehicle card appears in the vehicles grid
        vehicle_plate = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//span[contains(@class, 'vehicle-plate') and contains(text(), '{test_vehicle_data['reg_number']}')]")
            )
        )
        assert vehicle_plate.is_displayed(), f"Registered vehicle plate {test_vehicle_data['reg_number']} not found"

        # Verify make/model text in the card
        parent_card = vehicle_plate.find_element(By.XPATH, "./ancestor::div[contains(@class, 'vehicle-card')]")
        assert test_vehicle_data["make"] in parent_card.text
        assert test_vehicle_data["model"] in parent_card.text

    def test_04_create_charging_slot_booking(self, driver, base_url, test_vehicle_data):
        """Journey 4: Navigate to bookings, select 30-min slot, and create a confirmed reservation."""
        wait = WebDriverWait(driver, 15)

        # 1. Navigate to 'My Bookings' via Sidebar
        bookings_nav_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//nav[contains(@class,'sidebar-nav')]//button[contains(., 'My Bookings')]")
            )
        )
        scroll_and_click(driver, bookings_nav_btn)

        # 2. Verify bookings section loaded
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "bookings-section-container")))

        # 3. Verify vehicle selector has registered vehicle
        vehicle_select_elem = wait.until(EC.presence_of_element_located((By.ID, "slot-vehicle-select")))
        select_obj = Select(vehicle_select_elem)
        options_text = [o.text for o in select_obj.options]
        has_vehicle = any(test_vehicle_data["reg_number"] in t for t in options_text)
        assert has_vehicle, f"Registered vehicle {test_vehicle_data['reg_number']} not in booking dropdown: {options_text}"

        # 4. Select booking date tab: 'Tomorrow'
        tomorrow_pill = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, 'day-select-pill') and text()='Tomorrow']")
            )
        )
        scroll_and_click(driver, tomorrow_pill)
        time.sleep(0.5)

        # 5. Wait for live availability slots to load
        available_slots = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".slot-tile.available"))
        )
        assert len(available_slots) > 0, "Expected at least one available 30-min slot for Tomorrow"

        # Select the first available slot
        first_slot = available_slots[0]
        slot_time_text = first_slot.find_element(By.CLASS_NAME, "slot-time").text
        scroll_and_click(driver, first_slot)
        time.sleep(0.3)

        assert "selected" in first_slot.get_attribute("class"), "Slot tile did not acquire selected class"

        # 6. Click 'Reserve 30-Min Slot'
        reserve_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm-slot-btn"))
        )
        scroll_and_click(driver, reserve_btn)

        # 7. Verify reservation confirmation banner
        success_alert = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".bookings-section-container .auth-alert.success"))
        )
        assert "Booking Confirmed!" in success_alert.text, f"Unexpected alert message: {success_alert.text}"

        # 8. Verify booking card in 'My Bookings History' stack
        booking_card = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".bookings-cards-stack .booking-card"))
        )
        status_pill = booking_card.find_element(By.CSS_SELECTOR, ".status-pill")
        assert "CONFIRMED" in status_pill.text, f"Expected CONFIRMED status, got: {status_pill.text}"

        # Verify cancel button is present on the confirmed card
        cancel_btn = booking_card.find_element(By.CSS_SELECTOR, "button.action-btn-danger")
        assert "Cancel Slot" in cancel_btn.text

    def test_05_cancel_booking_and_verify_status(self, driver, base_url):
        """Journey 5: Cancel the active booking, handle confirmation, and verify status update."""
        wait = WebDriverWait(driver, 15)

        # 1. Locate the confirmed booking card
        booking_card = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".bookings-cards-stack .booking-card"))
        )
        cancel_btn = booking_card.find_element(By.CSS_SELECTOR, "button.action-btn-danger")
        assert "Cancel Slot" in cancel_btn.text

        # 2. Click 'Cancel Slot' to open confirmation row
        scroll_and_click(driver, cancel_btn)

        # 3. Verify confirmation prompt appears
        confirm_row = wait.until(
            EC.visibility_of_element_located((By.CLASS_NAME, "cancel-confirm-row"))
        )
        assert "Cancel reservation?" in confirm_row.text

        confirm_yes_btn = confirm_row.find_element(By.CSS_SELECTOR, "button.action-btn-danger")
        assert "Yes, Cancel" in confirm_yes_btn.text

        # 4. Click 'Yes, Cancel'
        scroll_and_click(driver, confirm_yes_btn)

        # 5. Verify success banner for cancellation
        success_alert = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".bookings-section-container .auth-alert.success"))
        )
        assert "successfully cancelled" in success_alert.text.lower()

        # 6. Verify booking status updated to CANCELLED
        updated_card = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".bookings-cards-stack .booking-card"))
        )
        status_pill = updated_card.find_element(By.CSS_SELECTOR, ".status-pill.status-cancelled")
        assert "CANCELLED" in status_pill.text, f"Expected CANCELLED status, got: {status_pill.text}"

        # Verify 'Cancel Slot' button is no longer present
        action_btns = updated_card.find_elements(By.CSS_SELECTOR, "button.action-btn-danger")
        assert len(action_btns) == 0, "Cancel button should not be present on cancelled booking"
