
from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from vehicles.models import Vehicle
from stations.models import Station, Charger
from bookings.models import Booking


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
