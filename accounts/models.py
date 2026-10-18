from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        DRIVER = "DRIVER", "Driver"
        OPERATOR = "OPERATOR", "Charging Operator"

    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.DRIVER,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email