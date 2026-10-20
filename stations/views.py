from datetime import timezone as dt_timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from stations.models import Charger, Station
from stations.serializers import (
    ChargerAvailabilityQuerySerializer,
    ChargerFilterSerializer,
    ChargerSerializer,
    StationDetailSerializer,
    StationListSerializer,
)


def _format_utc_iso(dt):
    """Format datetime as UTC ISO 8601 string with trailing Z."""
    return dt.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StationListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StationListSerializer
    queryset = Station.objects.filter(is_active=True).order_by("name")


class StationDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StationDetailSerializer
    queryset = Station.objects.filter(is_active=True)


class ChargerListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ChargerSerializer

    def get_queryset(self):
        queryset = (
            Charger.objects.filter(
                is_active=True,
                station__is_active=True,
            )
            .select_related("station")
            .order_by("station__name", "name")
        )

        station_param = self.request.query_params.get("station")
        if station_param is not None:
            filter_serializer = ChargerFilterSerializer(
                data={"station": station_param}
            )
            filter_serializer.is_valid(raise_exception=True)
            station_obj = filter_serializer.validated_data["station"]
            queryset = queryset.filter(station=station_obj)

        return queryset


class ChargerAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        charger_id = self.kwargs.get("charger_id") or self.kwargs.get("pk")
        charger = get_object_or_404(
            Charger.objects.select_related("station"),
            id=charger_id,
        )

        if not charger.is_active:
            return Response(
                {"detail": "Charger is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not charger.station.is_active:
            return Response(
                {"detail": "Charging station is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if charger.status in [Charger.Status.OFFLINE, Charger.Status.MAINTENANCE]:
            return Response(
                {
                    "detail": (
                        f"Charger is currently {charger.get_status_display().lower()} "
                        "and unavailable for bookings."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        query_serializer = ChargerAvailabilityQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)
        start = query_serializer.validated_data["start"]
        end = query_serializer.validated_data["end"]

        # Query overlapping bookings: start_time < end AND end_time > start, excluding CANCELLED
        overlapping_bookings = (
            Booking.objects.filter(
                charger=charger,
                start_time__lt=end,
                end_time__gt=start,
            )
            .exclude(status=Booking.Status.CANCELLED)
            .order_by("start_time")
            .values("start_time", "end_time")
        )

        booked_intervals = [
            {
                "start_time": _format_utc_iso(b["start_time"]),
                "end_time": _format_utc_iso(b["end_time"]),
            }
            for b in overlapping_bookings
        ]

        return Response(
            {
                "charger_id": charger.id,
                "start": _format_utc_iso(start),
                "end": _format_utc_iso(end),
                "slot_duration_minutes": 30,
                "booked_intervals": booked_intervals,
            },
            status=status.HTTP_200_OK,
        )
