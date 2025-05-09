from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QDateEdit, QCheckBox,
                             QFrame, QToolButton, QSizePolicy, QSplitter,
                             QLineEdit, QCompleter, QAction, QMenu, QApplication,
                             QScrollArea, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QDateTime, QSize, pyqtSignal, QStringListModel, QPropertyAnimation, QRect, QEasingCurve, \
    QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot
import pandas as pd
import json
import os
from datetime import datetime, timedelta


class PairSelector(QFrame):
    pairSelected = pyqtSignal(str)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pairs = []
        self.init_ui()
        self.load_pairs()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)  # Уменьшаем расстояние между элементами

        # Поле ввода с автодополнением
        self.pair_input = QLineEdit()
        self.pair_input.setObjectName("pairInput")
        self.pair_input.setPlaceholderText("Enter or select trading pair...")
        self.pair_input.setMaximumHeight(28)  # Ограничиваем высоту поля ввода

        # Создаем автодополнение
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.pair_input.setCompleter(self.completer)

        # Кнопка выбора с выпадающим меню
        self.select_btn = QToolButton()
        self.select_btn.setIcon(QIcon("resources/icons/dropdown.png"))
        self.select_btn.setPopupMode(QToolButton.InstantPopup)
        self.select_btn.setObjectName("pairSelectButton")
        self.select_btn.setMaximumSize(28, 28)  # Уменьшаем размер кнопки

        # Создаем меню
        self.pair_menu = QMenu()
        self.select_btn.setMenu(self.pair_menu)

        # Кнопка для копирования текущей пары
        self.copy_btn = QToolButton()
        self.copy_btn.setIcon(QIcon("resources/icons/copy.png"))
        self.copy_btn.setToolTip("Copy pair name")
        self.copy_btn.setObjectName("copyButton")
        self.copy_btn.setMaximumSize(28, 28)  # Уменьшаем размер кнопки
        self.copy_btn.clicked.connect(self.copy_pair)

        # Добавляем виджеты в layout
        layout.addWidget(self.pair_input, 1)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.copy_btn)

        # Подключаем события
        self.pair_input.returnPressed.connect(self.on_pair_entered)



    def load_pairs(self):
        """Загружает список пар с биржи"""
        # Запустим асинхронную загрузку
        self.pairs = self.api_client.fetch_markets()
        if self.pairs is not None:
            # Создаем списки для интерфейса
            all_pairs = self.pairs['symbol'].tolist()

            # Исправлено: Используем QStringListModel вместо несуществующего метода model() у DataFrame
            string_list_model = QStringListModel(all_pairs)
            self.completer.setModel(string_list_model)

            # Заполняем выпадающее меню
            self.populate_menu(all_pairs)

    def populate_menu(self, pairs):
        """Заполняет выпадающее меню парами"""
        self.pair_menu.clear()

        # Создаем подменю по базовым валютам
        base_currencies = {}
        for pair in pairs:
            base = pair.split('/')[1] if '/' in pair else 'OTHER'  # USDT, BTC, etc.
            if base not in base_currencies:
                base_currencies[base] = []
            base_currencies[base].append(pair)

        # Сортируем базовые валюты и добавляем подменю
        for base in sorted(base_currencies.keys()):
            sub_menu = self.pair_menu.addMenu(base)

            # Добавляем пары в подменю, отсортированные по имени
            for pair in sorted(base_currencies[base]):
                action = QAction(pair, self)
                action.triggered.connect(lambda checked, p=pair: self.select_pair(p))
                sub_menu.addAction(action)

    def on_pair_entered(self):
        """Обработчик ввода пары"""
        pair = self.pair_input.text().strip()
        if pair:
            self.pairSelected.emit(pair)

    def select_pair(self, pair):
        """Выбор пары из выпадающего меню"""
        self.pair_input.setText(pair)
        self.pairSelected.emit(pair)

    def copy_pair(self):
        """Копирует текущую пару в буфер обмена"""
        pair = self.pair_input.text()
        if pair:
            QApplication.clipboard().setText(pair)
            # Можно добавить визуальную обратную связь


class ChartToolBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chartToolBar")
        self.setMaximumHeight(36)  # Ограничиваем высоту тулбара

        # Создаем горизонтальный layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Уменьшаем отступы
        layout.setSpacing(4)  # Уменьшаем расстояние между кнопками

        # Добавляем инструменты для экспорта данных
        button_size = QSize(16, 16)
        
        self.manual_save_btn = QToolButton()
        self.manual_save_btn.setIcon(QIcon("resources/icons/save.png"))
        self.manual_save_btn.setIconSize(button_size)
        self.manual_save_btn.setToolTip("Manual Save (Full Dataset)")
        self.manual_save_btn.setObjectName("chartToolButton")
        self.manual_save_btn.setMaximumSize(24, 24)

        self.fast_save_btn = QToolButton()
        self.fast_save_btn.setIcon(QIcon("resources/icons/export.png"))
        self.fast_save_btn.setIconSize(button_size)
        self.fast_save_btn.setToolTip("Fast-Save (Selected Data)")
        self.fast_save_btn.setObjectName("chartToolButton")
        self.fast_save_btn.setMaximumSize(24, 24)

        # Добавляем кнопки в layout
        layout.addWidget(self.manual_save_btn)
        layout.addWidget(self.fast_save_btn)
        layout.addStretch()


class IndicatorPanel(QFrame):
    indicatorChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("indicatorPanel")

        # Создаем вертикальный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем отступы
        layout.setSpacing(2)  # Уменьшаем расстояние между элементами

        # Заголовок
        title = QLabel("Indicators")
        title.setObjectName("panelTitle")
        title.setMaximumHeight(20)  # Уменьшаем высоту заголовка
        layout.addWidget(title)

        # Индикаторы - уменьшаем размер чекбоксов
        self.ma_check = QCheckBox("MA")  # Сокращаем текст
        self.ma_check.setObjectName("indicatorCheck")
        self.ma_check.stateChanged.connect(self.indicatorChanged)

        self.ema_check = QCheckBox("EMA")
        self.ema_check.setObjectName("indicatorCheck")
        self.ema_check.stateChanged.connect(self.indicatorChanged)

        self.rsi_check = QCheckBox("RSI")
        self.rsi_check.setObjectName("indicatorCheck")
        self.rsi_check.stateChanged.connect(self.indicatorChanged)

        self.macd_check = QCheckBox("MACD")
        self.macd_check.setObjectName("indicatorCheck")
        self.macd_check.stateChanged.connect(self.indicatorChanged)

        self.bollinger_check = QCheckBox("BB")  # Сокращаем текст
        self.bollinger_check.setObjectName("indicatorCheck")
        self.bollinger_check.stateChanged.connect(self.indicatorChanged)

        # Добавляем индикаторы в layout
        layout.addWidget(self.ma_check)
        layout.addWidget(self.ema_check)
        layout.addWidget(self.rsi_check)
        layout.addWidget(self.macd_check)
        layout.addWidget(self.bollinger_check)
        layout.addStretch()


class InfoTab(QWidget):
    def __init__(self, api_client, request_queue):
        super().__init__()
        self.api_client = api_client
        self.request_queue = request_queue
        self.data = None  # Для хранения текущих данных
        self.current_symbol = "BTC/USDT"  # Пара по умолчанию
        self.data_loaded = False  # Флаг загрузки данных
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем отступы
        layout.setSpacing(5)  # Уменьшаем расстояние между элементами

        # Используем прокручиваемую область для малых экранов
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # Верхняя панель с контролами - делаем её компактнее
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_frame.setMaximumHeight(60)  # Ограничиваем высоту панели контролов
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем отступы
        controls_layout.setSpacing(5)  # Уменьшаем расстояние между элементами

        # Селектор торговой пары
        pair_layout = QVBoxLayout()
        pair_layout.setSpacing(2)  # Уменьшаем расстояние
        pair_label = QLabel("Trading Pair")
        pair_label.setObjectName("controlLabel")
        pair_label.setMaximumHeight(16)  # Уменьшаем высоту метки
        self.pair_selector = PairSelector(self.api_client)
        self.pair_selector.pairSelected.connect(self.on_pair_selected)
        self.pair_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pair_layout.addWidget(pair_label)
        pair_layout.addWidget(self.pair_selector)
        controls_layout.addLayout(pair_layout, 2)

        # Выбор таймфрейма
        timeframe_layout = QVBoxLayout()
        timeframe_layout.setSpacing(2)  # Уменьшаем расстояние
        timeframe_label = QLabel("Timeframe")
        timeframe_label.setObjectName("controlLabel")
        timeframe_label.setMaximumHeight(16)  # Уменьшаем высоту метки
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        self.timeframe_combo.setCurrentText("1h")
        self.timeframe_combo.setObjectName("styledComboBox")
        self.timeframe_combo.setMaximumHeight(28)  # Ограничиваем высоту комбобокса
        timeframe_layout.addWidget(timeframe_label)
        timeframe_layout.addWidget(self.timeframe_combo)
        controls_layout.addLayout(timeframe_layout, 1)

        # Выбор даты
        date_layout = QVBoxLayout()
        date_layout.setSpacing(2)  # Уменьшаем расстояние
        date_label = QLabel("From Date")
        date_label.setObjectName("controlLabel")
        date_label.setMaximumHeight(16)  # Уменьшаем высоту метки
        self.date_edit = QDateEdit(QDateTime.currentDateTime().addDays(-7).date())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setObjectName("styledDateEdit")
        self.date_edit.setMaximumHeight(28)  # Ограничиваем высоту датапикера
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        controls_layout.addLayout(date_layout, 1)

        # Кнопка загрузки
        load_layout = QVBoxLayout()
        load_layout.setSpacing(2)  # Уменьшаем расстояние
        # Добавляем пустую метку для выравнивания
        load_layout.addWidget(QLabel(""))
        self.load_btn = QPushButton("Load")  # Сокращаем текст кнопки
        self.load_btn.setObjectName("primaryButton")
        self.load_btn.setIcon(QIcon("resources/icons/download.png"))
        self.load_btn.setIconSize(QSize(16, 16))  # Уменьшаем размер иконки
        self.load_btn.clicked.connect(self.load_data)
        self.load_btn.setMaximumHeight(28)  # Ограничиваем высоту кнопки
        load_layout.addWidget(self.load_btn)
        controls_layout.addLayout(load_layout, 1)

        # Добавляем верхнюю панель в scroll_layout
        scroll_layout.addWidget(controls_frame)
        
        # Добавляем панель с кнопками для загрузки дополнительных данных
        data_nav_frame = QFrame()
        data_nav_frame.setObjectName("dataNavFrame")
        data_nav_layout = QHBoxLayout(data_nav_frame)
        data_nav_layout.setContentsMargins(5, 0, 5, 0)
        
        # Кнопка для загрузки предыдущего периода
        self.load_prev_btn = QPushButton("← Load Previous")
        self.load_prev_btn.setObjectName("navButton")
        self.load_prev_btn.setIcon(QIcon("resources/icons/arrow-left.png"))
        self.load_prev_btn.clicked.connect(self.load_previous_period)
        self.load_prev_btn.setEnabled(False)
        
        # Индикатор загруженных данных
        self.data_range_label = QLabel("No data loaded")
        self.data_range_label.setObjectName("dataRangeLabel")
        self.data_range_label.setAlignment(Qt.AlignCenter)
        
        # Кнопка для загрузки следующего периода
        self.load_next_btn = QPushButton("Load Next →")
        self.load_next_btn.setObjectName("navButton")
        self.load_next_btn.setIcon(QIcon("resources/icons/arrow-right.png"))
        self.load_next_btn.setIconSize(QSize(16, 16))
        self.load_next_btn.clicked.connect(self.load_next_period)
        self.load_next_btn.setEnabled(False)
        
        data_nav_layout.addWidget(self.load_prev_btn)
        data_nav_layout.addWidget(self.data_range_label, 1)
        data_nav_layout.addWidget(self.load_next_btn)
        
        scroll_layout.addWidget(data_nav_frame)

        # Создаем сплиттер для графика и панели индикаторов
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(4)  # Делаем ручку сплиттера тоньше
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Важное изменение!

        # Создаем контейнер для графика
        chart_container = QFrame()
        chart_container.setObjectName("chartContainer")
        chart_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Расширяем в обоих направлениях
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы полностью
        chart_layout.setSpacing(0)  # Убираем расстояние между элементами

        # Добавляем панель инструментов для графика
        self.chart_toolbar = ChartToolBar()
        chart_layout.addWidget(self.chart_toolbar)

        # Область для графика - самое важное изменение
        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Удаляем минимальную высоту, позволяя графику адаптироваться
        chart_layout.addWidget(self.browser, 1)  # Даем графику приоритет в распределении пространства

        # Панель индикаторов - делаем её уже
        self.indicator_panel = IndicatorPanel()
        self.indicator_panel.indicatorChanged.connect(self.update_indicators)
        self.indicator_panel.setMinimumWidth(100)  # Уменьшаем минимальную ширину
        self.indicator_panel.setMaximumWidth(150)  # Ограничиваем максимальную ширину

        # Добавляем в сплиттер
        splitter.addWidget(chart_container)
        splitter.addWidget(self.indicator_panel)

        # Устанавливаем соотношение размеров - даем графику больше места
        splitter.setSizes([850, 100])

        # Добавляем сплиттер в основной layout с приоритетом
        scroll_layout.addWidget(splitter, 1)  # Даем сплиттеру приоритет для заполнения пространства

        # Устанавливаем контент для области прокрутки
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Инициализируем пустой график
        self.create_empty_chart()

        # Подключаем события к тулбару
        self.chart_toolbar.manual_save_btn.clicked.connect(self.save_data_json)
        self.chart_toolbar.fast_save_btn.clicked.connect(self.save_selected_data)

        # Загружаем данные для пары по умолчанию
        self.load_data()

    def on_pair_selected(self, symbol):
        """Обработчик выбора торговой пары"""
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            self.data = None  # Сбрасываем текущие данные при смене пары
            self.data_loaded = False
            self.load_data()

    def create_empty_chart(self):
        # Создаем пустой график с сообщением
        fig = go.Figure()
        fig.add_annotation(text="Select parameters and click 'Load Data' to view chart",
                           xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(size=16, color="white"))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
            plot_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
            title="Cryptocurrency Price Chart",
            xaxis_title="Time",
            yaxis_title="Price",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=50, b=10),
            font=dict(color="white")  # Белый текст для контраста
        )

        # Отображаем график
        html = plot(fig, output_type='div', include_plotlyjs='cdn')
        self.browser.setHtml(html)

    def load_data(self, append_mode=False, direction=None):
        """
        Загружает данные для выбранной пары и периода
        
        Parameters:
        - append_mode: если True, добавляет данные к существующим
        - direction: 'prev' или 'next' для загрузки предыдущего или следующего периода
        """
        symbol = self.current_symbol
        timeframe = self.timeframe_combo.currentText()
        
        # Определяем дату начала в зависимости от режима и направления
        if append_mode and self.data is not None:
            if direction == 'prev':
                # Для предыдущего периода используем самую раннюю дату в текущих данных
                earliest_date = self.data['timestamp'].min()
                
                # Вычисляем размер шага назад в зависимости от таймфрейма
                time_shift = self._get_timeframe_shift(timeframe)
                since_date = earliest_date - time_shift
                
                print(f"Загрузка предыдущего периода с {since_date}")
            elif direction == 'next':
                # Для следующего периода используем самую позднюю дату в текущих данных
                latest_date = self.data['timestamp'].max()
                since_date = latest_date
                print(f"Загрузка следующего периода с {latest_date}")
            else:
                # Если направление не указано, используем стандартную дату
                since_date = self.date_edit.date().toPyDate()
        else:
            # При первичной загрузке используем дату из UI
            since_date = self.date_edit.date().toPyDate()

        # Изменяем текст кнопки
        self.load_btn.setText("Loading...")
        self.load_btn.setEnabled(False)
        
        # Отключаем навигационные кнопки на время загрузки
        self.load_prev_btn.setEnabled(False)
        self.load_next_btn.setEnabled(False)

        # Детальное логирование
        print(f"DEBUG: Загружаем {symbol} с таймфреймом {timeframe} с {since_date}, append_mode={append_mode}, direction={direction}")

        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage(f"Загрузка {symbol}, таймфрейм: {timeframe}")

        # Показываем загрузочное сообщение с деталями
        if not append_mode:
            loading_fig = go.Figure()
            loading_fig.add_annotation(
                text=f"Загрузка данных для {symbol}",
                xref="paper", yref="paper",
                x=0.5, y=0.6, showarrow=False,
                font=dict(size=20, color="#4CAF50")
            )

            loading_fig.add_annotation(
                text=f"Таймфрейм: {timeframe}, с даты: {since_date.strftime('%d.%m.%Y') if hasattr(since_date, 'strftime') else str(since_date)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#FFFFFF")
            )

            loading_fig.add_annotation(
                text="Пожалуйста, подождите...",
                xref="paper", yref="paper",
                x=0.5, y=0.4, showarrow=False,
                font=dict(size=14, color="#AAAAAA")
            )

            loading_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(25, 25, 35, 1)',
                plot_bgcolor='rgba(25, 25, 35, 1)',
                margin=dict(l=10, r=10, t=50, b=10),
            )

            html = plot(loading_fig, output_type='div', include_plotlyjs='cdn')
            self.browser.setHtml(html)

        # Определяем лимит на основе таймфрейма
        limit = self._get_limit_for_timeframe(timeframe)

        # Добавляем запрос в очередь
        task_id = self.request_queue.add_request(
            task_type="fetch_ohlcv",
            exchange="kucoin",  # Только KuCoin
            symbol=symbol,
            timeframe=timeframe,
            since=since_date,
            callback=lambda data, error: self.update_chart(data, error, append_mode, direction),
            limit=limit
        )
        print(f"DEBUG: Запрос добавлен в очередь, ID задачи: {task_id}")

    def _get_timeframe_shift(self, timeframe):
        """Вычисляет смещение времени на основе таймфрейма"""
        if timeframe == '1m':
            return timedelta(hours=16)
        elif timeframe == '5m':
            return timedelta(days=3)
        elif timeframe == '15m':
            return timedelta(days=7)
        elif timeframe == '30m':
            return timedelta(days=14)
        elif timeframe == '1h':
            return timedelta(days=20)
        elif timeframe == '4h':
            return timedelta(days=40)
        elif timeframe == '1d':
            return timedelta(days=100)
        elif timeframe == '1w':
            return timedelta(weeks=20)
        else:
            return timedelta(days=7)  # По умолчанию

    def _get_limit_for_timeframe(self, timeframe):
        """Определяет оптимальный лимит для каждого таймфрейма"""
        limits = {
            '1m': 1000,
            '5m': 1000,
            '15m': 1000,
            '30m': 1000,
            '1h': 1000,
            '4h': 750,
            '1d': 365,
            '1w': 200
        }
        return limits.get(timeframe, 500)  # По умолчанию 500 свечей

    def load_previous_period(self):
        """Загружает данные за предыдущий период"""
        self.load_data(append_mode=True, direction='prev')

    def load_next_period(self):
        """Загружает данные за следующий период"""
        self.load_data(append_mode=True, direction='next')

    def fetch_top_pairs(self, limit=12):
        """Получает топ-12 пар с USDT по объему"""
        # Получаем все доступные пары с USDT
        markets_df = self.request_queue.add_request(
            task_type="fetch_markets",
            callback=None  # Синхронный запрос
        )

        if markets_df is None or markets_df.empty:
            # Возвращаем стандартный список популярных пар
            print("DEBUG: Не удалось получить список рынков, используем стандартный список")
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT',
                    'ADA/USDT', 'SHIB/USDT', 'TRX/USDT', 'DOT/USDT',
                    'AVAX/USDT', 'MATIC/USDT', 'LTC/USDT']

        # Фильтруем только USDT пары
        usdt_markets = markets_df[markets_df['quote'] == 'USDT']

        # Получаем и сортируем по объему
        try:
            # Выбираем топ-12 самых популярных по минимальному объему
            top_pairs = usdt_markets.sort_values('minAmount', ascending=True).head(limit)['symbol'].tolist()
            print(f"DEBUG: Получено {len(top_pairs)} популярных пар")
            return top_pairs
        except Exception as e:
            print(f"DEBUG: Ошибка при сортировке пар: {e}")
            # Возвращаем статический список в случае ошибки
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT',
                    'ADA/USDT', 'SHIB/USDT', 'TRX/USDT', 'DOT/USDT',
                    'AVAX/USDT', 'MATIC/USDT', 'LTC/USDT']

    def update_chart(self, new_data, error=None, append_mode=False, direction=None):
        """
        Обновляет график с новыми данными
        
        Parameters:
        - new_data: новые данные для отображения
        - error: сообщение об ошибке (если есть)
        - append_mode: если True, добавляет данные к существующим
        - direction: 'prev' или 'next' для указания направления добавления данных
        """
        # Восстанавливаем кнопку
        self.load_btn.setText("Load Data")
        self.load_btn.setEnabled(True)

        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().clearMessage()

        if error:
            error_message = f"Ошибка: {error}"
            print(f"DEBUG: Ошибка при обновлении графика: {error}")
            
            # Отображение ошибки только если не в режиме добавления
            if not append_mode:
                error_fig = go.Figure()
                error_fig.add_annotation(
                    text=error_message,
                    xref="paper", yref="paper",
                    x=0.5, y=0.55, showarrow=False,
                    font=dict(size=18, color="#F44336")
                )

                error_fig.add_annotation(
                    text="Попробуйте изменить параметры и повторить запрос",
                    xref="paper", yref="paper",
                    x=0.5, y=0.45, showarrow=False,
                    font=dict(size=14, color="#FFFFFF")
                )

                error_fig.update_layout(
                    template="plotly_light",
                    paper_bgcolor='rgba(25, 25, 35, 1)',
                    plot_bgcolor='rgba(25, 25, 35, 1)',
                    margin=dict(l=10, r=10, t=50, b=10),
                )

                html = plot(error_fig, output_type='div', include_plotlyjs='cdn')
                self.browser.setHtml(html)

            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"Ошибка: {error}", 5000)

            # Включаем навигационные кнопки, если данные уже были загружены
            if self.data_loaded:
                self.load_prev_btn.setEnabled(True)
                self.load_next_btn.setEnabled(True)
                
            return

        # Обработка новых данных
        if new_data is not None and len(new_data) > 0:
            if append_mode and self.data is not None:
                # Объединение данных в зависимости от направления
                print(f"Объединение данных. Старых: {len(self.data)}, новых: {len(new_data)}")
                
                # Объединяем датафреймы и удаляем дубликаты
                combined_data = pd.concat([self.data, new_data])
                combined_data = combined_data.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                
                # Сохраняем объединенные данные
                self.data = combined_data
                print(f"Данные объединены. Итого: {len(self.data)} записей")
                print(f"Диапазон данных: с {self.data['timestamp'].min()} по {self.data['timestamp'].max()}")
            else:
                # Сохраняем новые данные
                self.data = new_data
                print(f"Новые данные загружены. Количество записей: {len(self.data)}")
                print(f"Диапазон данных: с {self.data['timestamp'].min()} по {self.data['timestamp'].max()}")

            # Обновляем метку диапазона данных
            self._update_data_range_label()
            
            # Устанавливаем флаг загрузки данных
            self.data_loaded = True
            
            # Включаем навигационные кнопки
            self.load_prev_btn.setEnabled(True)
            self.load_next_btn.setEnabled(True)
            
            # Обновляем график с учетом индикаторов
            self.update_indicators()
        else:
            # Если нет новых данных и нет старых данных
            if not self.data_loaded:
                no_data_fig = go.Figure()
                no_data_fig.add_annotation(
                    text="Нет данных для отображения",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=18, color="#FFFFFF")
                )
                no_data_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(25, 25, 35, 1)',
                    plot_bgcolor='rgba(25, 25, 35, 1)',
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                html = plot(no_data_fig, output_type='div', include_plotlyjs='cdn')
                self.browser.setHtml(html)

    def _update_data_range_label(self):
        """Обновляет метку с информацией о диапазоне загруженных данных"""
        if self.data is not None and len(self.data) > 0:
            min_date = self.data['timestamp'].min().strftime('%d.%m.%Y')
            max_date = self.data['timestamp'].max().strftime('%d.%m.%Y')
            count = len(self.data)
            self.data_range_label.setText(f"Data: {min_date} - {max_date} ({count} candles)")
        else:
            self.data_range_label.setText("No data loaded")

    def update_indicators(self):
        if self.data is None:
            return

        data = self.data
        symbol = self.current_symbol

        # Определяем количество подграфиков
        subplot_rows = 1
        has_separate_indicators = self.indicator_panel.rsi_check.isChecked() or self.indicator_panel.macd_check.isChecked()

        if has_separate_indicators:
            subplot_rows = 2
            row_heights = [0.7, 0.3]
        else:
            subplot_rows = 1
            row_heights = [1]

        # Создаем подграфики
        fig = make_subplots(rows=subplot_rows, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.05,
                            row_heights=row_heights)

        # Добавляем свечной график
        fig.add_trace(
            go.Candlestick(
                x=data['timestamp'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name="OHLC",
                increasing_line_color='#26A69A',  # Зеленый цвет для роста
                decreasing_line_color='#EF5350',  # Красный цвет для падения
                increasing_fillcolor='rgba(38, 166, 154, 0.6)',  # Полупрозрачный зеленый
                decreasing_fillcolor='rgba(239, 83, 80, 0.6)'  # Полупрозрачный красный
            ),
            row=1, col=1
        )

        # Если выбран индикатор MA
        if self.indicator_panel.ma_check.isChecked():
            # Вычисляем простую скользящую среднюю за 20 периодов
            ma20 = data['close'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=ma20,
                    line=dict(width=1.5, color='#FFD600'),  # Яркий желтый для контраста
                    name="MA 20"
                ),
                row=1, col=1
            )

        # Если выбран индикатор EMA
        if self.indicator_panel.ema_check.isChecked():
            # Вычисляем экспоненциальную скользящую среднюю за 14 периодов
            ema14 = data['close'].ewm(span=14).mean()
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=ema14,
                    line=dict(width=1.5, color='#42A5F5'),  # Яркий синий для контраста
                    name="EMA 14"
                ),
                row=1, col=1
            )

        # Если выбраны полосы Боллинджера
        if self.indicator_panel.bollinger_check.isChecked():
            # Вычисляем полосы Боллинджера
            ma20 = data['close'].rolling(window=20).mean()
            std20 = data['close'].rolling(window=20).std()
            upper_band = ma20 + 2 * std20
            lower_band = ma20 - 2 * std20

            # Верхняя полоса
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=upper_band,
                    line=dict(width=1, color='rgba(173, 216, 230, 0.7)'),
                    name="Upper BB"
                ),
                row=1, col=1
            )

            # Нижняя полоса
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=lower_band,
                    line=dict(width=1, color='rgba(173, 216, 230, 0.7)'),
                    fill='tonexty',
                    fillcolor='rgba(173, 216, 230, 0.2)',  # Увеличил непрозрачность заливки
                    name="Lower BB"
                ),
                row=1, col=1
            )

        # Если выбран RSI
        if self.indicator_panel.rsi_check.isChecked() and subplot_rows > 1:
            # Вычисляем RSI
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=rsi,
                    line=dict(width=1.5, color='#EC407A'),  # Яркий розовый для контраста
                    name="RSI (14)"
                ),
                row=2, col=1
            )

            # Добавляем линии уровней RSI с более заметным цветом
            fig.add_hline(y=70, line_width=1, line_color='rgba(255, 255, 255, 0.7)',
                          line_dash="dash", row=2, col=1)
            fig.add_hline(y=30, line_width=1, line_color='rgba(255, 255, 255, 0.7)',
                          line_dash="dash", row=2, col=1)

            # Задаем диапазон для RSI
            fig.update_yaxes(range=[0, 100], row=2, col=1)

        # Если выбран MACD
        if self.indicator_panel.macd_check.isChecked() and subplot_rows > 1:
            # Вычисляем MACD
            ema12 = data['close'].ewm(span=12).mean()
            ema26 = data['close'].ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line

            # MACD линия
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=macd_line,
                    line=dict(width=1.5, color='#42A5F5'),  # Яркий синий
                    name="MACD"
                ),
                row=2, col=1
            )

            # Сигнальная линия
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=signal_line,
                    line=dict(width=1.5, color='#FFD600'),  # Яркий желтый
                    name="Signal"
                ),
                row=2, col=1
            )

            # Гистограмма с более яркими цветами
            colors = ['#26A69A' if val >= 0 else '#EF5350' for val in histogram]
            fig.add_trace(
                go.Bar(
                    x=data['timestamp'],
                    y=histogram,
                    marker_color=colors,
                    name="Histogram"
                ),
                row=2, col=1
            )

        # Настраиваем внешний вид графика
        timeframe = self.timeframe_combo.currentText()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
            plot_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
            title=dict(
                text=f"{symbol} Price Chart ({timeframe})",
                font=dict(size=20, color='white')  # Белый цвет для заголовка
            ),
            legend=dict(
                bgcolor='rgba(25, 25, 35, 0.8)',
                bordercolor='rgba(255, 255, 255, 0.3)',  # Увеличил контраст рамки
                borderwidth=1,
                font=dict(color="white")  # Белый цвет для текста легенды
            ),
            hovermode="x unified",
            hoverdistance=100,
            spikedistance=1000,
            xaxis=dict(
                showspikes=True,
                spikesnap="cursor",
                spikemode="across",
                spikethickness=1,
                spikecolor="rgba(255, 255, 255, 0.7)",  # Более заметная линия
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.2)',  # Увеличил контраст сетки
                tickfont=dict(color="white")  # Белый цвет для подписей по оси X
            ),
            yaxis=dict(
                showspikes=True,
                spikesnap="cursor",
                spikemode="across",
                spikethickness=1,
                spikecolor="rgba(255, 255, 255, 0.7)",  # Более заметная линия
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.2)',  # Увеличил контраст сетки
                tickfont=dict(color="white")  # Белый цвет для подписей по оси Y
            ),
            margin=dict(l=10, r=10, t=50, b=10),
        )

        # Добавляем подписи для подграфиков с белым цветом
        if subplot_rows > 1:
            fig.update_yaxes(title_text="Price", title_font=dict(color="white"), row=1, col=1)

            if self.indicator_panel.rsi_check.isChecked() and not self.indicator_panel.macd_check.isChecked():
                fig.update_yaxes(title_text="RSI", title_font=dict(color="white"), row=2, col=1)
            elif not self.indicator_panel.rsi_check.isChecked() and self.indicator_panel.macd_check.isChecked():
                fig.update_yaxes(title_text="MACD", title_font=dict(color="white"), row=2, col=1)
            else:
                fig.update_yaxes(title_text="Indicators", title_font=dict(color="white"), row=2, col=1)

            # Добавляем белый цвет для подписей на оси Y второй диаграммы
            fig.update_yaxes(tickfont=dict(color="white"), row=2, col=1)

        # В конце метода обновляем настройки компоновки
        if self.data is not None:
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
                plot_bgcolor='rgba(25, 25, 35, 1)',  # Более темный фон
                title=dict(
                    text=f"{symbol} Price Chart ({timeframe})",
                    font=dict(size=20, color='white')  # Белый цвет для заголовка
                ),
                legend=dict(
                    bgcolor='rgba(25, 25, 35, 0.8)',
                    bordercolor='rgba(255, 255, 255, 0.3)',  # Увеличил контраст рамки
                    borderwidth=1,
                    font=dict(color="white")  # Белый цвет для текста легенды
                ),
                hovermode="x unified",
                hoverdistance=100,
                spikedistance=1000,
                xaxis=dict(
                    showspikes=True,
                    spikesnap="cursor",
                    spikemode="across",
                    spikethickness=1,
                    spikecolor="rgba(255, 255, 255, 0.7)",  # Более заметная линия
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.2)',  # Увеличил контраст сетки
                    tickfont=dict(color="white")  # Белый цвет для подписей по оси X
                ),
                yaxis=dict(
                    showspikes=True,
                    spikesnap="cursor",
                    spikemode="across",
                    spikethickness=1,
                    spikecolor="rgba(255, 255, 255, 0.7)",  # Более заметная линия
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.2)',  # Увеличил контраст сетки
                    tickfont=dict(color="white")  # Белый цвет для подписей по оси Y
                ),
                margin=dict(l=5, r=5, t=40, b=5),  # Уменьшаем отступы графика
                autosize=True,  # Автоматическое изменение размера
            )

        # Отображаем график
        html = plot(fig, output_type='div', include_plotlyjs='cdn', config={'responsive': True})
        self.browser.setHtml(html)

        # Устанавливаем фокус на график

    def save_data_json(self):
        """Saves all current data to a JSON file"""
        if self.data is None or self.data.empty:
            QMessageBox.warning(self, "No Data", "There is no data to save.")
            return

        # Get path for saving with improved filename
        default_dir = os.path.expanduser("~/crypto_data")
        os.makedirs(default_dir, exist_ok=True)

        default_filename = self._generate_filename(is_selected=False)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data",
            os.path.join(default_dir, default_filename),
            "JSON Files (*.json)"
        )

        if filepath:
            try:
                # Create metadata
                metadata = {
                    'symbol': self.current_symbol,
                    'timeframe': self.timeframe_combo.currentText(),
                    'start_date': self.data.index.min().strftime('%Y-%m-%d %H:%M:%S'),
                    'end_date': self.data.index.max().strftime('%Y-%m-%d %H:%M:%S'),
                    'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'candle_count': len(self.data)
                }

                # Prepare export data
                export_data = {
                    'metadata': metadata,
                    'data': self.data.reset_index().to_dict('records')
                }

                # Save to file
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)

                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(f"Data saved to {filepath}")

                # Check if server upload is needed
                self._send_to_server_if_needed(filepath, export_data)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
    def save_selected_data(self):
        """Saves only the selected/visible chart data range without confirmation"""
        if self.data is None or self.data.empty:
            QMessageBox.warning(self, "No Data", "There is no data to save.")
            return

        # Fix: Wrap the JS in an anonymous function to make the return statement valid
        script = """
        (function() {
            var rangeData = {};
            try {
                // Находим элемент графика Plotly
                var plotlyDiv = document.querySelector('.js-plotly-plot');
                if (plotlyDiv && plotlyDiv._fullLayout) {
                    // Проверяем, есть ли у графика данные о выбранном диапазоне
                    if (plotlyDiv._fullLayout.xaxis && plotlyDiv._fullLayout.xaxis.range) {
                        rangeData.xRange = plotlyDiv._fullLayout.xaxis.range;
                        rangeData.success = true;
                    } else {
                        // Если диапазон не выбран, используем весь видимый диапазон
                        rangeData.xRange = plotlyDiv._fullLayout.xaxis._range;
                        rangeData.success = true;
                    }
                } else {
                    rangeData.success = false;
                    rangeData.error = "Cannot find Plotly graph or layout";
                }
            } catch (e) {
                rangeData.success = false;
                rangeData.error = e.toString();
            }
            return rangeData;
        })();
        """

        # Run JavaScript to get selected range and pass to fast save handler
        self.browser.page().runJavaScript(script, self.on_fast_save_range_received)

    def _generate_filename(self, is_selected=False):
        """Generate a descriptive filename that includes all required information"""
        if self.data is None or self.data.empty:
            return None

        # Get date range from the data using the timestamp column instead of index
        start_date = pd.to_datetime(self.data['timestamp'].min()).strftime('%Y%m%d')
        end_date = pd.to_datetime(self.data['timestamp'].max()).strftime('%Y%m%d')

        # Add current timestamp to show when exported
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate filename with all required information
        selection_tag = "selected" if is_selected else "full"
        filename = f"{self.current_symbol.replace('/', '_')}_{self.timeframe_combo.currentText()}_{start_date}-{end_date}_{selection_tag}_{timestamp}.json"

        return filename

    def on_fast_save_range_received(self, range_data):
        """Handler for receiving range data for fast save without confirmation"""
        print("DEBUG: Received range data for fast save:", range_data)
        if not range_data or not range_data.get('success', False):
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage("Failed to get selected range data")
            return

        try:
            # Extract the date range
            date_range = range_data.get('xRange', [])
            if not date_range or len(date_range) != 2:
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage("Invalid range data received")
                return

            # Convert to timestamps
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1])

            # Filter data to the selected range using timestamp column
            filtered_df = self.data[(pd.to_datetime(self.data['timestamp']) >= start_date) &
                                    (pd.to_datetime(self.data['timestamp']) <= end_date)].copy()

            if filtered_df.empty:
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage("No data in selected range")
                return

            # Create metadata for export
            metadata = {
                'symbol': self.current_symbol,
                'timeframe': self.timeframe_combo.currentText(),
                'start_date': str(pd.to_datetime(filtered_df['timestamp'].min())),
                'end_date': str(pd.to_datetime(filtered_df['timestamp'].max())),
                'rows': len(filtered_df),
                'exported_at': datetime.now().isoformat()
            }

            # Convert DataFrame to serializable format - properly handle timestamps
            filtered_df_copy = filtered_df.copy()
            for column in filtered_df_copy.select_dtypes(include=['datetime64']).columns:
                filtered_df_copy[column] = filtered_df_copy[column].astype(str)

            # Now convert to records with timestamps as strings
            records = filtered_df_copy.replace({pd.NA: None}).to_dict('records')

            # Prepare export data
            export_data = {
                'metadata': metadata,
                'data': records
            }

            # Set default save location
            default_dir = os.path.expanduser("~/crypto_data")
            os.makedirs(default_dir, exist_ok=True)

            # Generate descriptive filename
            filename = self._generate_filename(is_selected=True)
            filepath = os.path.join(default_dir, filename)

            print(f"DEBUG: Starting to save data to {filepath}")

            # Save with proper JSON serialization
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

            print(f"DEBUG: Successfully saved data to {filepath}")

            # Show feedback in status bar
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"Data saved to {filepath}")

            # Show toast notification
            self.show_save_notification(filepath)

            # Send to server if needed
            self._send_to_server_if_needed(filepath, export_data)

        except Exception as e:
            print(f"DEBUG: Error in save operation: {str(e)}")
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"Error saving data: {str(e)}")

    def show_save_notification(self, filepath):
        """Shows a notification when data is saved successfully"""
        print("DEBUG: Showing save notification for", filepath)

        # 1. Send system notification via notify-send (this works well)
        try:
            import subprocess
            subprocess.Popen([
                'notify-send',
                'Data Saved',
                f'File saved to {os.path.basename(filepath)}',
                '--icon=document-save'
            ])
        except Exception as e:
            print(f"DEBUG: Error sending system notification: {str(e)}")

        # 2. Show status bar message for longer duration
        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage(f"Data saved to {filepath}", 5000)  # Show for 5 seconds



    def _fade_out_notification(self, notification):
        """Animate notification removal"""
        if notification in getattr(self, 'active_notifications', []):
            self.active_notifications.remove(notification)

        # Create fade-out animation
        anim = QPropertyAnimation(notification, b"geometry")
        anim.setDuration(300)
        start_rect = notification.geometry()
        end_rect = QRect(
            self.browser.width(),
            start_rect.y(),
            start_rect.width(),
            start_rect.height()
        )
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(notification.deleteLater)
        anim.start()
    def _close_notification(self):
        """Safely close the notification"""
        if hasattr(self, 'save_notification') and self.save_notification:
            self.save_notification.deleteLater()
            self.save_notification = None
    def _send_to_server_if_needed(self, local_filepath, export_data):
        """Send data to remote server if configured in settings"""
        try:
            # Get settings from main window
            settings_tab = self.parent().settings_tab
            save_locally = settings_tab.save_locally.isChecked()

            if not save_locally:  # If not save locally only
                # Get server settings
                host = settings_tab.host.text()
                port = settings_tab.port.value()
                secure = settings_tab.secure.isChecked()
                protocol = "https" if settings_tab.http_radio.isChecked() and secure else "http"
                protocol = "tcp" if settings_tab.tcp_radio.isChecked() else protocol
                api_path = settings_tab.api_path.text()

                # Add to request queue for server upload with visualization in pipe tab
                task_id = self.request_queue.add_request(
                    task_type="upload_data",
                    data=export_data,
                    endpoint=f"{protocol}://{host}:{port}{api_path}",
                    callback=self._on_server_upload_complete,
                    priority=5,  # High priority for uploads
                    metadata={
                        "symbol": self.current_symbol,
                        "timeframe": self.timeframe_combo.currentText(),
                        "filepath": local_filepath
                    }
                )

                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(f"Uploading data to server (Task ID: {task_id})")

        except Exception as e:
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"Error preparing server upload: {str(e)}")

    def _on_server_upload_complete(self, result, error=None, metadata=None):
        """Callback for server upload completion"""
        if error:
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"Error uploading to server: {error}")
        else:
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    f"Successfully uploaded {metadata.get('symbol', 'data')} to server")

    def on_range_received(self, range_data):
        """Обработчик получения данных о выбранном диапазоне из JavaScript"""
        if not range_data or not range_data.get('success', False):
            error_msg = range_data.get('error', 'Unknown error') if range_data else 'Failed to get range data'
            QMessageBox.warning(self, "Selection Error", 
                              f"Unable to determine selected range: {error_msg}\n"
                              "Try zooming or selecting an area on the chart first.")
            return
            
        try:
            # Извлекаем диапазон дат
            x_range = range_data.get('xRange', [])
            
            if not x_range or len(x_range) < 2:
                QMessageBox.warning(self, "Selection Error", 
                                   "Invalid date range received from chart.")
                return
                
            # Преобразуем строки дат из plotly в datetime
            start_date = pd.to_datetime(x_range[0])
            end_date = pd.to_datetime(x_range[1])
            
            # Фильтруем данные по выбранному диапазону
            selected_data = self.data[(self.data['timestamp'] >= start_date) & 
                                      (self.data['timestamp'] <= end_date)]
            
            if selected_data.empty:
                QMessageBox.warning(self, "Selection Error", 
                                   "No data points in the selected range.")
                return
                
            # Получаем путь для сохранения
            default_dir = os.path.expanduser("~/crypto_data")
            os.makedirs(default_dir, exist_ok=True)
            
            default_filename = f"{self.current_symbol.replace('/', '_')}_{self.timeframe_combo.currentText()}_selection.json"
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Selected Data as JSON", 
                os.path.join(default_dir, default_filename),
                "JSON Files (*.json)"
            )
            
            if filepath:
                # Преобразуем DataFrame в формат JSON
                json_data = {
                    "metadata": {
                        "symbol": self.current_symbol,
                        "timeframe": self.timeframe_combo.currentText(),
                        "selection_start": start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        "selection_end": end_date.strftime('%Y-%m-%d %H:%M:%S'),
                        "export_time": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "export_type": "selected_range",
                        "points_count": len(selected_data)
                    },
                    "data": selected_data.to_dict(orient='records')
                }
                
                # Сохраняем в файл
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4, default=str)
                
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(f"Selected data ({len(selected_data)} points) saved to {filepath}", 5000)
                print(f"DEBUG: Выбранные данные ({len(selected_data)} точек) сохранены в {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save selected data: {str(e)}")
            print(f"DEBUG: Ошибка при сохранении выбранных данных: {e}")

    def export_data(self):
        """Exports data according to settings from Settings tab"""
        # This method is now obsolete and replaced by save_data_json and save_selected_data
        self.save_data_json()
