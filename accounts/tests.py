from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.valid_user_payload = {
            "email": "driver@example.com",
            "username": "driver1",
            "password": "StrongPassword123!",
            "phone_number": "+1234567890",
        }

    def test_successful_registration(self):
        response = self.client.post(self.register_url, self.valid_user_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "driver@example.com")
        self.assertEqual(user_data["username"], "driver1")
        self.assertEqual(user_data["role"], User.Role.DRIVER)
        self.assertNotIn("password", user_data)

        # Verify DB state and password hashing
        user = User.objects.get(email="driver@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertNotEqual(user.password, "StrongPassword123!")

        # Verify token in DB matches
        token = Token.objects.get(user=user)
        self.assertEqual(token.key, response.data["token"])

    def test_duplicate_email_rejection(self):
        self.client.post(self.register_url, self.valid_user_payload)

        # Attempt to register with the exact same email (different case)
        duplicate_payload = {
            "email": "DRIVER@EXAMPLE.COM",
            "username": "driver2",
            "password": "AnotherStrongPassword123!",
        }
        response = self.client.post(self.register_url, duplicate_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_password_validation(self):
        weak_payload = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",  # Fails minimum length validator
        }
        response = self.client.post(self.register_url, weak_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_role_escalation_prevented(self):
        payload = {
            **self.valid_user_payload,
            "role": "OPERATOR",
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="driver@example.com")
        self.assertEqual(user.role, User.Role.DRIVER)

    def test_successful_login(self):
        User.objects.create_user(
            email="login@example.com",
            username="loginuser",
            password="StrongPassword123!",
        )

        response = self.client.post(
            self.login_url,
            {"email": "login@example.com", "password": "StrongPassword123!"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["email"], "login@example.com")

        user = User.objects.get(email="login@example.com")
        token = Token.objects.get(user=user)
        self.assertEqual(response.data["token"], token.key)

    def test_login_invalid_password(self):
        User.objects.create_user(
            email="login@example.com",
            username="loginuser",
            password="StrongPassword123!",
        )

        response = self.client.post(
            self.login_url,
            {"email": "login@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("token", response.data)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.login_url,
            {"email": "nonexistent@example.com", "password": "AnyPassword123!"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_token_authentication(self):
        user = User.objects.create_user(
            email="authuser@example.com",
            username="authuser",
            password="StrongPassword123!",
        )
        token = Token.objects.create(user=user)

        # Access vehicles endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(reverse("vehicle-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
