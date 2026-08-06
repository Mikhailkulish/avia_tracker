import logging
from pathlib import Path

import pytest

from src.logger_manager import LoggerManager, log_manager


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Очищает кэш логгеров после каждого теста"""
    yield
    # Очищаем кэш логгеров
    LoggerManager._loggers.clear()


def test_init(tmp_path):
    """Тест инициализации LoggerManager"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    assert manager.log_dir == log_dir
    assert log_dir.exists()
    assert logging.getLogger("urllib3").level == logging.WARNING


def test_get_logger_new(tmp_path):
    """Тест создания нового логгера"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("test_logger")

    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.FileHandler)
    assert logger.handlers[0].level == logging.DEBUG
    assert not logger.propagate
    assert "test_logger" in manager._loggers


def test_get_logger_cached(tmp_path):
    """Тест получения уже существующего логгера из кэша"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger1 = manager.get_logger("cached_logger")
    logger2 = manager.get_logger("cached_logger")

    assert logger1 is logger2
    assert len(manager._loggers) == 1


def test_get_logger_handlers_not_cleared_on_cached(tmp_path):
    """Тест: при получении кэшированного логгера хендлеры НЕ очищаются"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    # Создаем логгер с одним handler
    logger = manager.get_logger("test_handlers")
    assert len(logger.handlers) == 1

    # Добавляем дополнительный handler
    extra_handler = logging.StreamHandler()
    logger.addHandler(extra_handler)
    assert len(logger.handlers) == 2

    # Получаем логгер снова - хендлеры НЕ очищаются, т.к. логгер уже в кэше
    logger2 = manager.get_logger("test_handlers")
    # Хендлеров все еще 2
    assert len(logger2.handlers) == 2


def test_get_logger_clear_handlers_manually(tmp_path):
    """Тест: ручная очистка кэша перед созданием логгера"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    # Создаем логгер с одним handler
    logger = manager.get_logger("test_clear_manual")
    assert len(logger.handlers) == 1

    # Добавляем дополнительный handler
    extra_handler = logging.StreamHandler()
    logger.addHandler(extra_handler)
    assert len(logger.handlers) == 2

    # Очищаем кэш вручную
    LoggerManager._loggers.clear()

    # Создаем новый менеджер и логгер - хендлеры будут очищены
    manager2 = LoggerManager(log_dir)
    logger2 = manager2.get_logger("test_clear_manual")
    # Должен быть только один handler (FileHandler)
    assert len(logger2.handlers) == 1
    assert isinstance(logger2.handlers[0], logging.FileHandler)


def test_get_logger_file_creation(tmp_path):
    """Тест создания файла лога"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("file_test")
    logger.info("Test message")

    log_file = log_dir / "file_test.log"
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    assert "Test message" in content
    assert "INFO" in content


def test_get_logger_file_overwrite(tmp_path):
    """Тест перезаписи файла лога при каждом запуске"""
    log_dir = tmp_path / "logs"

    # Создаем первый менеджер и пишем первое сообщение
    manager1 = LoggerManager(log_dir)
    logger1 = manager1.get_logger("overwrite_test")
    logger1.info("First message")

    # Очищаем кэш, чтобы при создании нового менеджера логгер создался заново
    LoggerManager._loggers.clear()

    # Создаем второй менеджер и пишем второе сообщение
    manager2 = LoggerManager(log_dir)
    logger2 = manager2.get_logger("overwrite_test")
    logger2.info("Second message")

    log_file = log_dir / "overwrite_test.log"
    content = log_file.read_text(encoding="utf-8")

    # Должно быть только второе сообщение (перезапись)
    assert "Second message" in content
    assert "First message" not in content


def test_get_logger_custom_level(tmp_path):
    """Тест установки пользовательского уровня логирования"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("level_test", level=logging.ERROR)

    assert logger.level == logging.ERROR
    assert logger.handlers[0].level == logging.ERROR


def test_get_logger_formatting(tmp_path):
    """Тест форматирования сообщений"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("format_test")
    logger.info("Test format")

    log_file = log_dir / "format_test.log"
    content = log_file.read_text(encoding="utf-8")

    # Проверяем наличие всех компонентов форматирования
    assert " - format_test - " in content
    assert " - INFO: Test format" in content
    assert "test_logger_manager.py" in content


def test_get_logger_no_console_handler(tmp_path, capsys):
    """Тест отсутствия консольного вывода"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("no_console_test")
    logger.info("Console message")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_log_manager_global_instance():
    """Тест глобального экземпляра log_manager"""
    assert log_manager is not None
    assert isinstance(log_manager, LoggerManager)
    assert log_manager.log_dir == Path(__file__).parent.parent / "logs"


def test_get_logger_file_handler_error(tmp_path):
    """Тест обработки ошибки при создании файлового handler"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    # Создаем файл с правами только для чтения
    log_file = log_dir / "error_test.log"
    log_file.touch()
    log_file.chmod(0o444)

    with pytest.raises(PermissionError):
        manager.get_logger("error_test")


def test_logger_manager_multiple_loggers(tmp_path):
    """Тест создания нескольких разных логгеров"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger1 = manager.get_logger("logger1")
    logger2 = manager.get_logger("logger2")

    assert logger1 is not logger2
    assert len(manager._loggers) == 2
    assert (log_dir / "logger1.log").exists()
    assert (log_dir / "logger2.log").exists()


def test_get_logger_propagate_false(tmp_path):
    """Тест отключения пропагации логов"""
    log_dir = tmp_path / "logs"
    manager = LoggerManager(log_dir)

    logger = manager.get_logger("propagate_test")

    assert logger.propagate is False
