from abc import ABC, abstractmethod


class BaseAPIAdapter(ABC):
    """Абстрактный класс поиска самолетов по странам"""

    @abstractmethod
    def get_aeroplanes(self, country: str) -> None:
        """Абстрактный метод поиска самолетов по странам"""
        pass
