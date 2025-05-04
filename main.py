import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QFontDatabase
from PyQt5.QtCore import QFile, QTextStream

from ui.main_window import MainWindow


def load_stylesheet(file_path):
    """Загружает таблицу стилей из файла"""
    stylesheet = ""
    style_file = QFile(file_path)
    if style_file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(style_file)
        stylesheet = stream.readAll()
    return stylesheet


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("KuCoin Viewer")
    app.setWindowIcon(QIcon("resources/icons/app_icon.png"))

    # Загружаем шрифты
    QFontDatabase.addApplicationFont("resources/fonts/Roboto-Regular.ttf")
    QFontDatabase.addApplicationFont("resources/fonts/Roboto-Bold.ttf")

    # Устанавливаем стили
    app.setStyleSheet(load_stylesheet("resources/styles/dark_theme.qss"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())