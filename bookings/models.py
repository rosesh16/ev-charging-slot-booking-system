
from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Q, Value


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    charger = models.ForeignKey(
        "stations.Charger",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="booking_end_after_start",
            ),
            ExclusionConstraint(
                name="no_overlapping_active_charger_bookings",
                expressions=[
                    ("charger", RangeOperators.EQUAL),
                    (
                        Func(
                            F("start_time"),
                            F("end_time"),
                            Value("[)"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=~Q(status="CANCELLED"),
            ),
        ]

    def clean(self):
        super().clean()

        if self.start_time and self.end_time:
            if self.end_time - self.start_time != timedelta(minutes=30):
                raise ValidationError(
                    {"end_time": "Bookings must be exactly 30 minutes long."}
                )

        if self.vehicle_id and self.user_id:
            if self.vehicle.owner_id != self.user_id:
                raise ValidationError(
                    {
                        "vehicle": (
                            "The selected vehicle must belong "
                            "to the booking user."
                        )
                    }
                )

    def __str__(self):
        return f"Booking #{self.pk} - {self.status}"
