from unittest.mock import Mock, patch
import pytest
import psycopg2

from src.fill_db import get_connection, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


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


@pytest.fixture
def mock_logger():
    """Фикстура для мока логгера"""
    with patch('src.fill_db.logger') as mock:
        yield mock


@pytest.fixture
def mock_psycopg2():
    """Фикстура для мока psycopg2"""
    with patch('src.fill_db.psycopg2') as mock:
        yield mock


@pytest.fixture
def mock_successful_connection(mock_psycopg2):
    """Фикстура для успешного подключения"""
    mock_conn = Mock()
    mock_psycopg2.connect.return_value = mock_conn
    return mock_psycopg2  # Возвращаем мок psycopg2, а не соединение


@pytest.fixture
def mock_failed_connection(mock_psycopg2):
    """Фикстура для неудачного подключения"""
    mock_psycopg2.connect.side_effect = psycopg2.OperationalError("Connection failed")
    return mock_psycopg2


@pytest.fixture
def mock_cursor():
    """Фикстура для мока курсора"""
    mock_cur = Mock()
    return mock_cur


@pytest.fixture
def mock_connection_with_cursor(mock_cursor):
    """Фикстура для мока соединения с курсором"""
    mock_conn = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def mock_get_connection():
    """Фикстура для мока get_connection"""
    with patch('src.fill_db.get_connection') as mock:
        yield mock


@pytest.fixture
def mock_logger_db_manager():
    """Фикстура для мока логгера"""
    with patch('src.db_manager.logger') as mock:
        yield mock


@pytest.fixture
def mock_psycopg2_db_manager():
    """Фикстура для мока psycopg2"""
    with patch('src.db_manager.psycopg2') as mock:
        yield mock
