import json
from unittest.mock import Mock, patch

import pytest
from requests import ConnectionError, RequestException, Timeout


@pytest.mark.usefixtures("api_adapter")
class TestAPIAdapter:
    """Тесты для APIAdapter"""

    def test_init(self, api_adapter):
        """Тест инициализации класса"""
        assert api_adapter.openstreetmap_url == "https://nominatim.openstreetmap.org/search"
        assert api_adapter.opensky_url == "https://opensky-network.org/api/states/all?"
        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_success(self, mock_get, api_adapter, mock_response_success, mock_response_opensky):
        """Тест успешного получения данных о самолетах"""
        mock_get.side_effect = [mock_response_success, mock_response_opensky]

        api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes == {
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
        assert mock_get.call_count == 2

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_invalid_country_empty(self, mock_get, api_adapter):
        """Тест с пустым названием страны"""
        with pytest.raises(ValueError, match="Некорректное название страны:"):
            api_adapter.get_aeroplanes("")
        mock_get.assert_not_called()

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_invalid_country_not_string(self, mock_get, api_adapter):
        """Тест с нестроковым названием страны"""
        with pytest.raises(ValueError, match="Некорректное название страны:"):
            api_adapter.get_aeroplanes(123)
        mock_get.assert_not_called()

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_empty_data(self, mock_get, api_adapter, mock_empty_response):
        """Тест когда данные по стране не найдены"""
        mock_get.return_value = mock_empty_response

        api_adapter.get_aeroplanes("UnknownCountry")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_timeout(self, mock_get, api_adapter):
        """Тест таймаута при запросе"""
        mock_get.side_effect = Timeout("Connection timeout")

        with pytest.raises(ConnectionError, match="Превышено время ожидания ответа от OpenStreetMap"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_connection_error(self, mock_get, api_adapter):
        """Тест ошибки соединения"""
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(ConnectionError, match="Connection failed"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_request_exception(self, mock_get, api_adapter):
        """Тест общей ошибки запроса"""
        mock_get.side_effect = RequestException("Request failed")

        with pytest.raises(RequestException, match="Request failed"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_json_decode_error(self, mock_get, api_adapter):
        """Тест ошибки парсинга JSON"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.text = "Invalid JSON"

        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Некорректный формат данных от OpenStreetMap"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_missing_coordinates(self, mock_get, api_adapter):
        """Тест отсутствия координат в ответе OpenStreetMap"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{}]  # Пустой словарь без boundingbox

        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Не удалось получить координаты для страны"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_invalid_coordinates_count(self, mock_get, api_adapter):
        """Тест некорректного количества координат"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"boundingbox": ["50.0", "60.0"]}]  # Только 2 координаты вместо 4

        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Некорректные координаты для страны"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_opensky_timeout(self, mock_get, api_adapter, mock_response_success):
        """Тест таймаута при запросе к OpenSky"""
        mock_get.side_effect = [mock_response_success, Timeout("OpenSky timeout")]

        with pytest.raises(ConnectionError, match="Превышено время ожидания ответа от OpenSky"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_opensky_connection_error(self, mock_get, api_adapter, mock_response_success):
        """Тест ошибки соединения с OpenSky"""
        mock_get.side_effect = [mock_response_success, ConnectionError("OpenSky connection failed")]

        with pytest.raises(ConnectionError, match="OpenSky connection failed"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None

    @patch("src.api_adapter.get")
    def test_get_aeroplanes_opensky_json_error(self, mock_get, api_adapter, mock_response_success):
        """Тест ошибки парсинга JSON от OpenSky"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.text = "Invalid JSON"

        mock_get.side_effect = [mock_response_success, mock_response]

        with pytest.raises(ValueError, match="Некорректный формат данных от OpenSky"):
            api_adapter.get_aeroplanes("Russia")

        assert api_adapter.aeroplanes is None
