from unittest.mock import patch
from django.db import OperationalError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from stations.models import Charger, Station


class StationAndChargerApiTests(APITestCase):
    def setUp(self):
        self.station_list_url = reverse("station-list")
        self.charger_list_url = reverse("charger-list")
        self.health_url = reverse("health-check")

        self.active_station_1 = Station.objects.create(
            name="Downtown Supercharger",
            address="100 Main Street",
            city="Metropolis",
            latitude="18.922000",
            longitude="72.834700",
            is_active=True,
        )

        self.active_station_2 = Station.objects.create(
            name="Uptown Hub",
            address="200 North Avenue",
            city="Metropolis",
            latitude="18.950000",
            longitude="72.850000",
            is_active=True,
        )

        self.inactive_station = Station.objects.create(
            name="Decommissioned Station",
            address="999 Abandoned Way",
            city="Gotham",
            is_active=False,
        )

        # Chargers at active_station_1
        self.charger_1a = Charger.objects.create(
            station=self.active_station_1,
            name="Bay 1",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )
        self.charger_1b_inactive = Charger.objects.create(
            station=self.active_station_1,
            name="Bay 2 Inactive",
            connector_type=Charger.ConnectorType.TYPE_2,
            power_kw=22.00,
            status=Charger.Status.MAINTENANCE,
            is_active=False,
        )

        # Charger at active_station_2
        self.charger_2a = Charger.objects.create(
            station=self.active_station_2,
            name="Bay 1",
            connector_type=Charger.ConnectorType.CHADEMO,
            power_kw=60.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

        # Charger at inactive_station
        self.charger_inactive_st = Charger.objects.create(
            station=self.inactive_station,
            name="Ghost Bay",
            connector_type=Charger.ConnectorType.CCS2,
            power_kw=50.00,
            status=Charger.Status.AVAILABLE,
            is_active=True,
        )

    def test_anonymous_access_allowed(self):
        # Station list
        r = self.client.get(self.station_list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Station detail
        detail_url = reverse(
            "station-detail", kwargs={"pk": self.active_station_1.id}
        )
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Charger list
        r = self.client.get(self.charger_list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # Health endpoint
        r = self.client.get(self.health_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_active_stations_only(self):
        response = self.client.get(self.station_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        station_names = [s["name"] for s in response.data]
        self.assertIn("Downtown Supercharger", station_names)
        self.assertIn("Uptown Hub", station_names)
        self.assertNotIn("Decommissioned Station", station_names)

    def test_station_detail_and_nested_chargers(self):
        detail_url = reverse(
            "station-detail", kwargs={"pk": self.active_station_1.id}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data["id"], self.active_station_1.id)
        self.assertEqual(data["name"], "Downtown Supercharger")
        self.assertEqual(data["city"], "Metropolis")
        self.assertTrue(data["is_active"])

        # Check nested chargers: only active charger should be returned
        chargers = data["chargers"]
        self.assertEqual(len(chargers), 1)
        self.assertEqual(chargers[0]["id"], self.charger_1a.id)
        self.assertEqual(chargers[0]["name"], "Bay 1")
        self.assertEqual(chargers[0]["connector_type"], "CCS2")
        self.assertEqual(float(chargers[0]["power_kw"]), 50.00)
        self.assertEqual(chargers[0]["status"], "AVAILABLE")
        self.assertTrue(chargers[0]["is_active"])

    def test_station_detail_404_for_nonexistent_or_inactive(self):
        # Nonexistent station
        url_nonexistent = reverse("station-detail", kwargs={"pk": 99999})
        response = self.client.get(url_nonexistent)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Inactive station
        url_inactive = reverse(
            "station-detail", kwargs={"pk": self.inactive_station.id}
        )
        response = self.client.get(url_inactive)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_active_charger_filtering(self):
        response = self.client.get(self.charger_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_ids = [c["id"] for c in response.data]

        # Active chargers at active stations are included
        self.assertIn(self.charger_1a.id, charger_ids)
        self.assertIn(self.charger_2a.id, charger_ids)

        # Inactive charger at active station is excluded
        self.assertNotIn(self.charger_1b_inactive.id, charger_ids)

    def test_excluding_chargers_whose_stations_are_inactive(self):
        response = self.client.get(self.charger_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_ids = [c["id"] for c in response.data]

        # Active charger at inactive station must be excluded
        self.assertNotIn(self.charger_inactive_st.id, charger_ids)

    def test_filtering_chargers_by_station(self):
        response = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_1.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.charger_1a.id)
        self.assertEqual(
            response.data[0]["station"]["id"], self.active_station_1.id
        )

        response_2 = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_2.id}"
        )
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_2.data), 1)
        self.assertEqual(response_2.data[0]["id"], self.charger_2a.id)
        self.assertEqual(
            response_2.data[0]["station"]["id"], self.active_station_2.id
        )

    def test_invalid_or_nonexistent_station_filter_rejected(self):
        # Non-integer station parameter
        response_invalid = self.client.get(
            f"{self.charger_list_url}?station=invalid_abc"
        )
        self.assertEqual(response_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("station", response_invalid.data)

        # Nonexistent station ID
        response_nonexistent = self.client.get(
            f"{self.charger_list_url}?station=99999"
        )
        self.assertEqual(
            response_nonexistent.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("station", response_nonexistent.data)

        # Inactive station ID
        response_inactive = self.client.get(
            f"{self.charger_list_url}?station={self.inactive_station.id}"
        )
        self.assertEqual(
            response_inactive.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("station", response_inactive.data)

    def test_charger_response_fields(self):
        response = self.client.get(
            f"{self.charger_list_url}?station={self.active_station_1.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charger_data = response.data[0]

        expected_keys = {
            "id",
            "name",
            "connector_type",
            "power_kw",
            "status",
            "is_active",
            "station",
        }
        self.assertEqual(set(charger_data.keys()), expected_keys)

        station_data = charger_data["station"]
        self.assertEqual(station_data["id"], self.active_station_1.id)
        self.assertEqual(station_data["name"], "Downtown Supercharger")
        self.assertEqual(station_data["address"], "100 Main Street")
        self.assertEqual(station_data["city"], "Metropolis")

    def test_health_endpoint_success(self):
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": "healthy", "database": "connected"},
        )

    @patch("django.db.connection.ensure_connection")
    def test_health_endpoint_database_failure(self, mock_ensure_connection):
        mock_ensure_connection.side_effect = OperationalError(
            "Database connection failed"
        )
        response = self.client.get(self.health_url)
        self.assertEqual(
            response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
        )
        self.assertEqual(
            response.data,
            {"status": "unhealthy", "database": "disconnected"},
        )
