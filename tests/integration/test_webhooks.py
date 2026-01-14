"""Integration tests for webhook endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, test_client: TestClient):
        """Health endpoint should return 200."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSmartLeadWebhook:
    """Tests for SmartLead webhook endpoint."""

    def test_smartlead_webhook_accepts_valid_payload(
        self,
        test_client: TestClient,
        sample_smartlead_payload: dict,
    ):
        """Valid SmartLead payload should be accepted."""
        response = test_client.post(
            "/webhook/smartlead",
            json=sample_smartlead_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "webhook_id" in data

    def test_smartlead_webhook_requires_event_type(self, test_client: TestClient):
        """Payload without event_type should fail validation."""
        response = test_client.post(
            "/webhook/smartlead",
            json={"lead_id": "123"},
        )

        assert response.status_code == 422  # Validation error


class TestConnectSafelyWebhook:
    """Tests for ConnectSafely webhook endpoint."""

    def test_connectsafely_webhook_accepts_valid_payload(
        self,
        test_client: TestClient,
        sample_connectsafely_payload: dict,
    ):
        """Valid ConnectSafely payload should be accepted."""
        response = test_client.post(
            "/webhook/connectsafely",
            json=sample_connectsafely_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "webhook_id" in data

    def test_connectsafely_webhook_requires_event_type(self, test_client: TestClient):
        """Payload without event_type should fail validation."""
        response = test_client.post(
            "/webhook/connectsafely",
            json={"profile_url": "https://linkedin.com/in/test"},
        )

        assert response.status_code == 422  # Validation error
