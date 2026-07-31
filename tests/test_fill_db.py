import pytest
import psycopg2
from unittest.mock import Mock, call, patch
from src.fill_db import (
    get_connection,
    create_db,
    clear_data,
    add_country,
    save_aircraft,
    save_track,
    get_country_id,
    get_existing_aircraft_in_country,
    fill_country,
    get_countries_from_user,
    fill_all_countries,
    MAX_AIRCRAFT_PER_COUNTRY,
    MIN_COUNTRIES,
    REQUEST_DELAY,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT
)


# Тестирование функции get_connection
def test_successful_connection(mock_successful_connection, mock_logger):
    """Тест успешного подключения к БД"""
    conn = get_connection()

    mock_successful_connection.connect.assert_called_once_with(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    assert conn == mock_successful_connection.connect.return_value
    mock_logger.debug.assert_called_once_with(f"Подключение к БД {DB_NAME} установлено")


def test_successful_connection_custom_dbname(mock_successful_connection, mock_logger):
    """Тест успешного подключения с пользовательским именем БД"""
    custom_dbname = "test_db"

    conn = get_connection(custom_dbname)

    mock_successful_connection.connect.assert_called_once_with(
        dbname=custom_dbname,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    mock_logger.debug.assert_called_once_with(f"Подключение к БД {custom_dbname} установлено")


def test_connection_failure(mock_failed_connection, mock_logger):
    """Тест ошибки подключения к БД"""
    with pytest.raises(psycopg2.OperationalError) as exc_info:
        get_connection()

    assert str(exc_info.value) == "Connection failed"
    mock_logger.error.assert_called_once_with(f"Ошибка подключения к БД {DB_NAME}: Connection failed")


def test_connection_failure_custom_dbname(mock_failed_connection, mock_logger):
    """Тест ошибки подключения с пользовательским именем БД"""
    custom_dbname = "test_db"

    with pytest.raises(psycopg2.OperationalError) as exc_info:
        get_connection(custom_dbname)

    assert str(exc_info.value) == "Connection failed"
    mock_logger.error.assert_called_once_with(f"Ошибка подключения к БД {custom_dbname}: Connection failed")


# Тестирование функции create_db
def test_create_db_database_not_exists(mock_get_connection, mock_logger):
    """Тест создания БД, когда БД не существует"""
    # Создаем моки для соединений
    mock_conn_postgres = Mock()
    mock_conn_postgres.autocommit = False
    mock_cur_postgres = Mock()
    mock_cur_postgres.fetchone.return_value = None  # БД не существует
    mock_conn_postgres.cursor.return_value = mock_cur_postgres

    mock_conn_app = Mock()
    mock_conn_app.autocommit = False
    mock_cur_app = Mock()
    mock_conn_app.cursor.return_value = mock_cur_app

    # Настраиваем get_connection для возврата разных соединений
    mock_get_connection.side_effect = [mock_conn_postgres, mock_conn_app]

    # Выполняем тестируемую функцию
    create_db()

    # Проверяем вызовы get_connection
    assert mock_get_connection.call_count == 2
    mock_get_connection.assert_has_calls([
        call("postgres"),
        call()
    ])

    # Проверяем создание БД
    mock_cur_postgres.execute.assert_any_call(
        "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
    )
    mock_cur_postgres.execute.assert_any_call(f"CREATE DATABASE {DB_NAME}")

    # Проверяем создание таблиц
    mock_cur_app.execute.assert_any_call("""
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
    mock_cur_app.execute.assert_any_call("""
            CREATE TABLE IF NOT EXISTS aircraft (
                id SERIAL PRIMARY KEY,
                icao24 VARCHAR(6) NOT NULL UNIQUE,
                callsign VARCHAR(10),
                origin_country VARCHAR(100)
            )
        """)
    mock_cur_app.execute.assert_any_call("""
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

    # Проверяем autocommit
    assert mock_conn_postgres.autocommit is True
    assert mock_conn_app.autocommit is True

    # Проверяем закрытие соединений
    mock_conn_postgres.close.assert_called_once()
    mock_conn_app.close.assert_called_once()

    # Проверяем логирование
    mock_logger.info.assert_any_call("Начало создания базы данных")
    mock_logger.info.assert_any_call(f"База данных '{DB_NAME}' создана")
    mock_logger.debug.assert_any_call("Таблица countries создана/проверена")
    mock_logger.debug.assert_any_call("Таблица aircraft создана/проверена")
    mock_logger.debug.assert_any_call("Таблица tracks создана/проверена")
    mock_logger.info.assert_any_call("Создание базы данных завершено успешно")


def test_create_db_database_exists(mock_get_connection, mock_logger):
    """Тест создания БД, когда БД уже существует"""
    mock_conn_postgres = Mock()
    mock_conn_postgres.autocommit = False
    mock_cur_postgres = Mock()
    mock_cur_postgres.fetchone.return_value = True  # БД существует
    mock_conn_postgres.cursor.return_value = mock_cur_postgres

    mock_conn_app = Mock()
    mock_conn_app.autocommit = False
    mock_cur_app = Mock()
    mock_conn_app.cursor.return_value = mock_cur_app

    mock_get_connection.side_effect = [mock_conn_postgres, mock_conn_app]

    create_db()

    # Проверяем, что CREATE DATABASE не вызывался
    mock_cur_postgres.execute.assert_any_call(
        "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
    )
    # Проверяем, что CREATE DATABASE НЕ вызывался
    create_calls = [call for call in mock_cur_postgres.execute.call_args_list
                    if "CREATE DATABASE" in str(call)]
    assert len(create_calls) == 0

    # Проверяем логирование о существующей БД
    mock_logger.info.assert_any_call(f"База данных '{DB_NAME}' уже существует")


def test_create_db_connection_error(mock_get_connection, mock_logger):
    """Тест ошибки подключения при создании БД"""
    mock_get_connection.side_effect = psycopg2.OperationalError("Connection refused")

    with pytest.raises(psycopg2.OperationalError) as exc_info:
        create_db()

    assert str(exc_info.value) == "Connection refused"
    mock_logger.error.assert_called_once_with(
        f"Ошибка при создании базы данных: Connection refused"
    )


def test_create_db_creation_error(mock_get_connection, mock_logger):
    """Тест ошибки при создании БД"""
    mock_conn_postgres = Mock()
    mock_conn_postgres.autocommit = False
    mock_cur_postgres = Mock()
    mock_cur_postgres.fetchone.return_value = None
    mock_cur_postgres.execute.side_effect = psycopg2.Error("Database creation failed")
    mock_conn_postgres.cursor.return_value = mock_cur_postgres

    mock_get_connection.side_effect = [mock_conn_postgres]

    with pytest.raises(psycopg2.Error) as exc_info:
        create_db()

    assert str(exc_info.value) == "Database creation failed"
    mock_logger.error.assert_called_once_with(
        f"Ошибка при создании базы данных: Database creation failed"
    )


def test_create_db_table_creation_error(mock_get_connection, mock_logger):
    """Тест ошибки при создании таблиц"""
    mock_conn_postgres = Mock()
    mock_conn_postgres.autocommit = False
    mock_cur_postgres = Mock()
    mock_cur_postgres.fetchone.return_value = None
    mock_conn_postgres.cursor.return_value = mock_cur_postgres

    mock_conn_app = Mock()
    mock_conn_app.autocommit = False
    mock_cur_app = Mock()
    mock_cur_app.execute.side_effect = psycopg2.Error("Table creation failed")
    mock_conn_app.cursor.return_value = mock_cur_app

    mock_get_connection.side_effect = [mock_conn_postgres, mock_conn_app]

    with pytest.raises(psycopg2.Error) as exc_info:
        create_db()

    assert str(exc_info.value) == "Table creation failed"
    mock_logger.error.assert_called_once_with(
        f"Ошибка при создании базы данных: Table creation failed"
    )


# Тестирование функции clear_data
def test_clear_data_success(mock_get_connection, mock_logger, capsys):
    """Тест успешной очистки данных"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    clear_data()

    mock_get_connection.assert_called_once_with()
    assert mock_conn.autocommit is True
    mock_cur.execute.assert_has_calls([
        call("TRUNCATE TABLE tracks CASCADE"),
        call("TRUNCATE TABLE aircraft CASCADE"),
        call("TRUNCATE TABLE countries CASCADE")
    ])
    assert mock_cur.execute.call_count == 3
    mock_conn.close.assert_called_once()
    mock_logger.info.assert_called_once_with("Все данные очищены")

    captured = capsys.readouterr()
    assert "Данные очищены" in captured.out


def test_clear_data_error_handling(mock_get_connection, mock_logger, capsys):
    """Тест обработки ошибки - функция перехватывает исключение и не пробрасывает его"""
    mock_get_connection.side_effect = Exception("Database error")

    # Функция не выбрасывает исключение
    clear_data()

    # Проверяем логирование
    mock_logger.error.assert_called_once_with("Ошибка очистки данных: Database error")

    # Проверяем print
    captured = capsys.readouterr()
    assert "Ошибка очистки: Database error" in captured.out


# Тестирование функции add_country
def test_add_country_success(mock_get_connection, mock_logger):
    """Тест успешного добавления страны"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    add_country("Russia")

    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
    mock_logger.debug.assert_called_once()


def test_add_country_error(mock_get_connection, mock_logger):
    """Тест ошибки при добавлении страны"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.execute.side_effect = Exception("Database error")
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    add_country("Russia")

    mock_logger.error.assert_called_once_with(
        "Ошибка добавления страны 'Russia': Database error"
    )
    mock_conn.commit.assert_not_called()
    # close не вызывается при ошибке
    mock_conn.close.assert_not_called()


# Тестирование функции save_aircraft
def test_save_aircraft_success(mock_get_connection, mock_logger):
    """Тест успешного сохранения самолета"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.fetchone.return_value = (123,)
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    result = save_aircraft("ABC123", "FL123", "Russia")

    mock_cur.execute.assert_called_once()
    mock_cur.fetchone.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
    assert result == 123
    mock_logger.debug.assert_called_once_with("Самолет ABC123 сохранен с ID 123")


def test_save_aircraft_error(mock_get_connection, mock_logger):
    """Тест ошибки при сохранении самолета"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.execute.side_effect = Exception("Database error")
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    with pytest.raises(Exception) as exc_info:
        save_aircraft("ABC123", "FL123", "Russia")

    assert str(exc_info.value) == "Database error"
    mock_logger.error.assert_called_once_with(
        "Ошибка сохранения самолета ABC123: Database error"
    )
    mock_conn.commit.assert_not_called()
    # close НЕ вызывается при ошибке
    mock_conn.close.assert_not_called()


# Тестирование функции save_track
def test_save_track_success(mock_get_connection, mock_logger):
    """Тест успешного сохранения трека"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    save_track(1, 1, "ABC123", 10000.5, 500.25, 55.7558, 37.6173)

    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
    mock_logger.debug.assert_called_once_with("Трек для ABC123 сохранен")


def test_save_track_duplicate(mock_get_connection, mock_logger):
    """Тест сохранения дублирующего трека"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    save_track(1, 1, "ABC123", 10000.5, 500.25, 55.7558, 37.6173)
    save_track(1, 1, "ABC123", 10000.5, 500.25, 55.7558, 37.6173)

    assert mock_cur.execute.call_count == 2
    assert mock_conn.commit.call_count == 2
    assert mock_conn.close.call_count == 2
    assert mock_logger.debug.call_count == 2


def test_save_track_error(mock_get_connection, mock_logger):
    """Тест ошибки при сохранении трека (функция не выбрасывает исключение)"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.execute.side_effect = Exception("Database error")
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    save_track(1, 1, "ABC123", 10000.5, 500.25, 55.7558, 37.6173)

    mock_logger.error.assert_called_once_with(
        "Ошибка сохранения трека для ABC123: Database error"
    )
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_not_called()


def test_save_track_connection_error(mock_get_connection, mock_logger):
    """Тест ошибки подключения"""
    mock_get_connection.side_effect = psycopg2.OperationalError("Connection refused")

    save_track(1, 1, "ABC123", 10000.5, 500.25, 55.7558, 37.6173)

    mock_logger.error.assert_called_once_with(
        "Ошибка сохранения трека для ABC123: Connection refused"
    )


# Тестирование функции get_country_id
def test_get_country_id_success(mock_get_connection, mock_logger):
    """Тест успешного получения ID страны"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.fetchone.return_value = (5,)
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    result = get_country_id("Russia")

    mock_cur.execute.assert_called_once()
    mock_cur.fetchone.assert_called_once()
    mock_conn.close.assert_called_once()
    assert result == 5
    mock_logger.debug.assert_called_once_with("ID страны 'Russia': 5")


def test_get_country_id_not_found(mock_get_connection, mock_logger):
    """Тест получения ID несуществующей страны"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    result = get_country_id("NonExistent")

    assert result is None
    mock_logger.warning.assert_called_once_with("Страна 'NonExistent' не найдена")


def test_get_country_id_error(mock_get_connection, mock_logger):
    """Тест ошибки при получении ID"""
    mock_get_connection.side_effect = Exception("Database error")

    result = get_country_id("Russia")

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Ошибка получения ID для 'Russia': Database error"
    )


# Тестирование функции get_existing_aircraft_in_country
def test_get_existing_aircraft_in_country_success(mock_get_connection, mock_logger):
    """Тест успешного получения списка ICAO самолетов в стране"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.fetchall.return_value = [("ABC123",), ("DEF456",)]
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    result = get_existing_aircraft_in_country(1)

    mock_cur.execute.assert_called_once()
    mock_cur.fetchall.assert_called_once()
    mock_conn.close.assert_called_once()
    assert result == {"ABC123", "DEF456"}
    mock_logger.debug.assert_called_once_with("В стране ID 1 уже 2 самолетов")


def test_get_existing_aircraft_in_country_empty(mock_get_connection, mock_logger):
    """Тест когда нет самолетов в стране"""
    mock_conn = Mock()
    mock_cur = Mock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cur
    mock_get_connection.return_value = mock_conn

    result = get_existing_aircraft_in_country(1)

    assert result == set()
    mock_logger.debug.assert_called_once_with("В стране ID 1 уже 0 самолетов")


def test_get_existing_aircraft_in_country_error(mock_get_connection, mock_logger):
    """Тест ошибки при получении списка самолетов"""
    mock_get_connection.side_effect = Exception("Database error")

    result = get_existing_aircraft_in_country(1)

    assert result == set()
    mock_logger.error.assert_called_once_with(
        "Ошибка получения существующих самолетов: Database error"
    )


# Тестирование функции fill_country
def test_fill_country_success(mock_get_connection, mock_logger):
    """Тест успешного заполнения страны"""
    with patch('src.fill_db.add_country') as mock_add_country, \
            patch('src.fill_db.get_country_id') as mock_get_country_id, \
            patch('src.fill_db.APIAdapter') as mock_api_adapter, \
            patch('src.fill_db.get_existing_aircraft_in_country') as mock_get_existing, \
            patch('src.fill_db.save_aircraft') as mock_save_aircraft, \
            patch('src.fill_db.save_track') as mock_save_track:
        mock_get_country_id.return_value = 1
        mock_get_existing.return_value = set()

        mock_api = Mock()
        mock_api.aeroplanes = {
            "states": [
                ["ABC123", "FL123", "Russia", None, None, 37.6173, 55.7558, 10000.5, None, 500.25]
            ]
        }
        mock_api_adapter.return_value = mock_api
        mock_save_aircraft.return_value = 1

        processed_icaos = set()
        result = fill_country("Russia", processed_icaos)

        assert result == 1
        assert processed_icaos == {"ABC123"}


def test_fill_country_no_data(mock_get_connection, mock_logger):
    """Тест когда API не возвращает данные"""
    with patch('src.fill_db.add_country') as mock_add_country, \
            patch('src.fill_db.get_country_id') as mock_get_country_id, \
            patch('src.fill_db.APIAdapter') as mock_api_adapter:
        mock_get_country_id.return_value = 1

        mock_api = Mock()
        mock_api.aeroplanes = {}
        mock_api_adapter.return_value = mock_api

        result = fill_country("Russia")

        assert result == 0


def test_fill_country_limit_reached(mock_get_connection, mock_logger):
    """Тест когда лимит достигнут"""
    with patch('src.fill_db.add_country') as mock_add_country, \
            patch('src.fill_db.get_country_id') as mock_get_country_id, \
            patch('src.fill_db.get_existing_aircraft_in_country') as mock_get_existing:
        mock_get_country_id.return_value = 1
        mock_get_existing.return_value = {f"ABC{i:03d}" for i in range(MAX_AIRCRAFT_PER_COUNTRY)}

        result = fill_country("Russia")

        assert result == 0


def test_fill_country_critical_error(mock_get_connection, mock_logger):
    """Тест критической ошибки"""
    with patch('src.fill_db.add_country') as mock_add_country:
        mock_add_country.side_effect = Exception("Critical error")

        result = fill_country("Russia")

        assert result == 0
        mock_logger.error.assert_called_once_with(
            "Критическая ошибка при заполнении Russia: Critical error"
        )


# Тестирование функции get_countries_from_user
def test_get_countries_from_user_success(mock_logger):
    """Тест успешного ввода стран"""
    inputs = ["Russia", "USA", "France", "Germany", "n"]

    with patch('builtins.input', side_effect=inputs):
        result = get_countries_from_user()

    expected = ["Russia", "USA", "France", "Germany"]
    assert result == expected
    assert len(result) == MIN_COUNTRIES
    mock_logger.info.assert_called_once_with(f"Пользователь ввел страны: {', '.join(expected)}")


def test_get_countries_from_user_with_extra(mock_logger):
    """Тест ввода дополнительных стран"""
    inputs = ["Russia", "USA", "France", "Germany", "y", "Italy", "n"]

    with patch('builtins.input', side_effect=inputs):
        result = get_countries_from_user()

    assert result == ["Russia", "USA", "France", "Germany", "Italy"]


def test_get_countries_from_user_stop(mock_logger):
    """Тест остановки командой stop"""
    inputs = ["France", "Germany", "Italy", "Spain", "stop"]

    with patch('builtins.input', side_effect=inputs):
        result = get_countries_from_user()

    assert result == ["France", "Germany", "Italy", "Spain"]


def test_get_countries_from_user_duplicate(mock_logger):
    """Тест ввода дублирующейся страны"""
    inputs = ["France", "Germany", "Italy", "Spain", "France", "n"]

    with patch('builtins.input', side_effect=inputs):
        result = get_countries_from_user()

    assert result == ["France", "Germany", "Italy", "Spain"]


def test_get_countries_from_user_not_enough(mock_logger):
    """Тест, когда введено меньше минимального количества"""
    inputs = ["France", "Germany", "", "Italy", "Spain", "n"]

    with patch('builtins.input', side_effect=inputs):
        result = get_countries_from_user()

    assert len(result) >= MIN_COUNTRIES


# Тестирование функции fill_all_countries
def test_fill_all_countries_success(mock_logger):
    """Тест успешного заполнения всех стран"""
    countries = ["Russia", "USA"]

    with patch('src.fill_db.create_db') as mock_create_db, \
            patch('src.fill_db.fill_country') as mock_fill_country, \
            patch('src.fill_db.time.sleep') as mock_sleep, \
            patch('src.fill_db.time.time') as mock_time:

        mock_time.side_effect = [0, 1, 2, 3, 4, 5]

        def fill_country_side_effect(country, processed_icaos):
            if country == "Russia":
                processed_icaos.update(["RUS001", "RUS002", "RUS003", "RUS004", "RUS005"])
                return 5
            else:
                processed_icaos.update(["USA001", "USA002", "USA003"])
                return 3

        mock_fill_country.side_effect = fill_country_side_effect

        fill_all_countries(countries)

        mock_create_db.assert_called_once()
        assert mock_fill_country.call_count == 2
        mock_sleep.assert_called_once_with(REQUEST_DELAY)

        # Проверяем финальное сообщение
        final_message = None
        for call_args in mock_logger.info.call_args_list:
            if "Сбор завершен" in call_args[0][0]:
                final_message = call_args[0][0]
                break

        assert final_message is not None
        assert "Всего новых: 8" in final_message
        assert "уникальных ICAO: 8" in final_message


def test_fill_all_countries_empty(mock_logger):
    """Тест с пустым списком стран"""
    with patch('src.fill_db.create_db') as mock_create_db, \
            patch('src.fill_db.fill_country') as mock_fill_country, \
            patch('src.fill_db.time.sleep') as mock_sleep, \
            patch('src.fill_db.time.time') as mock_time:
        mock_time.side_effect = [0, 1]

        fill_all_countries([])

        mock_create_db.assert_called_once()
        mock_fill_country.assert_not_called()
        mock_sleep.assert_not_called()


def test_fill_all_countries_error(mock_logger):
    """Тест критической ошибки"""
    countries = ["Russia"]

    with patch('src.fill_db.create_db') as mock_create_db:
        mock_create_db.side_effect = Exception("DB error")

        with pytest.raises(Exception) as exc_info:
            fill_all_countries(countries)

        assert str(exc_info.value) == "DB error"
        mock_logger.error.assert_called_once_with(
            "Критическая ошибка при сборе данных: DB error"
        )
