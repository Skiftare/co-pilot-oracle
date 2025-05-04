from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QFrame, QComboBox, QHeaderView, QMenu,
                             QAction, QApplication, QMessageBox, QToolButton)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor, QCursor
import pandas as pd


class TrendsTab(QWidget):
    def __init__(self, api_client, request_queue):
        super().__init__()
        self.api_client = api_client
        self.request_queue = request_queue
        self.trending_data = None
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Верхняя панель управления
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_layout = QHBoxLayout(controls_frame)

        # Период для анализа трендов
        period_label = QLabel("Period:")
        period_label.setObjectName("controlLabel")
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1h", "4h", "12h", "24h", "7d"])
        self.period_combo.setCurrentText("24h")
        self.period_combo.setObjectName("styledComboBox")
        controls_layout.addWidget(period_label)
        controls_layout.addWidget(self.period_combo)

        # Фильтр по объему
        volume_label = QLabel("Min Volume (USDT):")
        volume_label.setObjectName("controlLabel")
        self.volume_combo = QComboBox()
        self.volume_combo.addItems(["5,000", "10,000", "50,000", "100,000", "500,000", "1,000,000"])
        self.volume_combo.setCurrentText("50,000")
        self.volume_combo.setObjectName("styledComboBox")
        controls_layout.addWidget(volume_label)
        controls_layout.addWidget(self.volume_combo)

        controls_layout.addStretch()

        # Кнопка для поиска трендов
        self.scan_btn = QPushButton("Scan For Trends")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.setIcon(QIcon("resources/icons/search.png"))
        self.scan_btn.clicked.connect(self.find_trends)
        controls_layout.addWidget(self.scan_btn)

        # Добавляем панель управления в основной layout
        layout.addWidget(controls_frame)

        # Информационная панель
        info_frame = QFrame()
        info_frame.setObjectName("infoFrame")
        info_layout = QHBoxLayout(info_frame)

        self.info_label = QLabel("Quickly find trending coins with significant price movement")
        self.info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.info_label)

        # Индикатор загрузки
        self.loading_label = QLabel("Scanning...")
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.setVisible(False)
        info_layout.addWidget(self.loading_label, 0, Qt.AlignRight)

        layout.addWidget(info_frame)

        # Таблица с трендами
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Symbol", "Price", "24h Change (%)", "Volume", "Actions"])
        self.table.setObjectName("trendsTable")
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # Включаем контекстное меню
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        # Нижняя панель с подсказками
        tips_frame = QFrame()
        tips_frame.setObjectName("tipsFrame")
        tips_layout = QHBoxLayout(tips_frame)

        tips_label = QLabel("💡 Tip: Right-click on any coin for additional options")
        tips_label.setObjectName("tipsLabel")
        tips_layout.addWidget(tips_label)

        # Добавляем автообновление
        self.auto_refresh = QPushButton("Auto Refresh: Off")
        self.auto_refresh.setObjectName("secondaryButton")
        self.auto_refresh.setCheckable(True)
        self.auto_refresh.clicked.connect(self.toggle_auto_refresh)
        tips_layout.addWidget(self.auto_refresh, 0, Qt.AlignRight)

        layout.addWidget(tips_frame)

        # Таймер для автообновления
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.find_trends)

    def find_trends(self):
        # Показываем индикатор загрузки
        self.loading_label.setVisible(True)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")

        # Получаем выбранный период
        period = self.period_combo.currentText()

        # Добавляем запрос в очередь
        task_id = self.request_queue.add_request(
            task_type="fetch_trending_coins",
            timeframe=period,
            limit=30,
            callback=self.update_trends_table
        )

    def update_trends_table(self, data, error=None):
        # Скрываем индикатор загрузки
        self.loading_label.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan For Trends")

        if error:
            QMessageBox.warning(self, "Error", f"Failed to fetch trending coins: {error}")
            return

        if data is None or len(data) == 0:
            self.info_label.setText("No trending coins found matching your criteria")
            return

        # Сохраняем данные
        self.trending_data = data

        # Обновляем информационную метку
        self.info_label.setText(f"Found {len(data)} trending coins. Updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

        # Очищаем таблицу
        self.table.setRowCount(len(data))

        # Заполняем таблицу данными
        for row, (_, coin) in enumerate(data.iterrows()):
            # Символ пары
            symbol_item = QTableWidgetItem(coin['symbol'])
            symbol_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 0, symbol_item)

            # Текущая цена
            price_item = QTableWidgetItem(f"{coin['price']:.8f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 1, price_item)

            # Изменение цены
            change = coin['change']
            change_item = QTableWidgetItem(f"{change:.2f}%")
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Окрашиваем в зависимости от изменения цены
            if change > 0:
                change_item.setForeground(QColor('#26A69A'))  # Зеленый для роста
            else:
                change_item.setForeground(QColor('#EF5350'))  # Красный для падения

            self.table.setItem(row, 2, change_item)

            # Объем торгов
            volume_usd = coin['volume_usd']
            if volume_usd >= 1_000_000:
                volume_text = f"${volume_usd / 1_000_000:.2f}M"
            else:
                volume_text = f"${volume_usd / 1_000:.2f}K"

            volume_item = QTableWidgetItem(volume_text)
            volume_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, volume_item)

            # Кнопки действий
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)

            # Кнопка копирования
            copy_btn = QToolButton()
            copy_btn.setIcon(QIcon("resources/icons/copy.png"))
            copy_btn.setToolTip("Copy trading pair")
            copy_btn.setObjectName("tableToolButton")
            copy_btn.clicked.connect(lambda checked, s=coin['symbol']: self.copy_symbol(s))

            # Кнопка анализа
            chart_btn = QToolButton()
            chart_btn.setIcon(QIcon("resources/icons/chart.png"))
            chart_btn.setToolTip("Open in Chart")
            chart_btn.setObjectName("tableToolButton")
            chart_btn.clicked.connect(lambda checked, s=coin['symbol']: self.open_in_chart(s))

            # Добавляем кнопки в layout
            actions_layout.addWidget(copy_btn)
            actions_layout.addWidget(chart_btn)
            actions_layout.addStretch()

            # Устанавливаем виджет в ячейку
            self.table.setCellWidget(row, 4, actions_widget)

            # Устанавливаем фон строки в зависимости от изменения цены
            bg_color = QColor('rgba(38, 166, 154, 0.1)') if change > 0 else QColor('rgba(239, 83, 80, 0.1)')
            for col in range(5):
                if col != 4:  # Не устанавливаем цвет для ячейки с кнопками
                    self.table.item(row, col).setBackground(bg_color)

    def copy_symbol(self, symbol):
        """Копирует символ пары в буфер обмена"""
        QApplication.clipboard().setText(symbol)
        self.info_label.setText(f"Copied {symbol} to clipboard")

    def open_in_chart(self, symbol):
        """Открывает выбранную пару во вкладке с графиком"""
        # Здесь можно добавить код для переключения на вкладку Info и загрузки пары
        # Это потребует сигнала для передачи данных между вкладками
        print(f"Opening {symbol} in chart tab")

    def show_context_menu(self, position):
        """Показывает контекстное меню при правом клике на таблице"""
        menu = QMenu()

        row = self.table.rowAt(position.y())
        if row >= 0:
            symbol = self.table.item(row, 0).text()

            copy_action = QAction(QIcon("resources/icons/copy.png"), f"Copy {symbol}", self)
            copy_action.triggered.connect(lambda: self.copy_symbol(symbol))

            chart_action = QAction(QIcon("resources/icons/chart.png"), f"Open {symbol} Chart", self)
            chart_action.triggered.connect(lambda: self.open_in_chart(symbol))

            menu.addAction(copy_action)
            menu.addAction(chart_action)

            # Дополнительные действия
            menu.addSeparator()
            menu.addAction(QIcon("resources/icons/info.png"), "View Market Info")
            menu.addAction(QIcon("resources/icons/alert.png"), "Set Price Alert")

            menu.exec_(QCursor.pos())

    def toggle_auto_refresh(self, checked):
        """Включает/выключает автообновление"""
        if checked:
            self.auto_refresh.setText("Auto Refresh: On")
            # Запускаем таймер обновления (каждые 5 минут)
            self.refresh_timer.start(300000)
        else:
            self.auto_refresh.setText("Auto Refresh: Off")
            self.refresh_timer.stop