import psycopg2

from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from src.logger_manager import log_manager

logger = log_manager.get_logger("db_manager")


class DBManager:
    """Класс для управления запросами к базе данных"""

    def __init__(self):
        """Инициализация подключения к БД"""
        self.connection = None
        self._connect()
        logger.info("DBManager инициализирован")

    def _connect(self):
        """Устанавливает соединение с БД"""
        try:
            self.connection = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
            )
            self.connection.autocommit = True
            logger.info(f"Подключение к БД {DB_NAME} установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise

    def close(self):
        """Закрывает соединение с БД"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Соединение с БД закрыто")

    def get_countries_and_aeroplanes_count(self) -> list:
        """Получает список всех стран и количество самолетов."""
        query = """
            SELECT
                c.name as country,
                COUNT(DISTINCT t.icao24) as aircraft_count
            FROM countries c
            LEFT JOIN tracks t ON c.id = t.country_id
            GROUP BY c.id, c.name
            ORDER BY aircraft_count DESC
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query)
            result = cur.fetchall()
            cur.close()

            logger.info(f"Получен список стран с количеством самолетов: {len(result)} записей")
            return result

        except Exception as e:
            logger.error(f"Ошибка получения списка стран: {e}")
            raise

    def get_all_aeroplanes(self) -> list:
        """Получает список всех воздушных судов с их последними данными."""
        query = """
            SELECT
                a.icao24,
                a.callsign,
                a.origin_country,
                MAX(t.timestamp) as last_seen,
                COUNT(t.id) as track_count
            FROM aircraft a
            LEFT JOIN tracks t ON a.id = t.aircraft_id
            GROUP BY a.id, a.icao24, a.callsign, a.origin_country
            ORDER BY track_count DESC
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query)
            result = cur.fetchall()
            cur.close()

            logger.info(f"Получен список всех самолетов: {len(result)} записей")
            return result

        except Exception as e:
            logger.error(f"Ошибка получения списка самолетов: {e}")
            raise

    def get_avg_speed(self) -> float:
        """Получает среднюю скорость по всем самолетам."""
        query = """
            SELECT
                AVG(velocity) as avg_speed
            FROM tracks
            WHERE velocity IS NOT NULL
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query)
            result = cur.fetchone()[0]
            cur.close()

            avg_speed = float(result) if result is not None else 0.0
            logger.info(f"Средняя скорость: {avg_speed:.2f} м/с")
            return avg_speed

        except Exception as e:
            logger.error(f"Ошибка получения средней скорости: {e}")
            raise

    def get_aeroplanes_with_higher_speed(self) -> list:
        """Получает список всех самолетов, у которых скорость выше средней."""
        query = """
                WITH avg_speed_cte AS (
                    SELECT AVG(velocity) as avg_speed
                    FROM tracks
                    WHERE velocity IS NOT NULL
                )
                SELECT
                    t.icao24,
                    a.callsign,
                    MAX(t.velocity) as max_speed,
                    (SELECT avg_speed FROM avg_speed_cte) as avg_speed
                FROM tracks t
                JOIN aircraft a ON t.aircraft_id = a.id
                WHERE t.velocity IS NOT NULL
                GROUP BY t.icao24, a.callsign
                HAVING MAX(t.velocity) > (SELECT avg_speed FROM avg_speed_cte)
                ORDER BY max_speed DESC
            """

        try:
            cur = self.connection.cursor()
            cur.execute(query)
            result = cur.fetchall()
            cur.close()

            logger.info(f"Получен список самолетов со скоростью выше средней: {len(result)} записей")
            return result

        except Exception as e:
            logger.error(f"Ошибка получения самолетов с высокой скоростью: {e}")
            raise

    def get_aeroplanes_with_keyword(self, keyword: str) -> list:
        """Получает список всех самолетов, в позывном которых содержатся переданные символы."""
        if not keyword or not isinstance(keyword, str):
            logger.warning("Передан пустой или некорректный ключевой слово")
            return []

        query = """
            SELECT
                a.icao24,
                a.callsign,
                a.origin_country,
                COUNT(t.id) as track_count
            FROM aircraft a
            LEFT JOIN tracks t ON a.id = t.aircraft_id
            WHERE a.callsign ILIKE %s
            GROUP BY a.id, a.icao24, a.callsign, a.origin_country
            ORDER BY track_count DESC
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query, (f"%{keyword}%",))
            result = cur.fetchall()
            cur.close()

            logger.info(f"Поиск самолетов с ключевым словом '{keyword}': найдено {len(result)} записей")
            return result

        except Exception as e:
            logger.error(f"Ошибка поиска самолетов с ключевым словом '{keyword}': {e}")
            raise

    # Дополнительные методы

    def get_aeroplanes_by_country(self, country_name: str) -> list:
        """Получает список самолетов для конкретной страны."""
        query = """
            SELECT
                t.icao24,
                a.callsign,
                t.altitude,
                t.latitude,
                t.longitude,
                t.timestamp
            FROM tracks t
        JOIN aircraft a ON t.aircraft_id = a.id
        JOIN countries c ON t.country_id = c.id
        WHERE c.name = %s
        ORDER BY t.timestamp DESC
        LIMIT 100
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query, (country_name,))
            result = cur.fetchall()
            cur.close()

            logger.info(f"Получен список самолетов для страны {country_name}: {len(result)} записей")
            return result

        except Exception as e:
            logger.error(f"Ошибка получения самолетов для страны {country_name}: {e}")
            raise

    def get_statistics_summary(self) -> dict:
        """Получает сводную статистику по базе данных."""
        query = """
            SELECT
                (SELECT COUNT(*) FROM countries) as total_countries,
                (SELECT COUNT(*) FROM aircraft) as total_aircraft,
                (SELECT COUNT(*) FROM tracks) as total_tracks,
                (SELECT COUNT(DISTINCT icao24) FROM tracks) as unique_icao,
                (SELECT COUNT(DISTINCT country_id) FROM tracks) as active_countries
        """

        try:
            cur = self.connection.cursor()
            cur.execute(query)
            row = cur.fetchone()
            cur.close()

            result = {
                "total_countries": row[0],
                "total_aircraft": row[1],
                "total_tracks": row[2],
                "unique_icao": row[3],
                "active_countries": row[4],
            }

            logger.info(f"Получена сводная статистика: {result}")
            return result

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            raise

    def print_countries_and_aeroplanes_count(self):
        """Выводит список стран с количеством самолетов в удобном формате."""
        data = self.get_countries_and_aeroplanes_count()

        print("\n" + "=" * 60)
        print("СТРАНЫ И КОЛИЧЕСТВО САМОЛЕТОВ")
        print("=" * 60)

        if not data:
            print("Нет данных")
            return

        total = 0
        for country, count in data:
            print(f"  {country}: {count} самолетов")
            total += count

        print("-" * 60)
        print(f"  ВСЕГО: {total} самолетов")
        print("=" * 60 + "\n")

    def print_all_aeroplanes(self, limit: int = 20):
        """Выводит список всех самолетов (первые N)."""
        data = self.get_all_aeroplanes()

        print("\n" + "=" * 80)
        print("СПИСОК ВСЕХ САМОЛЕТОВ")
        print("=" * 80)
        print(f"{'ICAO':<10} {'Позывной':<12} {'Страна':<20} {'Последний раз':<20} {'Треков':<8}")
        print("-" * 80)

        for i, (icao, callsign, origin, last_seen, track_count) in enumerate(data[:limit], 1):
            callsign_display = callsign or "Нет данных"
            origin_display = origin or "Неизвестно"
            last_seen_display = last_seen.strftime("%Y-%m-%d %H:%M") if last_seen else "Нет данных"
            print(f"{icao:<10} {callsign_display:<12} {origin_display:<20} {last_seen_display:<20} {track_count:<8}")

        if len(data) > limit:
            print(f"\n... и еще {len(data) - limit} записей")
        print("=" * 80 + "\n")

    def print_aeroplanes_with_keyword(self, keyword: str):
        """Выводит список самолетов с ключевым словом в позывном."""
        data = self.get_aeroplanes_with_keyword(keyword)

        print(f"\n{'=' * 60}")
        print(f"САМОЛЕТЫ С КЛЮЧЕВЫМ СЛОВОМ '{keyword.upper()}'")
        print("=" * 60)

        if not data:
            print(f"Самолеты с ключевым словом '{keyword}' не найдены")
            return

        print(f"{'ICAO':<10} {'Позывной':<15} {'Страна':<20} {'Треков':<8}")
        print("-" * 60)

        for icao, callsign, origin, track_count in data:
            callsign_display = callsign or "Нет данных"
            origin_display = origin or "Неизвестно"
            print(f"{icao:<10} {callsign_display:<15} {origin_display:<20} {track_count:<8}")

        print(f"\nВсего: {len(data)} самолетов")
        print("=" * 60 + "\n")

    def print_avg_speed(self):
        """Выводит среднюю скорость."""
        avg_speed = self.get_avg_speed()

        print("\n" + "=" * 60)
        print("СТАТИСТИКА СКОРОСТИ")
        print("=" * 60)

        if avg_speed == 0:
            print("Нет данных о скорости")
        else:
            print(f"Средняя скорость: {avg_speed:.2f} м/с")
            print(f"Средняя скорость: {avg_speed * 3.6:.2f} км/ч")

        print("=" * 60 + "\n")

    def print_aeroplanes_with_higher_speed(self):
        """Выводит список самолетов со скоростью выше средней."""
        data = self.get_aeroplanes_with_higher_speed()

        print("\n" + "=" * 80)
        print("САМОЛЕТЫ СО СКОРОСТЬЮ ВЫШЕ СРЕДНЕЙ")
        print("=" * 80)

        if not data:
            print("Нет данных о самолетах с высокой скоростью")
            return

        print(f"{'ICAO':<10} {'Позывной':<12} {'Макс. скорость (м/с)':<20} {'Ср. скорость (м/с)':<18}")
        print("-" * 80)

        for icao, callsign, max_speed, avg_speed in data:
            callsign_display = callsign or "Нет данных"
            max_speed_display = f"{max_speed:.2f}" if max_speed else "Нет данных"
            avg_speed_display = f"{avg_speed:.2f}" if avg_speed else "Нет данных"
            print(f"{icao:<10} {callsign_display:<12} {max_speed_display:<20} {avg_speed_display:<18}")

        print(f"\nВсего: {len(data)} самолетов")
        print("=" * 80 + "\n")
