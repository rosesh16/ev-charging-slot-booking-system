from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from stations.models import Charger, Station


class StationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = [
            "id",
            "name",
            "address",
            "city",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
        ]


class StationChargerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charger
        fields = [
            "id",
            "name",
            "connector_type",
            "power_kw",
            "status",
            "is_active",
        ]


class StationDetailSerializer(serializers.ModelSerializer):
    chargers = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = [
            "id",
            "name",
            "address",
            "city",
            "latitude",
            "longitude",
            "is_active",
            "chargers",
            "created_at",
        ]

    def get_chargers(self, obj):
        active_chargers = obj.chargers.filter(is_active=True).order_by("name")
        return StationChargerSerializer(active_chargers, many=True).data


class StationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "name", "address", "city"]


class ChargerSerializer(serializers.ModelSerializer):
    station = StationSummarySerializer(read_only=True)

    class Meta:
        model = Charger
        fields = [
            "id",
            "station",
            "name",
            "connector_type",
            "power_kw",
            "status",
            "is_active",
        ]


class ChargerFilterSerializer(serializers.Serializer):
    station = serializers.PrimaryKeyRelatedField(
        queryset=Station.objects.filter(is_active=True),
        error_messages={
            "does_not_exist": "Station does not exist or is inactive.",
            "incorrect_type": "Station ID must be a valid integer.",
        },
    )


class ChargerAvailabilityQuerySerializer(serializers.Serializer):
    start = serializers.CharField(required=True)
    end = serializers.CharField(required=True)

    def validate_start(self, value):
        dt = parse_datetime(value)
        if dt is None:
            raise serializers.ValidationError("Must be a valid ISO 8601 timestamp.")
        if timezone.is_naive(dt):
            raise serializers.ValidationError(
                "Timestamp must be timezone-aware (e.g. including 'Z' or '+00:00')."
            )
        return dt

    def validate_end(self, value):
        dt = parse_datetime(value)
        if dt is None:
            raise serializers.ValidationError("Must be a valid ISO 8601 timestamp.")
        if timezone.is_naive(dt):
            raise serializers.ValidationError(
                "Timestamp must be timezone-aware (e.g. including 'Z' or '+00:00')."
            )
        return dt

    def validate(self, attrs):
        start = attrs.get("start")
        end = attrs.get("end")

        if start >= end:
            raise serializers.ValidationError(
                {"end": "'start' must be earlier than 'end'."}
            )

        if end <= timezone.now():
            raise serializers.ValidationError(
                {"end": "The requested time window must end in the future."}
            )

        if end - start > timedelta(hours=24):
            raise serializers.ValidationError(
                {"end": "The requested time window cannot exceed 24 hours."}
            )

        return attrs
