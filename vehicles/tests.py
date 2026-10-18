from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from vehicles.models import Vehicle

User = get_user_model()


class VehicleApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("vehicle-list-create")
        self.user_a = User.objects.create_user(
            email="usera@example.com",
            username="usera",
            password="StrongPassword123!",
        )
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(
            email="userb@example.com",
            username="userb",
            password="StrongPassword123!",
        )
        self.token_b = Token.objects.create(user=self.user_b)

        self.valid_payload = {
            "registration_number": "MH12AB1234",
            "make": "Tesla",
            "model": "Model 3",
            "battery_capacity_kwh": 75.00,
        }

    def test_unauthenticated_access_rejected(self):
        # GET request without authentication
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # POST request without authentication
        post_response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(post_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_vehicle_creation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["registration_number"], "MH12AB1234")
        self.assertEqual(response.data["make"], "Tesla")
        self.assertEqual(response.data["model"], "Model 3")
        self.assertEqual(float(response.data["battery_capacity_kwh"]), 75.00)
        self.assertEqual(response.data["owner"], self.user_a.id)

        # Check DB
        vehicle = Vehicle.objects.get(registration_number="MH12AB1234")
        self.assertEqual(vehicle.owner, self.user_a)

    def test_automatic_assignment_of_authenticated_user_as_owner(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vehicle = Vehicle.objects.get(id=response.data["id"])
        self.assertEqual(vehicle.owner, self.user_a)

    def test_attempt_to_create_vehicle_for_another_user_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        tampered_payload = {
            **self.valid_payload,
            "owner": self.user_b.id,
            "owner_id": self.user_b.id,
        }
        response = self.client.post(self.url, tampered_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify the owner is still user_a, NOT user_b
        vehicle = Vehicle.objects.get(id=response.data["id"])
        self.assertEqual(vehicle.owner, self.user_a)
        self.assertEqual(response.data["owner"], self.user_a.id)

    def test_listing_only_authenticated_user_vehicles(self):
        # Create vehicle for User A
        Vehicle.objects.create(
            owner=self.user_a,
            registration_number="MH12AA1111",
            make="Tata",
            model="Nexon EV",
            battery_capacity_kwh=40.50,
        )

        # Create vehicle for User B
        Vehicle.objects.create(
            owner=self.user_b,
            registration_number="DL01BB2222",
            make="MG",
            model="ZS EV",
            battery_capacity_kwh=50.30,
        )

        # User A requests their vehicle list
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        response_a = self.client.get(self.url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_a.data), 1)
        self.assertEqual(response_a.data[0]["registration_number"], "MH12AA1111")

        # User B requests their vehicle list
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        response_b = self.client.get(self.url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_b.data), 1)
        self.assertEqual(response_b.data[0]["registration_number"], "DL01BB2222")

    def test_duplicate_registration_number_rejection(self):
        # Create vehicle with registration number
        Vehicle.objects.create(
            owner=self.user_a,
            registration_number="MH12AB1234",
            make="Tesla",
            model="Model 3",
            battery_capacity_kwh=75.00,
        )

        # Attempt to create duplicate vehicle by User B
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_b.key}")
        duplicate_payload = {
            "registration_number": "mh12ab1234",  # Same number case-insensitive
            "make": "Hyundai",
            "model": "Ioniq 5",
            "battery_capacity_kwh": 72.60,
        }
        response = self.client.post(self.url, duplicate_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("registration_number", response.data)
