from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame,
                             QGridLayout, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QBrush


class StatusCard(QFrame):
    def __init__(self, title, value="0", subtitle="", icon_path=None, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setMinimumHeight(100)

        layout = QGridLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Иконка
        if icon_path:
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(32, 32)))
            layout.addWidget(icon_label, 0, 0, 2, 1)

        # Заголовок
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label, 0, 1)

        # Значение
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label, 1, 1)

        # Подзаголовок (опционально)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("cardSubtitle")
            layout.addWidget(subtitle_label, 2, 1)

    def setValue(self, value):
        self.value_label.setText(str(value))

    def setColor(self, color_name):
        self.setProperty("cardColor", color_name)
        self.style().unpolish(self)
        self.style().polish(self)


class PipeTab(QWidget):
    def __init__(self, request_queue):
        super().__init__()
        self.request_queue = request_queue
        self.init_ui()

        # Обновляем информацию каждые 500 мс
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(500)

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Карточки статуса
        status_layout = QHBoxLayout()

        # Карточка количества запросов в очереди
        self.queue_card = StatusCard(
            "Queue Size",
            "0",
            "Active requests",
            "resources/icons/queue.png"
        )
        status_layout.addWidget(self.queue_card)

        # Карточка статуса лимитов API
        self.rate_limit_card = StatusCard(
            "API Status",
            "OK",
            "",
            "resources/icons/api.png"
        )
        self.rate_limit_card.setColor("success")
        status_layout.addWidget(self.rate_limit_card)

        # Карточка времени до сброса ограничений
        self.reset_time_card = StatusCard(
            "Time to Reset",
            "N/A",
            "seconds",
            "resources/icons/timer.png"
        )
        status_layout.addWidget(self.reset_time_card)

        # Карточка обработанных запросов
        self.processed_card = StatusCard(
            "Processed",
            "0",
            "completed requests",
            "resources/icons/check.png"
        )
        status_layout.addWidget(self.processed_card)

        # Добавляем карточки в основной layout
        layout.addLayout(status_layout)

        # Группа управления очередью
        control_group = QGroupBox("Queue Control")
        control_group.setObjectName("controlGroup")
        control_layout = QHBoxLayout(control_group)

        # Прогресс-бар загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setObjectName("styledProgressBar")
        control_layout.addWidget(self.progress_bar, 1)

        # Кнопки управления
        self.pause_btn = QPushButton("Pause Queue")
        self.pause_btn.setObjectName("controlButton")
        self.pause_btn.setIcon(QIcon("resources/icons/pause.png"))
        self.pause_btn.setMinimumHeight(30)
        self.pause_btn.clicked.connect(self.toggle_queue)
        control_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear Queue")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.setIcon(QIcon("resources/icons/trash.png"))
        self.clear_btn.setMinimumHeight(30)
        self.clear_btn.clicked.connect(self.clear_queue)
        control_layout.addWidget(self.clear_btn)

        # Добавляем группу управления в основной layout
        layout.addWidget(control_group)

        # Группа для таблицы запросов
        table_group = QGroupBox("Active Requests")
        table_group.setObjectName("tableGroup")
        table_layout = QVBoxLayout(table_group)

        # Таблица с текущими запросами
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Status", "Exchange", "Symbol", "Timeframe", "Priority"])
        self.table.setObjectName("requestsTable")
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        table_layout.addWidget(self.table)

        # Добавляем группу таблицы в основной layout
        layout.addWidget(table_group, 1)

    def update_stats(self):
        # Обновляем информацию о состоянии очереди
        queue_stats = self.request_queue.get_stats()

        # Обновляем карточки
        self.queue_card.setValue(queue_stats['queue_size'])

        # Обновляем карточку лимита API
        if queue_stats['rate_limited']:
            self.rate_limit_card.setValue("RATE LIMITED")
            self.rate_limit_card.setColor("danger")
        else:
            self.rate_limit_card.setValue("OK")
            self.rate_limit_card.setColor("success")

        # Обновляем карточку времени сброса
        if queue_stats['reset_time'] > 0:
            self.reset_time_card.setValue(queue_stats['reset_time'])
        else:
            self.reset_time_card.setValue("N/A")

        # Обновляем карточку обработанных запросов
        self.processed_card.setValue(len(queue_stats['tasks']))

        # Обновляем прогресс-бар
        self.progress_bar.setValue(queue_stats['progress'])

        # Обновляем текст кнопки паузы
        if queue_stats['paused']:
            self.pause_btn.setText("Resume Queue")
            self.pause_btn.setIcon(QIcon("resources/icons/play.png"))
            self.pause_btn.setProperty("status", "paused")
        else:
            self.pause_btn.setText("Pause Queue")
            self.pause_btn.setIcon(QIcon("resources/icons/pause.png"))
            self.pause_btn.setProperty("status", "active")

        # Принудительно обновляем стиль
        self.pause_btn.style().unpolish(self.pause_btn)
        self.pause_btn.style().polish(self.pause_btn)

        # Обновляем таблицу
        self.update_table(queue_stats['tasks'])

    def update_table(self, tasks):
        # Очищаем и заново заполняем таблицу
        self.table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            # ID
            id_item = QTableWidgetItem(str(task['id']))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)

            # Status
            status_item = QTableWidgetItem(task['status'].upper())
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, status_item)

            # Exchange
            exchange_item = QTableWidgetItem(task['exchange'])
            self.table.setItem(row, 2, exchange_item)

            # Symbol
            symbol_item = QTableWidgetItem(task['symbol'])
            self.table.setItem(row, 3, symbol_item)

            # Timeframe
            timeframe_item = QTableWidgetItem(task.get('timeframe', '-'))
            timeframe_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, timeframe_item)

            # Priority
            priority_item = QTableWidgetItem(str(task['priority']))
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, priority_item)

            # Раскрашиваем строки в зависимости от статуса
            status_color = {
                'completed': "rgba(76, 175, 80, 0.2)",
                'error': "rgba(244, 67, 54, 0.2)",
                'in_progress': "rgba(255, 193, 7, 0.2)",
                'rate_limited': "rgba(156, 39, 176, 0.2)",
                'queued': "rgba(33, 150, 243, 0.15)",
                'cancelled': "rgba(158, 158, 158, 0.2)"
            }

            bg_color = status_color.get(task['status'].lower(), "transparent")
            for col in range(6):
                self.table.item(row, col).setBackground(QColor(bg_color))

                # Дополнительное форматирование для статуса
                if col == 1:
                    if task['status'] == 'completed':
                        self.table.item(row, col).setForeground(QColor('#4CAF50'))
                    elif task['status'] == 'error':
                        self.table.item(row, col).setForeground(QColor('#F44336'))
                    elif task['status'] == 'in_progress':
                        self.table.item(row, col).setForeground(QColor('#FFC107'))
                    elif task['status'] == 'rate_limited':
                        self.table.item(row, col).setForeground(QColor('#9C27B0'))

    def toggle_queue(self):
        if self.request_queue.is_paused():
            self.request_queue.resume()
            self.pause_btn.setText("Pause Queue")
            self.pause_btn.setIcon(QIcon("resources/icons/pause.png"))
        else:
            self.request_queue.pause()
            self.pause_btn.setText("Resume Queue")
            self.pause_btn.setIcon(QIcon("resources/icons/play.png"))

    def clear_queue(self):
        self.request_queue.clear()