from unittest.mock import Mock

import pytest

from src.db_manager import DBManager


class TestDBManager:

    def test_init_success(self, mock_logger_db_manager: Mock, mock_psycopg2_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_psycopg2_db_manager.connect.return_value = mock_conn

        db = DBManager()

        mock_psycopg2_db_manager.connect.assert_called_once()
        assert db.connection == mock_conn

    def test_init_error(self, mock_logger_db_manager: Mock, mock_psycopg2_db_manager: Mock) -> None:
        mock_psycopg2_db_manager.connect.side_effect = Exception("Connection error")

        with pytest.raises(Exception):
            DBManager()

        mock_logger_db_manager.error.assert_called_once()

    def test_close(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        db = DBManager()
        db.connection = mock_conn

        db.close()

        mock_conn.close.assert_called_once()
        assert db.connection is None

    def test_get_countries_and_aeroplanes_count(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchall.return_value = [("Russia", 5)]
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_countries_and_aeroplanes_count()

        assert result == [("Russia", 5)]
        mock_cur.execute.assert_called_once()

    def test_get_all_aeroplanes(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchall.return_value = [("ABC123", "FL123", "Russia", "2024-01-01", 3)]
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_all_aeroplanes()

        assert result == [("ABC123", "FL123", "Russia", "2024-01-01", 3)]

    def test_get_avg_speed(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchone.return_value = (450.5,)
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_avg_speed()

        assert result == 450.5

    def test_get_aeroplanes_with_higher_speed(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchall.return_value = [("ABC123", "FL123", 600.0, 450.5)]
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_aeroplanes_with_higher_speed()

        assert result == [("ABC123", "FL123", 600.0, 450.5)]

    def test_get_aeroplanes_with_keyword(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchall.return_value = [("ABC123", "FL123", "Russia", 5)]
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_aeroplanes_with_keyword("FL")

        assert result == [("ABC123", "FL123", "Russia", 5)]
        mock_cur.execute.assert_called_once()

    def test_get_aeroplanes_by_country(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchall.return_value = [("ABC123", "FL123", 10000, 55.7558, 37.6173, "2024-01-01")]
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_aeroplanes_by_country("Russia")

        assert len(result) == 1

    def test_get_statistics_summary(self, mock_logger_db_manager: Mock) -> None:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_cur.fetchone.return_value = (10, 50, 1000, 40, 8)
        mock_conn.cursor.return_value = mock_cur

        db = DBManager()
        db.connection = mock_conn

        result = db.get_statistics_summary()

        assert result["total_countries"] == 10
        assert result["total_aircraft"] == 50
        assert result["total_tracks"] == 1000
