from datetime import timedelta, timezone as dt_timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from bookings.models import Booking
from stations.models import Charger, Station
from vehicles.models import Vehicle

User = get_user_model()


class StationAndChargerApiTests(APITestCase):
    def setUp(self):
        self.station_list_url = reverse("station-list")
        self.charger_list_url = reverse("charger-list")
        self.health_url = reverse("health-check")

        self.active_station_1 = Station.objects.create(
            name="Downtown Supercharger",
            address="100 Main Street",
            city="Metropolis",
            latitude="18.922000",
            longitude="72.834700",
            is_active=True,
        )

        self.active_station_2 = Station.objects.create(
            name="Uptown Hub",
            address="200 North Avenue",
            city="Metropolis",
            latitude="18.950000",
            longitude="72.850000",
            is_active=True,
        )

        self.inactive_station = Station.objects.create(
            name="Decommissioned Station",
            address="999 Abandoned Way",
            city="Gotham",
            is_active=False,
        )

        # Chargers at active_station_1
        self.charger_1a = Charger.objects.create(
            station=self.active_station_1,
            name="Bay 1",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )
        self.charger_1b_inactive = Charger.objects.create(
            station=self.active_station_1,
            name="Bay 2 Inactive",
            connector_type=Charger.ConnectorType.TYPE_2,
            power_kw=22.00,
            status=Charger.Status.MAINTENANCE,
            is_active=False,
        )

        # Charger at active_station_2
        self.charger_2a = Charger.objects.create(
            station=self.active_station_2,
            name="Bay 1",
            connector_type=Charger.ConnectorType.CHADEMO,
            power_kw=60.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

        # Charger at inactive_station
        self.charger_inactive_st = Charger.objects.create(
            station=self.inactive_station,
            name="Ghost Bay",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

    def test_anonymous_access_allowed(self):
        # Station list
        r = self.client.get(self.station_list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Station detail
        detail_url = reverse(
            "station-detail", kwargs={"pk": self.active_station_1.id}
        )
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Charger list
        r = self.client.get(self.charger_list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Health endpoint
        r = self.client.get(self.health_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_active_stations_only(self):
        response = self.client.get(self.station_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        station_names = [s["name"] for s in response.data]
        self.assertIn("Downtown Supercharger", station_names)
        self.assertIn("Uptown Hub", station_names)
        self.assertNotIn("Decommissioned Station", station_names)

    def test_station_detail_and_nested_chargers(self):
        detail_url = reverse(
            "station-detail", kwargs={"pk": self.active_station_1.id}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data["id"], self.active_station_1.id)
        self.assertEqual(data["name"], "Downtown Supercharger")
        self.assertEqual(data["city"], "Metropolis")
        self.assertTrue(data["is_active"])

        # Check nested chargers: only active charger should be returned
        chargers = data["chargers"]
        self.assertEqual(len(chargers), 1)
        self.assertEqual(chargers[0]["id"], self.charger_1a.id)
        self.assertEqual(chargers[0]["name"], "Bay 1")
        self.assertEqual(chargers[0]["connector_type"], "CCS2")
        self.assertEqual(float(chargers[0]["power_kw"]), 50.00)
        self.assertEqual(chargers[0]["status"], "AVAILABLE")
        self.assertTrue(chargers[0]["is_active"])

    def test_station_detail_404_for_nonexistent_or_inactive(self):
        # Nonexistent station
        url_nonexistent = reverse("station-detail", kwargs={"pk": 99999})
        response = self.client.get(url_nonexistent)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Inactive station
        url_inactive = reverse(
            "station-detail", kwargs={"pk": self.inactive_station.id}
        )
        response = self.client.get(url_inactive)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_active_charger_filtering(self):
        response = self.client.get(self.charger_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_ids = [c["id"] for c in response.data]

        # Active chargers at active stations are included
        self.assertIn(self.charger_1a.id, charger_ids)
        self.assertIn(self.charger_2a.id, charger_ids)

        # Inactive charger at active station is excluded
        self.assertNotIn(self.charger_1b_inactive.id, charger_ids)

    def test_excluding_chargers_whose_stations_are_inactive(self):
        response = self.client.get(self.charger_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_ids = [c["id"] for c in response.data]

        # Active charger at inactive station must be excluded
        self.assertNotIn(self.charger_inactive_st.id, charger_ids)

    def test_filtering_chargers_by_station(self):
        response = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_1.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.charger_1a.id)
        self.assertEqual(
            response.data[0]["station"]["id"], self.active_station_1.id
        )

        response_2 = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_2.id}"
        )
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.data), 1)
        self.assertEqual(response_2.data[0]["id"], self.charger_2a.id)
        self.assertEqual(
            response_2.data[0]["station"]["id"], self.active_station_2.id
        )

    def test_invalid_or_nonexistent_station_filter_rejected(self):
        # Non-integer station parameter
        response_invalid = self.client.get(
            f"{self.charger_list_url}?station=invalid_abc"
        )
        self.assertEqual(response_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("station", response_invalid.data)

        # Nonexistent station ID
        response_nonexistent = self.client.get(
            f"{self.charger_list_url}?station=99999"
        )
        self.assertEqual(
            response_nonexistent.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("station", response_nonexistent.data)

        # Inactive station ID
        response_inactive = self.client.get(
            f"{self.charger_list_url}?station={self.inactive_station.id}"
        )
        self.assertEqual(
            response_inactive.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("station", response_inactive.data)

    def test_charger_response_fields(self):
        response = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_1.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_data = response.data[0]

        expected_keys = {
            "id",
            "name",
            "connector_type",
            "power_kw",
            "status",
            "is_active",
            "station",
        }
        self.assertEqual(set(charger_data.keys()), expected_keys)

        station_data = charger_data["station"]
        self.assertEqual(station_data["id"], self.active_station_1.id)
        self.assertEqual(station_data["name"], "Downtown Supercharger")
        self.assertEqual(station_data["address"], "100 Main Street")
        self.assertEqual(station_data["city"], "Metropolis")

    def test_health_endpoint_success(self):
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": "healthy", "database": "connected"},
        )

    @patch("django.db.connection.ensure_connection")
    def test_health_endpoint_database_failure(self, mock_ensure_connection):
        mock_ensure_connection.side_effect = OperationalError(
            "Database connection failed"
        )
        response = self.client.get(self.health_url)
        self.assertEqual(
            response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
        )
        self.assertEqual(
            response.data,
            {"status": "unhealthy", "database": "disconnected"},
        )


class ChargerAvailabilityApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="availability_driver",
            email="avail_driver@example.com",
            password="StrongPassword123!",
        )
        self.token = Token.objects.create(user=self.user)

        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number="AVAIL-EV-100",
            make="Tesla",
            model="Model Y",
            battery_capacity_kwh=80.00,
        )

        self.active_station = Station.objects.create(
            name="Metro Supercharger",
            address="500 High St",
            city="Metropolis",
            is_active=True,
        )

        self.inactive_station = Station.objects.create(
            name="Abandoned Station",
            address="100 Ghost Way",
            city="Metropolis",
            is_active=False,
        )

        self.active_charger = Charger.objects.create(
            station=self.active_station,
            name="Bay Alpha",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=150.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

        self.inactive_charger = Charger.objects.create(
            station=self.active_station,
            name="Bay Beta Inactive",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=150.00,
            status=Charger.Status.AVAILABLE,
            is_active=False,
        )

        self.charger_at_inactive_station = Charger.objects.create(
            station=self.inactive_station,
            name="Bay Gamma Ghost",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=150.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

        self.offline_charger = Charger.objects.create(
            station=self.active_station,
            name="Bay Delta Offline",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=150.00,
            status=Charger.Status.OFFLINE,
            is_active=True,
        )

        self.maintenance_charger = Charger.objects.create(
            station=self.active_station,
            name="Bay Epsilon Maintenance",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=150.00,
            status=Charger.Status.MAINTENANCE,
            is_active=True,
        )

        # Baseline future time (tomorrow at 10:00 UTC)
        self.base_time = (timezone.now() + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.url = reverse(
            "charger-availability", kwargs={"charger_id": self.active_charger.id}
        )

    def _fmt(self, dt):
        return dt.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_valid_request_no_bookings_returns_empty_list(self):
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=3))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["charger_id"], self.active_charger.id)
        self.assertEqual(response.data["start"], start_str)
        self.assertEqual(response.data["end"], end_str)
        self.assertEqual(response.data["slot_duration_minutes"], 30)
        self.assertEqual(response.data["booked_intervals"], [])

    def test_confirmed_booking_inside_window_is_returned(self):
        b = Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time + timedelta(hours=1),
            end_time=self.base_time + timedelta(hours=1, minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=3))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervals = response.data["booked_intervals"]
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["start_time"], self._fmt(b.start_time))
        self.assertEqual(intervals[0]["end_time"], self._fmt(b.end_time))

    def test_booking_starting_before_window_and_overlapping_is_returned(self):
        # Booking from 09:30 to 10:30 (window is 10:00 to 12:00)
        b = Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time - timedelta(minutes=30),
            end_time=self.base_time + timedelta(minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervals = response.data["booked_intervals"]
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["start_time"], self._fmt(b.start_time))
        self.assertEqual(intervals[0]["end_time"], self._fmt(b.end_time))

    def test_booking_completely_outside_window_is_excluded(self):
        # Booking earlier than window (08:00 - 08:30)
        Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time - timedelta(hours=2),
            end_time=self.base_time - timedelta(hours=1, minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        # Booking later than window (13:00 - 13:30)
        Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time + timedelta(hours=3),
            end_time=self.base_time + timedelta(hours=3, minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["booked_intervals"], [])

    def test_cancelled_bookings_are_excluded(self):
        # Cancelled booking in the window
        Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time + timedelta(hours=1),
            end_time=self.base_time + timedelta(hours=1, minutes=30),
            status=Booking.Status.CANCELLED,
            cancelled_at=timezone.now(),
        )
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["booked_intervals"], [])

    def test_adjacent_bookings_do_not_produce_false_overlaps(self):
        # Immediately preceding booking: 09:30 to 10:00 (window starts at 10:00)
        Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time - timedelta(minutes=30),
            end_time=self.base_time,
            status=Booking.Status.CONFIRMED,
        )
        # Immediately succeeding booking: 12:00 to 12:30 (window ends at 12:00)
        Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.active_charger,
            start_time=self.base_time + timedelta(hours=2),
            end_time=self.base_time + timedelta(hours=2, minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Neither adjacent booking should be included
        self.assertEqual(response.data["booked_intervals"], [])

    def test_missing_start_or_end_returns_400(self):
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))

        # Missing end
        r1 = self.client.get(f"{self.url}?start={start_str}")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", r1.data)

        # Missing start
        r2 = self.client.get(f"{self.url}?end={end_str}")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start", r2.data)

    def test_invalid_timestamp_returns_400(self):
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start=not-a-timestamp&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start", response.data)

    def test_naive_timestamp_returns_400(self):
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        # Naive timestamp lacking offset or 'Z'
        naive_str = "2026-10-21T10:00:00"
        response = self.client.get(f"{self.url}?start={naive_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start", response.data)

    def test_start_greater_than_or_equal_to_end_returns_400(self):
        start_str = self._fmt(self.base_time)
        # start == end
        r1 = self.client.get(f"{self.url}?start={start_str}&end={start_str}")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", r1.data)

        # start > end
        earlier_str = self._fmt(self.base_time - timedelta(hours=1))
        r2 = self.client.get(f"{self.url}?start={start_str}&end={earlier_str}")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", r2.data)

    def test_query_window_exceeding_24_hours_returns_400(self):
        start_str = self._fmt(self.base_time)
        # 25 hours window
        end_str = self._fmt(self.base_time + timedelta(hours=25))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", response.data)

    def test_nonexistent_charger_returns_404(self):
        url = reverse("charger-availability", kwargs={"charger_id": 999999})
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_charger_and_station_return_400(self):
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))

        # Inactive charger
        url_inactive = reverse(
            "charger-availability", kwargs={"charger_id": self.inactive_charger.id}
        )
        r1 = self.client.get(f"{url_inactive}?start={start_str}&end={end_str}")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactive", r1.data["detail"].lower())

        # Charger at inactive station
        url_ghost = reverse(
            "charger-availability",
            kwargs={"charger_id": self.charger_at_inactive_station.id},
        )
        r2 = self.client.get(f"{url_ghost}?start={start_str}&end={end_str}")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactive", r2.data["detail"].lower())

    def test_offline_and_maintenance_chargers_return_400(self):
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))

        # Offline charger
        url_offline = reverse(
            "charger-availability", kwargs={"charger_id": self.offline_charger.id}
        )
        r1 = self.client.get(f"{url_offline}?start={start_str}&end={end_str}")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("offline", r1.data["detail"].lower())

        # Maintenance charger
        url_maint = reverse(
            "charger-availability", kwargs={"charger_id": self.maintenance_charger.id}
        )
        r2 = self.client.get(f"{url_maint}?start={start_str}&end={end_str}")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("maintenance", r2.data["detail"].lower())

    def test_authenticated_access_also_succeeds(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_endpoint_does_not_mutate_or_create_bookings(self):
        initial_count = Booking.objects.count()
        start_str = self._fmt(self.base_time)
        end_str = self._fmt(self.base_time + timedelta(hours=2))
        response = self.client.get(f"{self.url}?start={start_str}&end={end_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Booking.objects.count(), initial_count)
