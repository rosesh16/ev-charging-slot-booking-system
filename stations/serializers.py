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
