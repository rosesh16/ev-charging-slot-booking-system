import logging
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from bookings.serializers import BookingCreateSerializer, BookingReadSerializer
from stations.models import Charger

logger = logging.getLogger(__name__)


def is_overlap_constraint_violation(exc):
    """
    Check if an IntegrityError was caused by the PostgreSQL exclusion constraint
    no_overlapping_active_charger_bookings, prioritizing psycopg Diagnostic info.
    """
    cause = getattr(exc, "__cause__", None)
    if cause:
        diag = getattr(cause, "diag", None)
        if diag:
            constraint_name = getattr(diag, "constraint_name", None)
            if constraint_name == "no_overlapping_active_charger_bookings":
                return True

    # Fallback to constraint name check in exception message
    err_str = str(exc)
    if cause:
        err_str = f"{err_str} {cause}"
    return "no_overlapping_active_charger_bookings" in err_str.lower()


class BookingListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("vehicle", "charger", "charger__station")
            .order_by("-start_time")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookingCreateSerializer
        return BookingReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                # Lock charger row first to serialize concurrent booking creation requests
                charger = Charger.objects.select_for_update().get(
                    id=data["charger"].id
                )

                # Pre-check for overlapping active bookings
                overlap = (
                    Booking.objects.filter(
                        charger=charger,
                        start_time__lt=data["end_time"],
                        end_time__gt=data["start_time"],
                    )
                    .exclude(status=Booking.Status.CANCELLED)
                    .exists()
                )
                if overlap:
                    return Response(
                        {
                            "detail": (
                                "This charger is already booked for the requested time slot."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                booking = Booking.objects.create(
                    user=request.user,
                    vehicle=data["vehicle"],
                    charger=charger,
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    status=Booking.Status.CONFIRMED,
                )
        except IntegrityError as exc:
            if is_overlap_constraint_violation(exc):
                return Response(
                    {
                        "detail": (
                            "This charger is already booked for the requested time slot."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            logger.exception("Unexpected database IntegrityError: %s", exc)
            return Response(
                {"detail": "A database integrity error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            BookingReadSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class BookingDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookingReadSerializer

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("vehicle", "charger", "charger__station")
        )


class BookingCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        with transaction.atomic():
            # Lookup booking and charger_id in a single query
            booking_info = (
                Booking.objects.filter(id=pk, user=request.user)
                .values_list("id", "charger_id")
                .first()
            )
            if not booking_info:
                return Response(
                    {"detail": "Booking not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            booking_id, charger_id = booking_info

            # Acquire locks in consistent order: Charger first, then Booking
            Charger.objects.select_for_update().get(id=charger_id)
            booking = (
                Booking.objects.select_for_update()
                .select_related("vehicle", "charger", "charger__station")
                .get(id=booking_id, user=request.user)
            )

            if booking.status == Booking.Status.CANCELLED:
                return Response(
                    {"detail": "This booking is already cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if booking.status == Booking.Status.COMPLETED:
                return Response(
                    {"detail": "Cannot cancel a completed booking."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if booking.start_time <= timezone.now():
                return Response(
                    {
                        "detail": (
                            "Cannot cancel a booking that has already started or ended."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = timezone.now()
            booking.save(update_fields=["status", "cancelled_at"])

        return Response(
            BookingReadSerializer(booking).data,
            status=status.HTTP_200_OK,
        )
