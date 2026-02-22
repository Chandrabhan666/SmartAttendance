from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Ticket


class TicketAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="apiuser123")
        token_response = self.client.post(
            "/api/token/",
            {"username": "apiuser", "password": "apiuser123"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        self.sample_payload = {
            "title": "WiFi not working",
            "description": "No internet in block A",
            "category": "network",
            "priority": "high",
        }

    def test_create_ticket(self):
        response = self.client.post("/tickets/", self.sample_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "open")

    def test_filter_search_order_pagination(self):
        Ticket.objects.create(
            title="WiFi down in hostel",
            description="No internet in hostel B",
            category="network",
            priority="high",
        )
        Ticket.objects.create(
            title="Projector issue",
            description="Classroom projector not starting",
            category="classroom",
            priority="low",
            status="closed",
        )

        response = self.client.get(
            "/tickets/?category=network&search=WiFi&ordering=priority&page=1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)
