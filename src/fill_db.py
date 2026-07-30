import psycopg2
import time
from src.api_adapter import APIAdapter
from src.config import (
    DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT,
    REQUEST_DELAY, MIN_COUNTRIES, MAX_AIRCRAFT_PER_COUNTRY
)
from src.logger_manager import log_manager

logger = log_manager.get_logger("db_filler")


# Подключение к базе данных
def get_connection(dbname: str = DB_NAME):
    """Создает соединение с БД"""
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.debug(f"Подключение к БД {dbname} установлено")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД {dbname}: {e}")
        raise


# Создание базы данных
def create_db() -> None:
    """Создает БД и таблицы"""
    logger.info("Начало создания базы данных")

    try:
        # Подключаемся к системной БД postgres
        conn = get_connection("postgres")
        conn.autocommit = True
        cur = conn.cursor()

        # Создаем БД если нет
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"База данных '{DB_NAME}' создана")
        else:
            logger.info(f"База данных '{DB_NAME}' уже существует")
        conn.close()

        # Подключаемся к нашей БД
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()

        # Таблица стран (2 колонки: id, name)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        logger.debug("Таблица countries создана/проверена")

        # Таблица самолетов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aircraft (
                id SERIAL PRIMARY KEY,
                icao24 VARCHAR(6) NOT NULL UNIQUE,
                callsign VARCHAR(10),
                origin_country VARCHAR(100)
            )
        """)
        logger.debug("Таблица aircraft создана/проверена")

        # Таблица треков
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id BIGSERIAL PRIMARY KEY,
                aircraft_id INTEGER REFERENCES aircraft(id),
                country_id INTEGER REFERENCES countries(id),
                icao24 VARCHAR(6),
                callsign VARCHAR(10),
                altitude DECIMAL(10, 2),
                velocity DECIMAL(10, 2),
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(icao24, country_id, timestamp)
            )
        """)
        logger.debug("Таблица tracks создана/проверена")

        conn.close()
        logger.info("Создание базы данных завершено успешно")

    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        raise


def clear_data() -> None:
    """Очищает все данные из таблиц (удаляет записи, но сохраняет структуру)"""
    try:
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()

        # TRUNCATE удаляет все записи, но структура таблиц сохраняется
        cur.execute("TRUNCATE TABLE tracks CASCADE")
        cur.execute("TRUNCATE TABLE aircraft CASCADE")
        cur.execute("TRUNCATE TABLE countries CASCADE")

        conn.close()
        logger.info("Все данные очищены")
        print("Данные очищены")

    except Exception as e:
        logger.error(f"Ошибка очистки данных: {e}")
        print(f"Ошибка очистки: {e}")


def add_country(country_name: str) -> None:
    """Добавляет страну в БД если её нет"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO countries (name) VALUES (%s)
            ON CONFLICT (name) DO NOTHING
        """, (country_name,))

        conn.commit()
        conn.close()
        logger.debug(f"Страна '{country_name}' добавлена/проверена")

    except Exception as e:
        logger.error(f"Ошибка добавления страны '{country_name}': {e}")


# Работа с данными
def save_aircraft(icao24: str, callsign: str, origin_country: str) -> int:
    """Сохраняет самолет"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO aircraft (icao24, callsign, origin_country)
            VALUES (%s, %s, %s)
            ON CONFLICT (icao24) DO UPDATE SET
                callsign = EXCLUDED.callsign,
                origin_country = EXCLUDED.origin_country
            RETURNING id
        """, (icao24, callsign, origin_country))

        aircraft_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        logger.debug(f"Самолет {icao24} сохранен с ID {aircraft_id}")
        return aircraft_id

    except Exception as e:
        logger.error(f"Ошибка сохранения самолета {icao24}: {e}")
        raise


def save_track(aircraft_id: int, country_id: int, icao24: str,
               altitude: float, velocity: float, latitude: float, longitude: float) -> None:
    """Сохраняет трек с защитой от дублей"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO tracks (aircraft_id, country_id, icao24, altitude, velocity, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (icao24, country_id, timestamp) DO NOTHING
        """, (aircraft_id, country_id, icao24, altitude, velocity, latitude, longitude))

        conn.commit()
        conn.close()
        logger.debug(f"Трек для {icao24} сохранен")

    except Exception as e:
        logger.error(f"Ошибка сохранения трека для {icao24}: {e}")


def get_country_id(country_name: str) -> int:
    """Получает ID страны"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
        result = cur.fetchone()
        conn.close()

        if result:
            logger.debug(f"ID страны '{country_name}': {result[0]}")
        else:
            logger.warning(f"Страна '{country_name}' не найдена")

        return result[0] if result else None

    except Exception as e:
        logger.error(f"Ошибка получения ID для '{country_name}': {e}")
        return None


def get_existing_aircraft_in_country(country_id: int) -> set:
    """Получает список ICAO уже сохраненных в этой стране"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT icao24 FROM tracks 
            WHERE country_id = %s
        """, (country_id,))
        result = {row[0] for row in cur.fetchall()}
        conn.close()

        logger.debug(f"В стране ID {country_id} уже {len(result)} самолетов")
        return result

    except Exception as e:
        logger.error(f"Ошибка получения существующих самолетов: {e}")
        return set()


# Заполнение одной страны
def fill_country(country_name: str, processed_icaos: set = None) -> int:
    """Заполняет одну страну."""
    if processed_icaos is None:
        processed_icaos = set()

    logger.info(f"Начало заполнения страны: {country_name}")

    try:
        # Добавляем страну
        add_country(country_name)

        country_id = get_country_id(country_name)
        if not country_id:
            logger.error(f"Не удалось получить ID для {country_name}")
            return 0

        # Получаем данные через API
        logger.debug(f"Запрос данных через API для {country_name}")
        api = APIAdapter()
        api.get_aeroplanes(country_name)

        if not api.aeroplanes or "states" not in api.aeroplanes:
            logger.warning(f"Нет данных от API для {country_name}")
            return 0

        total_in_response = len(api.aeroplanes["states"])
        logger.info(f"Получено {total_in_response} самолетов от API для {country_name}")

        # Получаем уже сохраненные самолеты в этой стране
        existing_in_country = get_existing_aircraft_in_country(country_id)

        # Считаем сколько уже есть
        current_count = len(existing_in_country)

        # Определяем лимит: сколько еще можно добавить
        remaining_limit = MAX_AIRCRAFT_PER_COUNTRY - current_count

        if remaining_limit <= 0:
            logger.warning(f"Лимит {MAX_AIRCRAFT_PER_COUNTRY} для {country_name} уже достигнут")
            print(f"  Лимит {MAX_AIRCRAFT_PER_COUNTRY} уже достигнут")
            return 0

        print(f"  Уже есть: {current_count} / {MAX_AIRCRAFT_PER_COUNTRY} (можно добавить {remaining_limit})")

        # Фильтруем новые самолеты
        new_states = []
        skipped_existing = 0
        skipped_global = 0

        for state in api.aeroplanes["states"]:
            icao24 = state[0]

            # Пропускаем если уже есть в этой стране
            if icao24 in existing_in_country:
                skipped_existing += 1
                continue

            # Пропускаем если уже обработан глобально
            if icao24 in processed_icaos:
                skipped_global += 1
                continue

            new_states.append(state)

        logger.info(
            f"Для {country_name}: новых {len(new_states)}, "
            f"пропущено (есть в стране) {skipped_existing}, "
            f"пропущено (глобальный дубль) {skipped_global}"
        )

        print(f"  Найдено новых: {len(new_states)} (всего в ответе: {total_in_response})")

        # Ограничиваем до остатка лимита
        if len(new_states) > remaining_limit:
            new_states = new_states[:remaining_limit]
            logger.info(f"Ограничено до {remaining_limit} самолетов для {country_name}")
            print(f"  Ограничено до {remaining_limit} самолетов")

        # Сохраняем
        saved = 0

        for state in new_states:
            try:
                icao24 = state[0]
                callsign = state[1].strip() if state[1] else None
                origin_country = state[2]
                latitude = float(state[6]) if state[6] else None
                longitude = float(state[5]) if state[5] else None
                altitude = float(state[7]) if state[7] else None
                velocity = float(state[9]) if state[9] else None

                aircraft_id = save_aircraft(icao24, callsign, origin_country)
                save_track(aircraft_id, country_id, icao24, altitude, velocity, latitude, longitude)

                processed_icaos.add(icao24)
                saved += 1

            except Exception as e:
                logger.error(f"Ошибка обработки самолета {state[0] if state else 'unknown'}: {e}")
                continue

        logger.info(f"Для {country_name} сохранено {saved} самолетов")
        return saved

    except Exception as e:
        logger.error(f"Критическая ошибка при заполнении {country_name}: {e}")
        return 0


# Ввод пользователя
def get_countries_from_user() -> list:
    """Просит пользователя ввести страны"""
    print("\n" + "=" * 60)
    print("ВВЕДИТЕ СТРАНЫ ДЛЯ СБОРА ДАННЫХ")
    print("=" * 60)
    print("\nИнструкция:")
    print("  - Введите название страны (например: France)")
    print("  - Для завершения введите пустую строку или 'stop'")
    print(f"  - Минимум {MIN_COUNTRIES} страны")
    print(f"  - Лимит: {MAX_AIRCRAFT_PER_COUNTRY} самолетов на страну\n")

    countries = []

    while True:
        country = input(f"Страна {len(countries) + 1}: ").strip()

        if not country or country.lower() == 'stop':
            if len(countries) < MIN_COUNTRIES:
                print(f"\nНужно минимум {MIN_COUNTRIES} стран. Введено: {len(countries)}")
                continue
            break

        if country in countries:
            print(f"Страна '{country}' уже добавлена")
            continue

        countries.append(country)
        print(f"Добавлено: {country}")

        if len(countries) >= MIN_COUNTRIES:
            more = input(f"\nВведено {len(countries)} стран. Добавить еще? (y/n): ").strip().lower()
            if more != 'y':
                break

    logger.info(f"Пользователь ввел страны: {', '.join(countries)}")
    return countries


# Заполнение всех стран
def fill_all_countries(countries: list) -> None:
    """Заполняет все введенные страны с защитой от дублей"""
    logger.info(f"Начало сбора данных для {len(countries)} стран: {', '.join(countries)}")

    try:
        create_db()

        print("\n" + "=" * 60)
        print("НАЧАЛО СБОРА ДАННЫХ")
        print("=" * 60)
        print(f"Лимит на страну: {MAX_AIRCRAFT_PER_COUNTRY} самолетов")
        print("Защита от дублей: каждый самолет сохраняется только 1 раз\n")

        results = {}
        processed_icaos = set()
        total_start_time = time.time()

        for i, country in enumerate(countries, 1):
            country_start_time = time.time()

            print(f"\n[{i}/{len(countries)}] Сбор данных для: {country}")
            print("-" * 50)

            count = fill_country(country, processed_icaos)
            results[country] = count

            country_elapsed = time.time() - country_start_time

            print(f"  Добавлено: {count} новых самолетов")
            print(f"  Всего в БД: {len(processed_icaos)} уникальных")
            print(f"  Время: {country_elapsed:.2f} сек")

            logger.info(
                f"Страна {country}: добавлено {count}, "
                f"всего уникальных {len(processed_icaos)}, "
                f"время {country_elapsed:.2f} сек"
            )

            if i < len(countries):
                logger.debug(f"Пауза {REQUEST_DELAY} сек перед следующим запросом")
                time.sleep(REQUEST_DELAY)

        total_elapsed = time.time() - total_start_time

        # Итоги
        print("\n" + "=" * 60)
        print("ИТОГИ СБОРА")
        print("=" * 60)

        total = 0
        for country, count in results.items():
            print(f"  {country}: {count} новых самолетов")
            total += count

        print("-" * 60)
        print(f"  ВСЕГО НОВЫХ САМОЛЕТОВ: {total}")
        print(f"  УНИКАЛЬНЫХ ICAO ВСЕГО: {len(processed_icaos)}")
        print(f"  ОБЩЕЕ ВРЕМЯ: {total_elapsed:.2f} сек")
        print("=" * 60 + "\n")

        logger.info(
            f"Сбор завершен. Всего новых: {total}, "
            f"уникальных ICAO: {len(processed_icaos)}, "
            f"время: {total_elapsed:.2f} сек"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка при сборе данных: {e}")
        raise
