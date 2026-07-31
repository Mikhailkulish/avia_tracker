import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from src.config import MAX_AIRCRAFT_PER_COUNTRY
from src.db_manager import DBManager
from src.fill_db import fill_all_countries, get_countries_from_user
from src.logger_manager import log_manager

logger = log_manager.get_logger("main")


def main():
    """Главная функция запуска приложения"""

    while True:  # <-- БЕСКОНЕЧНЫЙ ЦИКЛ ДЛЯ ВОЗВРАТА В ГЛАВНОЕ МЕНЮ
        print("\n" + "=" * 60)
        print("✈️  AVIATION DATA TRACKER")
        print("=" * 60)
        print("\nВыберите действие:")
        print("  1. Заполнить базу данных (сбор данных о самолетах)")
        print("  2. Просмотр и анализ данных (DBManager)")
        print("  3. Выход")

        choice = input("\nВаш выбор (1/2/3): ").strip()

        if choice == "1":
            print("\n" + "-" * 60)
            print("ЗАПУСК ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ")
            print("-" * 60)

            logger.info("=" * 60)
            logger.info("ЗАПУСК ПРОГРАММЫ СБОРА ДАННЫХ")
            logger.info("=" * 60)

            try:
                countries = get_countries_from_user()

                if not countries:
                    logger.warning("Страны не введены. Завершение.")
                    print("Страны не введены. Завершение.")
                    continue  # <-- ВОЗВРАТ В ГЛАВНОЕ МЕНЮ

                print(f"\nБудет обработано {len(countries)} стран: {', '.join(countries)}")
                print(f"Лимит на страну: {MAX_AIRCRAFT_PER_COUNTRY} самолетов")

                confirm = input("Продолжить? (y/n): ").strip().lower()

                if confirm != "y":
                    logger.info("Пользователь отменил выполнение")
                    print("Отмена.")
                    continue  # <-- ВОЗВРАТ В ГЛАВНОЕ МЕНЮ

                fill_all_countries(countries)
                print("\n✅ Готово!")
                logger.info("Программа завершена успешно")

            except KeyboardInterrupt:
                logger.warning("Программа прервана пользователем (Ctrl+C)")
                print("\n⚠️ Прервано пользователем")

            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
                print(f"\n❌ Ошибка: {e}")

            finally:
                logger.info("=" * 60)

            # Пауза перед возвратом в меню
            input("\nНажмите Enter для возврата в главное меню...")

        elif choice == "2":
            print("\n" + "-" * 60)
            print("ЗАПУСК МЕНЕДЖЕРА ДАННЫХ")
            print("-" * 60)

            db_manager = DBManager()

            try:
                while True:
                    print("\n" + "=" * 50)
                    print("ДОСТУПНЫЕ ДЕЙСТВИЯ:")
                    print("=" * 50)
                    print("  1. Список стран и количество самолетов")
                    print("  2. Список всех самолетов")
                    print("  3. Средняя скорость")
                    print("  4. Самолеты со скоростью выше средней")
                    print("  5. Поиск по ключевому слову в позывном")
                    print("  6. Самолеты по стране")
                    print("  7. Сводная статистика")
                    print("  8. Выход в главное меню")
                    print("-" * 50)

                    choice_db = input("Ваш выбор (1-8): ").strip()

                    if choice_db == "1":
                        db_manager.print_countries_and_aeroplanes_count()

                    elif choice_db == "2":
                        limit = input("Сколько записей показать? (по умолчанию 20): ").strip()
                        limit = int(limit) if limit else 20
                        db_manager.print_all_aeroplanes(limit=limit)

                    elif choice_db == "3":
                        db_manager.print_avg_speed()

                    elif choice_db == "4":
                        db_manager.print_aeroplanes_with_higher_speed()

                    elif choice_db == "5":
                        keyword = input("Введите ключевое слово для поиска (например, ACA): ").strip()
                        if keyword:
                            db_manager.print_aeroplanes_with_keyword(keyword)
                        else:
                            print("Ключевое слово не введено.")

                    elif choice_db == "6":
                        country = input("Введите название страны: ").strip()
                        if country:
                            data = db_manager.get_aeroplanes_by_country(country)
                            print(f"\n{'=' * 60}")
                            print(f"САМОЛЕТЫ НАД СТРАНОЙ '{country.upper()}'")
                            print("=" * 60)
                            if not data:
                                print("Нет данных")
                            else:
                                print(
                                    f"{'ICAO':<10} {'Позывной':<12} {'Высота':<10} "
                                    f"{'Скорость':<10} {'Широта':<12} {'Долгота':<12} {'Время':<20}"
                                )
                                print("-" * 90)
                                for row in data[:20]:
                                    icao, callsign, altitude, velocity, lat, lon, timestamp = row
                                    callsign_display = callsign or "Нет данных"
                                    altitude_display = f"{altitude:.0f}" if altitude else "Н/Д"
                                    velocity_display = f"{velocity:.2f}" if velocity else "Н/Д"
                                    lat_display = f"{lat:.4f}" if lat else "Н/Д"
                                    lon_display = f"{lon:.4f}" if lon else "Н/Д"
                                    time_display = timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "Н/Д"
                                    print(
                                        f"{icao:<10} {callsign_display:<12} {altitude_display:<10} "
                                        f"{velocity_display:<10} {lat_display:<12} "
                                        f"{lon_display:<12} {time_display:<20}"
                                    )
                            print("=" * 60 + "\n")
                        else:
                            print("Название страны не введено.")

                    elif choice_db == "7":
                        stats = db_manager.get_statistics_summary()
                        print("\n" + "=" * 60)
                        print("СВОДНАЯ СТАТИСТИКА")
                        print("=" * 60)
                        print(f"  Всего стран: {stats['total_countries']}")
                        print(f"  Всего самолетов: {stats['total_aircraft']}")
                        print(f"  Всего треков: {stats['total_tracks']}")
                        print(f"  Уникальных ICAO: {stats['unique_icao']}")
                        print(f"  Активных стран: {stats['active_countries']}")
                        print("=" * 60 + "\n")

                    elif choice_db == "8":
                        print("\nВыход в главное меню...")
                        break

                    else:
                        print("Неверный выбор. Пожалуйста, введите число от 1 до 8.")

            except KeyboardInterrupt:
                print("\n⚠️ Прервано пользователем")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
            finally:
                db_manager.close()
                logger.info("Менеджер данных завершил работу")

        elif choice == "3":
            print("\nВыход из программы. До свидания!")
            break  # <-- ВЫХОД ИЗ БЕСКОНЕЧНОГО ЦИКЛА И ЗАВЕРШЕНИЕ ПРОГРАММЫ

        else:
            print("Неверный выбор. Пожалуйста, введите 1, 2 или 3.")


if __name__ == "__main__":
    main()
