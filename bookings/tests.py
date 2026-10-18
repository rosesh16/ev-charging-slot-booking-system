from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from stations.models import Charger, Station
from vehicles.models import Vehicle


class BookingOverlapConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testdriver",
            email="driver@example.com",
            password="Test-password-123!",
        )

        cls.vehicle = Vehicle.objects.create(
            owner=cls.user,
            registration_number="TEST-EV-001",
            make="Test",
            model="Electric",
            battery_capacity_kwh=60,
        )

        cls.station = Station.objects.create(
            name="Test Charging Station",
            address="1 Test Road",
            city="Mumbai",
        )

        cls.charger = Charger.objects.create(
            station=cls.station,
            name="Charger 1",
            connector_type=Charger.ConnectorType.TYPE_2,
            power_kw=7.40,
        )

        cls.start = (timezone.now() + timedelta(days=2)).replace(
            second=0, microsecond=0
        )

    def create_booking(self, start, end, status=Booking.Status.CONFIRMED):
        return Booking.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            charger=self.charger,
            start_time=start,
            end_time=end,
            status=status,
        )

    def test_overlapping_booking_is_rejected(self):
        self.create_booking(
            self.start,
            self.start + timedelta(minutes=30),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_booking(
                    self.start + timedelta(minutes=15),
                    self.start + timedelta(minutes=45),
                )

    def test_adjacent_bookings_are_allowed(self):
        self.create_booking(
            self.start,
            self.start + timedelta(minutes=30),
        )

        next_booking = self.create_booking(
            self.start + timedelta(minutes=30),
            self.start + timedelta(minutes=60),
        )

        self.assertIsNotNone(next_booking.pk)

    def test_cancelled_booking_does_not_block_slot(self):
        self.create_booking(
            self.start,
            self.start + timedelta(minutes=30),
            status=Booking.Status.CANCELLED,
        )

        replacement = self.create_booking(
            self.start,
            self.start + timedelta(minutes=30),
        )

        self.assertIsNotNone(replacement.pk)


class BookingApiTests(APITestCase):
    def setUp(self):
        self.bookings_url = reverse("booking-list-create")

        # Users and auth tokens
        self.user_1 = User.objects.create_user(
            username="driver1",
            email="driver1@example.com",
            password="StrongPassword123!",
        )
        self.token_1 = Token.objects.create(user=self.user_1)

        self.user_2 = User.objects.create_user(
            username="driver2",
            email="driver2@example.com",
            password="StrongPassword123!",
        )
        self.token_2 = Token.objects.create(user=self.user_2)

        # Vehicles
        self.vehicle_1 = Vehicle.objects.create(
            owner=self.user_1,
            registration_number="EV-001-A",
            make="Tesla",
            model="Model 3",
            battery_capacity_kwh=75.00,
        )
        self.vehicle_2 = Vehicle.objects.create(
            owner=self.user_2,
            registration_number="EV-002-B",
            make="Tata",
            model="Nexon EV",
            battery_capacity_kwh=40.50,
        )

        # Stations
        self.active_station = Station.objects.create(
            name="Central Hub",
            address="1 Central Plaza",
            city="Metropolis",
            is_active=True,
        )
        self.inactive_station = Station.objects.create(
            name="Abandoned Hub",
            address="99 Dark Alley",
            city="Metropolis",
            is_active=False,
        )

        # Chargers
        self.active_charger = Charger.objects.create(
            station=self.active_station,
            name="Charger 101",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )
        self.inactive_charger = Charger.objects.create(
            station=self.active_station,
            name="Charger Inactive",
            connector_type=Charger.ConnectorType.TYPE_2,
            power_kw=22.00,
            status=Charger.Status.AVAILABLE,
            is_active=False,
        )
        self.charger_at_inactive_station = Charger.objects.create(
            station=self.inactive_station,
            name="Ghost Charger",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )
        self.offline_charger = Charger.objects.create(
            station=self.active_station,
            name="Charger Offline",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.OFFLINE,
            is_active=True,
        )
        self.maintenance_charger = Charger.objects.create(
            station=self.active_station,
            name="Charger Maintenance",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.MAINTENANCE,
            is_active=True,
        )

        # Time slots
        self.future_start = (timezone.now() + timedelta(days=2)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.future_end = self.future_start + timedelta(minutes=30)

        self.valid_payload = {
            "charger": self.active_charger.id,
            "vehicle": self.vehicle_1.id,
            "start_time": self.future_start.isoformat(),
            "end_time": self.future_end.isoformat(),
        }

    def test_unauthenticated_requests_rejected(self):
        # List / Create
        r_get = self.client.get(self.bookings_url)
        self.assertEqual(r_get.status_code, status.HTTP_401_UNAUTHORIZED)

        r_post = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(r_post.status_code, status.HTTP_401_UNAUTHORIZED)

        # Detail / Cancel
        detail_url = reverse("booking-detail", kwargs={"pk": 1})
        self.assertEqual(
            self.client.get(detail_url).status_code, status.HTTP_401_UNAUTHORIZED
        )

        cancel_url = reverse("booking-cancel", kwargs={"pk": 1})
        self.assertEqual(
            self.client.post(cancel_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_successful_booking_creation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        response = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["user"], self.user_1.id)
        self.assertEqual(data["charger"]["id"], self.active_charger.id)
        self.assertEqual(data["vehicle"]["id"], self.vehicle_1.id)
        self.assertEqual(data["status"], Booking.Status.CONFIRMED)
        self.assertIsNone(data["cancelled_at"])

        # Check DB state
        booking = Booking.objects.get(id=data["id"])
        self.assertEqual(booking.user, self.user_1)
        self.assertEqual(booking.charger, self.active_charger)
        self.assertEqual(booking.vehicle, self.vehicle_1)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_exact_30_minute_duration_validation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")

        # 15 minutes long
        payload_15m = {
            **self.valid_payload,
            "end_time": (self.future_start + timedelta(minutes=15)).isoformat(),
        }
        r_15m = self.client.post(self.bookings_url, payload_15m)
        self.assertEqual(r_15m.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_time", r_15m.data)

        # 45 minutes long
        payload_45m = {
            **self.valid_payload,
            "end_time": (self.future_start + timedelta(minutes=45)).isoformat(),
        }
        r_45m = self.client.post(self.bookings_url, payload_45m)
        self.assertEqual(r_45m.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_time", r_45m.data)

        # End time before start time
        payload_reversed = {
            **self.valid_payload,
            "end_time": (self.future_start - timedelta(minutes=30)).isoformat(),
        }
        r_rev = self.client.post(self.bookings_url, payload_reversed)
        self.assertEqual(r_rev.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_time", r_rev.data)

    def test_past_start_time_rejection(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        past_start = timezone.now() - timedelta(hours=2)
        past_payload = {
            **self.valid_payload,
            "start_time": past_start.isoformat(),
            "end_time": (past_start + timedelta(minutes=30)).isoformat(),
        }
        response = self.client.post(self.bookings_url, past_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", response.data)

    def test_vehicle_ownership_enforcement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        # user_1 tries to book with vehicle_2 (owned by user_2)
        payload = {
            **self.valid_payload,
            "vehicle": self.vehicle_2.id,
        }
        response = self.client.post(self.bookings_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vehicle", response.data)

    def test_inactive_charger_and_station_rejection(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")

        # Inactive charger
        payload_inactive_charger = {
            **self.valid_payload,
            "charger": self.inactive_charger.id,
        }
        r_charger = self.client.post(
            self.bookings_url, payload_inactive_charger
        )
        self.assertEqual(r_charger.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("charger", r_charger.data)

        # Charger at inactive station
        payload_inactive_station = {
            **self.valid_payload,
            "charger": self.charger_at_inactive_station.id,
        }
        r_station = self.client.post(
            self.bookings_url, payload_inactive_station
        )
        self.assertEqual(r_station.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("charger", r_station.data)

    def test_offline_and_maintenance_charger_rejection(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")

        # OFFLINE charger
        r_offline = self.client.post(
            self.bookings_url,
            {**self.valid_payload, "charger": self.offline_charger.id},
        )
        self.assertEqual(r_offline.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("charger", r_offline.data)

        # MAINTENANCE charger
        r_maint = self.client.post(
            self.bookings_url,
            {**self.valid_payload, "charger": self.maintenance_charger.id},
        )
        self.assertEqual(r_maint.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("charger", r_maint.data)

    def test_overlapping_booking_conflict(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        # Create first booking: 10:00 -> 10:30
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # User 2 attempts overlapping booking: 10:15 -> 10:45
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_2.key}")
        overlap_start = self.future_start + timedelta(minutes=15)
        overlap_end = overlap_start + timedelta(minutes=30)
        overlap_payload = {
            "charger": self.active_charger.id,
            "vehicle": self.vehicle_2.id,
            "start_time": overlap_start.isoformat(),
            "end_time": overlap_end.isoformat(),
        }
        r2 = self.client.post(self.bookings_url, overlap_payload)
        self.assertEqual(r2.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("detail", r2.data)

    def test_adjacent_booking_acceptance(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        # Booking 1: 10:00 -> 10:30
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # Booking 2 directly adjacent: 10:30 -> 11:00
        adjacent_start = self.future_end
        adjacent_end = adjacent_start + timedelta(minutes=30)
        adjacent_payload = {
            "charger": self.active_charger.id,
            "vehicle": self.vehicle_1.id,
            "start_time": adjacent_start.isoformat(),
            "end_time": adjacent_end.isoformat(),
        }
        r2 = self.client.post(self.bookings_url, adjacent_payload)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

    def test_cancelled_slot_reuse(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        # Create booking
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        booking_id = r1.data["id"]

        # Cancel booking
        cancel_url = reverse("booking-cancel", kwargs={"pk": booking_id})
        r_cancel = self.client.post(cancel_url)
        self.assertEqual(r_cancel.status_code, status.HTTP_200_OK)

        # User 2 rebooks the exact same slot
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_2.key}")
        reuse_payload = {
            "charger": self.active_charger.id,
            "vehicle": self.vehicle_2.id,
            "start_time": self.future_start.isoformat(),
            "end_time": self.future_end.isoformat(),
        }
        r_reuse = self.client.post(self.bookings_url, reuse_payload)
        self.assertEqual(r_reuse.status_code, status.HTTP_201_CREATED)

    def test_listing_only_authenticated_user_bookings(self):
        # User 1 creates a booking
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # User 2 creates a booking for a different time slot
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_2.key}")
        other_start = self.future_start + timedelta(hours=2)
        other_end = other_start + timedelta(minutes=30)
        r2 = self.client.post(
            self.bookings_url,
            {
                "charger": self.active_charger.id,
                "vehicle": self.vehicle_2.id,
                "start_time": other_start.isoformat(),
                "end_time": other_end.isoformat(),
            },
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        # User 1 lists bookings
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        list_1 = self.client.get(self.bookings_url)
        self.assertEqual(list_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_1.data), 1)
        self.assertEqual(list_1.data[0]["id"], r1.data["id"])

        # User 2 lists bookings
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_2.key}")
        list_2 = self.client.get(self.bookings_url)
        self.assertEqual(list_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_2.data), 1)
        self.assertEqual(list_2.data[0]["id"], r2.data["id"])

    def test_preventing_access_to_another_users_booking(self):
        # User 1 creates booking
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        booking_id = r1.data["id"]

        # User 2 attempts to retrieve it
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_2.key}")
        detail_url = reverse("booking-detail", kwargs={"pk": booking_id})
        r_get = self.client.get(detail_url)
        self.assertEqual(r_get.status_code, status.HTTP_404_NOT_FOUND)

        # User 2 attempts to cancel it
        cancel_url = reverse("booking-cancel", kwargs={"pk": booking_id})
        r_cancel = self.client.post(cancel_url)
        self.assertEqual(r_cancel.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_cancellation_and_cancelled_at(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        booking_id = r1.data["id"]

        cancel_url = reverse("booking-cancel", kwargs={"pk": booking_id})
        r_cancel = self.client.post(cancel_url)
        self.assertEqual(r_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(r_cancel.data["status"], Booking.Status.CANCELLED)
        self.assertIsNotNone(r_cancel.data["cancelled_at"])

        # Verify DB
        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertIsNotNone(booking.cancelled_at)

    def test_invalid_cancellation_attempts(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")
        r1 = self.client.post(self.bookings_url, self.valid_payload)
        booking_id = r1.data["id"]

        cancel_url = reverse("booking-cancel", kwargs={"pk": booking_id})

        # Cancel once -> OK
        r_cancel1 = self.client.post(cancel_url)
        self.assertEqual(r_cancel1.status_code, status.HTTP_200_OK)

        # Cancel again -> 400 Bad Request
        r_cancel2 = self.client.post(cancel_url)
        self.assertEqual(r_cancel2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", r_cancel2.data)

        # Try to cancel a COMPLETED booking
        completed_booking = Booking.objects.create(
            user=self.user_1,
            vehicle=self.vehicle_1,
            charger=self.active_charger,
            start_time=self.future_start + timedelta(days=5),
            end_time=self.future_start + timedelta(days=5, minutes=30),
            status=Booking.Status.COMPLETED,
        )
        r_comp = self.client.post(
            reverse("booking-cancel", kwargs={"pk": completed_booking.id})
        )
        self.assertEqual(r_comp.status_code, status.HTTP_400_BAD_REQUEST)

        # Try to cancel a past booking
        past_booking = Booking.objects.create(
            user=self.user_1,
            vehicle=self.vehicle_1,
            charger=self.active_charger,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1, minutes=30),
            status=Booking.Status.CONFIRMED,
        )
        r_past = self.client.post(
            reverse("booking-cancel", kwargs={"pk": past_booking.id})
        )
        self.assertEqual(r_past.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conflict_handling_without_leaking_database_exceptions(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")

        class MockDiag:
            constraint_name = "no_overlapping_active_charger_bookings"

        class MockCause(Exception):
            diag = MockDiag()

        mock_exc = IntegrityError(
            'conflicting key value violates exclusion constraint "no_overlapping_active_charger_bookings"'
        )
        mock_exc.__cause__ = MockCause()

        # Simulate database IntegrityError (exclusion constraint collision)
        with patch.object(
            Booking.objects,
            "create",
            side_effect=mock_exc,
        ):
            response = self.client.post(self.bookings_url, self.valid_payload)
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            self.assertIn("detail", response.data)
            # Ensure raw DB error message is NOT exposed to client
            self.assertNotIn(
                "exclusion constraint", response.data["detail"]
            )

    def test_unrelated_integrity_error_does_not_return_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_1.key}")

        class MockOtherDiag:
            constraint_name = "some_other_check_constraint"

        class MockOtherCause(Exception):
            diag = MockOtherDiag()

        mock_exc = IntegrityError(
            'check constraint "some_other_check_constraint" violation'
        )
        mock_exc.__cause__ = MockOtherCause()

        with patch.object(
            Booking.objects,
            "create",
            side_effect=mock_exc,
        ):
            response = self.client.post(self.bookings_url, self.valid_payload)
            # Unrelated integrity error must return 500, NOT 409
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            self.assertEqual(
                response.data["detail"], "A database integrity error occurred."
            )


from django.test import TestCase, TransactionTestCase


class PostgresConcurrencyTests(TransactionTestCase):
    # Uses real PostgreSQL test database with independent worker threads
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="concurrent_a",
            email="con_a@example.com",
            password="StrongPassword123!",
        )
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(
            username="concurrent_b",
            email="con_b@example.com",
            password="StrongPassword123!",
        )
        self.token_b = Token.objects.create(user=self.user_b)

        self.vehicle_a = Vehicle.objects.create(
            owner=self.user_a,
            registration_number="CON-001",
            make="Tesla",
            model="Model Y",
        )
        self.vehicle_b = Vehicle.objects.create(
            owner=self.user_b,
            registration_number="CON-002",
            make="Hyundai",
            model="Ioniq 5",
        )

        self.station = Station.objects.create(
            name="Concurrency Station",
            address="123 Sync Road",
            city="Metropolis",
            is_active=True,
        )
        self.charger = Charger.objects.create(
            station=self.station,
            name="Sync Charger",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=100.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

        self.slot_start = (timezone.now() + timedelta(days=3)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        self.slot_end = self.slot_start + timedelta(minutes=30)
        self.bookings_url = reverse("booking-list-create")

    def test_concurrent_simultaneous_booking_requests(self):
        import concurrent.futures
        import threading
        from django.db import connections
        from rest_framework.test import APIClient

        barrier = threading.Barrier(2)

        def make_booking_attempt(token, vehicle_id):
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
            payload = {
                "charger": self.charger.id,
                "vehicle": vehicle_id,
                "start_time": self.slot_start.isoformat(),
                "end_time": self.slot_end.isoformat(),
            }
            # Synchronize threads right before posting
            barrier.wait(timeout=5)
            try:
                return client.post(self.bookings_url, payload)
            finally:
                connections.close_all()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(
                make_booking_attempt, self.token_a.key, self.vehicle_a.id
            )
            future_b = executor.submit(
                make_booking_attempt, self.token_b.key, self.vehicle_b.id
            )
            res_a = future_a.result()
            res_b = future_b.result()

        # Exactly one request must succeed (201) and exactly one must fail with conflict (409)
        status_codes = sorted([res_a.status_code, res_b.status_code])
        self.assertEqual(
            status_codes,
            [status.HTTP_201_CREATED, status.HTTP_409_CONFLICT],
            f"Expected [201, 409], got {status_codes}. Response A: {res_a.data}, Response B: {res_b.data}",
        )

        # Exactly one active booking must exist in PostgreSQL
        active_bookings = Booking.objects.filter(
            charger=self.charger,
            start_time=self.slot_start,
            end_time=self.slot_end,
        ).exclude(status=Booking.Status.CANCELLED)
        self.assertEqual(active_bookings.count(), 1)
