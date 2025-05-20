import os
import sys
import platform

from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow


def configure_platform():
    """Настройка платформы в зависимости от операционной системы"""
    system = platform.system().lower()
    print("Определена ОС:", system)
    # Задаем платформенный плагин в зависимости от ОС
    if system == "linux":
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    elif system == "windows":
        os.environ["QT_QPA_PLATFORM"] = "windows"



def main():
    # Настройка платформы
    configure_platform()

    # Создаем приложение
    app = QApplication(sys.argv)

    # Настройка таблицы стилей
    try:
        # Используем os.path для кроссплатформенной работы с путями
        base_dir = os.path.dirname(os.path.abspath(__file__))
        style_path = os.path.join(base_dir, "resources", "styles", "light_aero_theme.qss")

        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
                print("Стиль успешно загружен:", style_path)
        else:
            print(f"Файл стилей не найден: {style_path}")
    except Exception as e:
        print(f"Ошибка загрузки стилей: {e}")

    # Создаем и показываем основное окно
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()