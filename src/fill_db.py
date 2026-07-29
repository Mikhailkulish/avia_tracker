import psycopg2
import time
from src.api_adapter import APIAdapter
from src.config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, REQUEST_DELAY, MIN_COUNTRIES


# ============= 1. ПОДКЛЮЧЕНИЕ К БД =============
def get_connection(dbname=DB_NAME):
    """Создает соединение с БД"""
    return psycopg2.connect(
        dbname=dbname,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


# ============= 2. СОЗДАНИЕ БАЗЫ =============
def create_db():
    """Создает БД и таблицы"""
    # Подключаемся к системной БД postgres
    conn = get_connection("postgres")
    conn.autocommit = True
    cur = conn.cursor()

    # Создаем БД если нет
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {DB_NAME}")
    conn.close()

    # Подключаемся к нашей БД
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    # Таблица стран
    cur.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )
    """)

    # Таблица самолетов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aircraft (
            id SERIAL PRIMARY KEY,
            icao24 VARCHAR(6) NOT NULL UNIQUE,
            callsign VARCHAR(10),
            origin_country VARCHAR(100)
        )
    """)

    # Таблица треков
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id BIGSERIAL PRIMARY KEY,
            aircraft_id INTEGER REFERENCES aircraft(id),
            country_id INTEGER REFERENCES countries(id),
            icao24 VARCHAR(6),
            altitude DECIMAL(10, 2),
            latitude DECIMAL(10, 6),
            longitude DECIMAL(10, 6),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.close()


# ============= 3. РАБОТА С ДАННЫМИ =============
def save_aircraft(icao24, callsign, origin_country):
    """Сохраняет самолет"""
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
    return aircraft_id


def save_track(aircraft_id, country_id, icao24, altitude, latitude, longitude):
    """Сохраняет трек"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tracks (aircraft_id, country_id, icao24, altitude, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (aircraft_id, country_id, icao24, altitude, latitude, longitude))

    conn.commit()
    conn.close()


def add_country(country_name):
    """Добавляет страну в БД если её нет"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO countries (name) VALUES (%s)
        ON CONFLICT (name) DO NOTHING
    """, (country_name,))

    conn.commit()
    conn.close()


def get_country_id(country_name):
    """Получает ID страны"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


# ============= 4. ЗАПОЛНЕНИЕ =============
def fill_country(country_name):
    """Заполняет одну страну"""
    add_country(country_name)

    api = APIAdapter()
    api.get_aeroplanes(country_name)

    if not api.aeroplanes or "states" not in api.aeroplanes:
        return 0

    country_id = get_country_id(country_name)
    if not country_id:
        return 0

    saved = 0
    for state in api.aeroplanes["states"]:
        try:
            icao24 = state[0]
            callsign = state[1].strip() if state[1] else None
            origin_country = state[2]
            latitude = float(state[6]) if state[6] else None
            longitude = float(state[5]) if state[5] else None
            altitude = float(state[7]) if state[7] else None

            aircraft_id = save_aircraft(icao24, callsign, origin_country)
            save_track(aircraft_id, country_id, icao24, altitude, latitude, longitude)
            saved += 1
        except:
            continue

    return saved


# ============= 5. ВВОД ПОЛЬЗОВАТЕЛЯ =============
def get_countries_from_user():
    """Просит пользователя ввести страны"""
    print("\n" + "=" * 60)
    print("ВВЕДИТЕ СТРАНЫ ДЛЯ СБОРА ДАННЫХ")
    print("=" * 60)
    print(f"\nИнструкция:")
    print(f"  - Введите название страны (например: France)")
    print(f"  - Для завершения введите пустую строку или 'stop'")
    print(f"  - Минимум {MIN_COUNTRIES} страны\n")

    countries = []

    while True:
        country = input(f"Страна {len(countries) + 1}: ").strip()

        if not country or country.lower() == 'stop':
            if len(countries) < MIN_COUNTRIES:
                print(f"\n⚠️ Нужно минимум {MIN_COUNTRIES} стран. Введено: {len(countries)}")
                continue
            break

        if country in countries:
            print(f"⚠️ Страна '{country}' уже добавлена")
            continue

        countries.append(country)
        print(f"✅ Добавлено: {country}")

        if len(countries) >= MIN_COUNTRIES:
            more = input(f"\nВведено {len(countries)} стран. Добавить еще? (y/n): ").strip().lower()
            if more != 'y':
                break

    return countries


# ============= 6. ЗАПОЛНЕНИЕ ВСЕХ СТРАН =============
def fill_all_countries(countries):
    """Заполняет все введенные страны"""
    create_db()

    print("\n" + "=" * 60)
    print("НАЧАЛО СБОРА ДАННЫХ")
    print("=" * 60)

    results = {}

    for i, country in enumerate(countries, 1):
        print(f"\n[{i}/{len(countries)}] Сбор данных для: {country}")

        count = fill_country(country)
        results[country] = count

        print(f"  Сохранено: {count} самолетов")

        if i < len(countries):
            time.sleep(REQUEST_DELAY)

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ СБОРА")
    print("=" * 60)

    total = 0
    for country, count in results.items():
        print(f"  {country}: {count} самолетов")
        total += count

    print("-" * 60)
    print(f"  ВСЕГО: {total} самолетов")
    print("=" * 60 + "\n")


# ============= ГЛАВНАЯ ФУНКЦИЯ =============
def main():
    """Главная функция"""
    countries = get_countries_from_user()

    if not countries:
        print("❌ Страны не введены. Завершение.")
        return

    print(f"\n📋 Будет обработано {len(countries)} стран: {', '.join(countries)}")
    confirm = input("Продолжить? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ Отмена.")
        return

    fill_all_countries(countries)
    print("✅ Готово!")