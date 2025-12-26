"""Tests for environment polling service."""

import pytest

import app.services.environment.polling as polling_module
from app.services.environment.polling import (
    EnvironmentPollingService,
    get_polling_service,
)


class TestEnvironmentPollingService:
    """Tests for EnvironmentPollingService."""

    def test_init_with_mock_sensors(self):
        """Test initialization with mock sensors enabled."""
        service = EnvironmentPollingService(use_mock_sensors=True)
        assert service._use_mock is True
        assert service._running is False

    def test_init_without_mock_sensors(self):
        """Test initialization with mock sensors disabled."""
        service = EnvironmentPollingService(use_mock_sensors=False)
        assert service._use_mock is False

    def test_set_session_factory(self):
        """Test setting the session factory."""
        service = EnvironmentPollingService()

        def mock_factory():
            pass

        service.set_session_factory(mock_factory)
        assert service._session_factory is mock_factory

    def test_get_latest_reading_returns_none_initially(self):
        """Test that get_latest_reading returns None when no readings exist."""
        service = EnvironmentPollingService()
        assert service.get_latest_reading(1) is None

    def test_get_all_latest_readings_returns_empty_dict_initially(self):
        """Test that get_all_latest_readings returns empty dict initially."""
        service = EnvironmentPollingService()
        assert service.get_all_latest_readings() == {}

    @pytest.mark.asyncio
    async def test_start_without_session_factory_logs_error(self):
        """Test that starting without session factory logs error and returns."""
        service = EnvironmentPollingService()
        await service.start()
        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping when service is not running."""
        service = EnvironmentPollingService()
        await service.stop()  # Should not raise


class TestGetPollingService:
    """Tests for get_polling_service singleton."""

    @pytest.fixture(autouse=True)
    def reset_global_state(self):
        """Reset global polling service state before and after each test."""
        # Reset before test
        polling_module._polling_service = None
        yield
        # Reset after test to avoid polluting other tests
        polling_module._polling_service = None

    def test_returns_same_instance(self):
        """Test that get_polling_service returns the same instance."""
        service1 = get_polling_service()
        service2 = get_polling_service()
        assert service1 is service2

    def test_returns_environment_polling_service(self):
        """Test that get_polling_service returns EnvironmentPollingService."""
        service = get_polling_service()
        assert isinstance(service, EnvironmentPollingService)
