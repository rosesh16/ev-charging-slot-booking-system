from rest_framework import serializers
from vehicles.models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "owner",
            "registration_number",
            "make",
            "model",
            "battery_capacity_kwh",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "created_at"]

    def validate_registration_number(self, value):
        normalized = value.strip().upper()
        if not normalized:
            raise serializers.ValidationError("Registration number cannot be empty.")
        # Check uniqueness case-insensitively or exact match
        qs = Vehicle.objects.filter(registration_number__iexact=normalized)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A vehicle with this registration number already exists."
            )
        return normalized
