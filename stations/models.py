from django.db import models


class Station(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.city}"


class Charger(models.Model):
    class ConnectorType(models.TextChoices):
        TYPE_2 = "TYPE_2", "Type 2"
        CCS2 = "CCS2", "CCS2"
        CHADEMO = "CHADEMO", "CHAdeMO"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        OFFLINE = "OFFLINE", "Offline"
        MAINTENANCE = "MAINTENANCE", "Under maintenance"

    station = models.ForeignKey(
        Station,
        on_delete=models.PROTECT,
        related_name="chargers",
    )
    name = models.CharField(max_length=100)
    connector_type = models.CharField(
        max_length=20,
        choices=ConnectorType.choices,
    )
    power_kw = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["station", "name"],
                name="unique_charger_name_per_station",
            ),
        ]

    def __str__(self):
        return f"{self.station.name} - {self.name}"