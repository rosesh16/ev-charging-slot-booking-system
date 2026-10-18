from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers

from bookings.models import Booking
from stations.models import Charger
from stations.serializers import ChargerSerializer
from vehicles.models import Vehicle
from vehicles.serializers import VehicleSerializer


class BookingReadSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.id")
    vehicle = VehicleSerializer(read_only=True)
    charger = ChargerSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "vehicle",
            "charger",
            "start_time",
            "end_time",
            "status",
            "created_at",
            "cancelled_at",
        ]


class BookingCreateSerializer(serializers.Serializer):
    charger = serializers.PrimaryKeyRelatedField(
        queryset=Charger.objects.all(),
        error_messages={
            "does_not_exist": "Charger does not exist.",
            "incorrect_type": "Charger ID must be a valid integer.",
        },
    )
    vehicle = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        error_messages={
            "does_not_exist": "Vehicle does not exist.",
            "incorrect_type": "Vehicle ID must be a valid integer.",
        },
    )
    start_time = serializers.DateTimeField(required=True)
    end_time = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError(
                {"detail": "Authentication required."}
            )

        user = request.user
        vehicle = attrs.get("vehicle")
        charger = attrs.get("charger")
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        # 1. Vehicle ownership
        if vehicle.owner_id != user.id:
            raise serializers.ValidationError(
                {"vehicle": "The selected vehicle does not belong to you."}
            )

        # 2. Exactly 30 minutes duration
        if end_time <= start_time or (end_time - start_time) != timedelta(minutes=30):
            raise serializers.ValidationError(
                {"end_time": "Booking duration must be exactly 30 minutes."}
            )

        # 3. Future start time
        if start_time <= timezone.now():
            raise serializers.ValidationError(
                {"start_time": "Booking start time must be in the future."}
            )

        # 4. Charger and station active check
        if not charger.is_active:
            raise serializers.ValidationError(
                {"charger": "Selected charger is inactive."}
            )
        if not charger.station.is_active:
            raise serializers.ValidationError(
                {"charger": "Charging station is inactive."}
            )

        # 5. Charger availability check
        if charger.status in [Charger.Status.OFFLINE, Charger.Status.MAINTENANCE]:
            raise serializers.ValidationError(
                {
                    "charger": (
                        f"Charger is currently {charger.get_status_display().lower()} "
                        "and unavailable for bookings."
                    )
                }
            )

        return attrs
