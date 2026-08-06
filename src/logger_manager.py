import logging
from pathlib import Path


class LoggerManager:
    """Менеджер для управления логгерами"""

    _loggers = {}

    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def get_logger(self, name, level=logging.DEBUG):
        """Получить или создать логгер (только в файл, с перезаписью)"""
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Очищаем старые handlers
        if logger.handlers:
            logger.handlers.clear()

        # Форматтер
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File handler с перезаписью
        log_file = self.log_dir / f"{name}.log"
        file_handler = logging.FileHandler(
            log_file, mode="w", encoding="utf-8"  # Перезаписывать файл при каждом запуске
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Нет консольного вывода

        logger.propagate = False
        self._loggers[name] = logger
        return logger


# Инициализация менеджера
current_file = Path(__file__)
project_root = current_file.parent.parent
log_manager = LoggerManager(project_root / "logs")


# В каждом файле нужно писать:
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
