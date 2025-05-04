from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QVBoxLayout, QWidget,
                             QStatusBar, QLabel, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from ui.info_tab import InfoTab
from ui.pipe_tab import PipeTab
from ui.trends_tab import TrendsTab
from ui.settings_tab import SettingsTab
from core.api_client import ApiClient
from core.request_queue import RequestQueue


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KuCoin Viewer")
        self.resize(1200, 800)

        # Создаём общие компоненты приложения
        self.api_client = ApiClient()
        self.request_queue = RequestQueue(self.api_client)

        # Инициализация UI
        self.init_ui()

    def init_ui(self):
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Создаем основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Добавляем верхнюю панель с заголовком
        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)

        # Лого и название
        logo_label = QLabel()
        logo_label.setPixmap(QIcon("resources/icons/logo.png").pixmap(QSize(32, 32)))
        title_label = QLabel("KuCoin Viewer")
        title_label.setObjectName("titleLabel")

        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Добавляем статус API в заголовок
        self.api_status = QLabel("API: OK")
        self.api_status.setObjectName("apiStatus")
        header_layout.addWidget(self.api_status)

        main_layout.addWidget(header)

        # Создаем виджет с вкладками
        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")

        # Создаем вкладки
        self.info_tab = InfoTab(self.api_client, self.request_queue)
        self.trends_tab = TrendsTab(self.api_client, self.request_queue)
        self.pipe_tab = PipeTab(self.request_queue)
        self.settings_tab = SettingsTab(self)

        # Добавляем вкладки в TabWidget с иконками
        tabs.addTab(self.info_tab, QIcon("resources/icons/chart.png"), "Info")
        tabs.addTab(self.trends_tab, QIcon("resources/icons/trends.png"), "Trends")
        tabs.addTab(self.pipe_tab, QIcon("resources/icons/pipe.png"), "Pipe")
        tabs.addTab(self.settings_tab, QIcon("resources/icons/settings.png"), "Settings")

        # Добавляем TabWidget в основной layout
        main_layout.addWidget(tabs)

        # Создаем статус-бар
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Connected to KuCoin")

        # Обновляем статус API при изменении
        self.request_queue.queue_status_changed.connect(self.update_api_status)

    def update_api_status(self, stats):
        if stats["rate_limited"]:
            self.api_status.setText(f"API: Rate Limited ({stats['reset_time']}s)")
            self.api_status.setProperty("status", "error")
        else:
            self.api_status.setText("API: OK")
            self.api_status.setProperty("status", "ok")

        # Принудительное обновление стиля
        self.api_status.style().unpolish(self.api_status)
        self.api_status.style().polish(self.api_status)

    def closeEvent(self, event):
        # Останавливаем все фоновые процессы при закрытии
        self.request_queue.stop()
        event.accept()