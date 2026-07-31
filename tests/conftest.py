from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def api_adapter():
    """Фикстура для создания экземпляра APIAdapter"""
    with patch("src.api_adapter.log_manager"):
        from src.api_adapter import APIAdapter

        adapter = APIAdapter()
        return adapter


@pytest.fixture
def mock_response_success():
    """Фикстура успешного ответа от OpenStreetMap"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [{"boundingbox": ["50.0", "60.0", "10.0", "20.0"]}]
    return mock


@pytest.fixture
def mock_response_opensky():
    """Фикстура успешного ответа от OpenSky"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "states": [
            [
                "abc123",
                "callsign",
                "country",
                1000,
                2000,
                300,
                400,
                500,
                600,
                700,
                800,
                900,
                1000,
                1100,
                1200,
                1300,
                1400,
            ]
        ]
    }
    return mock


@pytest.fixture
def mock_empty_response():
    """Фикстура пустого ответа от OpenStreetMap"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = []
    return mock
