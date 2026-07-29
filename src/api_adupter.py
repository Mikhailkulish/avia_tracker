import json

from requests import ConnectionError, RequestException, Timeout, get

from src.base_api_adapter import BaseAPIAdapter
from src.logger_manager import log_manager

logger = log_manager.get_logger(__name__)


class APIAdapter(BaseAPIAdapter):
    """Класс получения данных по поиску самолетов над страной"""

    openstreetmap_url: str
    opensky_url: str
    aeroplanes: None

    def __init__(self) -> None:
        """Метод инициализации класса"""
        self.openstreetmap_url = "https://nominatim.openstreetmap.org/search"
        self.opensky_url = "https://opensky-network.org/api/states/all?"
        self.aeroplanes = None
        logger.info("Объект класса инициализирован")

    def get_aeroplanes(self, country: str) -> None:
        """Метод поиска самолетов по странам"""
        if not country or not isinstance(country, str):
            error_msg = f"Некорректное название страны: {country}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        headers_nominatim = {
            "User-Agent": "test-app",
        }

        # Указываем параметры: в каком формате возвращать данные и максимальную длину списка стран в ответе.
        params_nominatim = {
            "country": country,
            "format": "json",
            "limit": 1,
        }
        logger.info(f"Сформирован запрос на получение координат страны {country}")

        try:
            response = get(url=self.openstreetmap_url, params=params_nominatim, headers=headers_nominatim, timeout=10)
            logger.info(f"Запрос к OpenStreetMap выполнен. Статус: {response.status_code}")

            response.raise_for_status()

        except Timeout as e:
            logger.error(f"Таймаут при запросе к OpenStreetMap для страны {country}: {e}")
            self.aeroplanes = None
            raise ConnectionError("Превышено время ожидания ответа " f"от OpenStreetMap для страны {country}") from e

        except ConnectionError as e:
            logger.error(f"Ошибка соединения с OpenStreetMap для страны {country}: {e}")
            self.aeroplanes = None
            raise

        except RequestException as e:
            logger.error(f"Ошибка при запросе к OpenStreetMap для страны {country}: {e}")
            self.aeroplanes = None
            raise

        try:
            data = response.json()
            logger.info("Ответ по запросу преобразован в словарь")

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON ответа от OpenStreetMap для страны {country}: {e}")
            logger.debug(f"Содержимое ответа: {response.text[:200]}...")  # Логируем часть ответа для отладки
            self.aeroplanes = None
            raise ValueError(f"Некорректный формат данных от OpenStreetMap для страны {country}") from e

            # Проверяем, что данные не пустые
        if not data:
            logger.warning(f"Данные по стране {country} не найдены в OpenStreetMap")
            self.aeroplanes = None
            return

        try:
            geo_coordinates = data[0].get("boundingbox")

            # Проверяем, что координаты получены
            if not geo_coordinates:
                logger.error(f"Координаты для страны {country} не найдены в ответе OpenStreetMap")
                self.aeroplanes = None
                raise ValueError(f"Не удалось получить координаты для страны {country}")

            # Проверяем, что координаты содержат 4 значения
            if len(geo_coordinates) != 4:
                logger.error(f"Неверное количество координат для страны {country}: {len(geo_coordinates)}")
                self.aeroplanes = None
                raise ValueError(f"Некорректные координаты для страны {country}")

            logger.info(f"Из ответа извлечены координаты страны {country}: {geo_coordinates}")

        except (KeyError, IndexError) as e:
            logger.error(f"Ошибка при извлечении координат для страны {country}: {e}")
            logger.debug(f"Структура данных: {data}")
            self.aeroplanes = None
            raise ValueError(f"Некорректная структура данных от OpenStreetMap для страны {country}") from e

        params = {
            "lamin": geo_coordinates[0],
            "lamax": geo_coordinates[1],
            "lomin": geo_coordinates[2],
            "lomax": geo_coordinates[3],
        }
        logger.info(f"Сформированы параметры для поиска самолетов над страной {country}: {params}")

        try:
            response = get(url=self.opensky_url, params=params, timeout=15)  # Для второго запроса чуть больше времени
            logger.info(f"Запрос к OpenSky выполнен. Статус: {response.status_code}")

            # Проверяем статус ответа
            response.raise_for_status()

        except Timeout as e:
            logger.error(f"Таймаут при запросе к OpenSky для страны {country}: {e}")
            self.aeroplanes = None
            raise ConnectionError(f"Превышено время ожидания ответа от OpenSky для страны {country}") from e

        except ConnectionError as e:
            logger.error(f"Ошибка соединения с OpenSky для страны {country}: {e}")
            self.aeroplanes = None
            raise

        except RequestException as e:
            logger.error(f"Ошибка при запросе к OpenSky для страны {country}: {e}")
            self.aeroplanes = None
            raise

        try:
            self.aeroplanes = response.json()
            logger.info(f"Результаты поиска самолетов над страной {country} сохранены в переменную")

            # Логируем количество найденных самолетов, если структура известна
            if isinstance(self.aeroplanes, dict) and "states" in self.aeroplanes:
                states_count = len(self.aeroplanes.get("states", []))
                logger.info(f"Найдено {states_count} самолетов над страной {country}")
            else:
                logger.debug(f"Структура ответа OpenSky: {type(self.aeroplanes)}")

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON ответа от OpenSky для страны {country}: {e}")
            logger.debug(f"Содержимое ответа: {response.text[:200]}...")
            self.aeroplanes = None
            raise ValueError(f"Некорректный формат данных от OpenSky для страны {country}") from e
