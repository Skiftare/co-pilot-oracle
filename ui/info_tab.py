from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QDateEdit, QCheckBox,
                             QFrame, QToolButton, QSizePolicy, QSplitter,
                             QLineEdit, QCompleter, QAction, QMenu, QApplication)
from PyQt5.QtCore import Qt, QDateTime, QSize, pyqtSignal, QStringListModel  # Добавлен импорт QStringListModel
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot
import pandas as pd


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

        # Поле ввода с автодополнением
        self.pair_input = QLineEdit()
        self.pair_input.setObjectName("pairInput")
        self.pair_input.setPlaceholderText("Enter or select trading pair...")

        # Создаем автодополнение
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.pair_input.setCompleter(self.completer)

        # Кнопка выбора с выпадающим меню
        self.select_btn = QToolButton()
        self.select_btn.setIcon(QIcon("resources/icons/dropdown.png"))
        self.select_btn.setPopupMode(QToolButton.InstantPopup)
        self.select_btn.setObjectName("pairSelectButton")

        # Создаем меню
        self.pair_menu = QMenu()
        self.select_btn.setMenu(self.pair_menu)

        # Кнопка для копирования текущей пары
        self.copy_btn = QToolButton()
        self.copy_btn.setIcon(QIcon("resources/icons/copy.png"))
        self.copy_btn.setToolTip("Copy pair name")
        self.copy_btn.setObjectName("copyButton")
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

        # Создаем горизонтальный layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Кнопки инструментов для графика
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setIcon(QIcon("resources/icons/zoom_in.png"))
        self.zoom_in_btn.setIconSize(QSize(18, 18))
        self.zoom_in_btn.setToolTip("Zoom In")
        self.zoom_in_btn.setObjectName("chartToolButton")

        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setIcon(QIcon("resources/icons/zoom_out.png"))
        self.zoom_out_btn.setIconSize(QSize(18, 18))
        self.zoom_out_btn.setToolTip("Zoom Out")
        self.zoom_out_btn.setObjectName("chartToolButton")

        self.reset_btn = QToolButton()
        self.reset_btn.setIcon(QIcon("resources/icons/reset.png"))
        self.reset_btn.setIconSize(QSize(18, 18))
        self.reset_btn.setToolTip("Reset View")
        self.reset_btn.setObjectName("chartToolButton")

        self.save_img_btn = QToolButton()
        self.save_img_btn.setIcon(QIcon("resources/icons/save.png"))
        self.save_img_btn.setIconSize(QSize(18, 18))
        self.save_img_btn.setToolTip("Save as Image")
        self.save_img_btn.setObjectName("chartToolButton")

        # Добавляем кнопки в layout
        layout.addWidget(self.zoom_in_btn)
        layout.addWidget(self.zoom_out_btn)
        layout.addWidget(self.reset_btn)
        layout.addSpacing(20)
        layout.addWidget(self.save_img_btn)
        layout.addStretch()


class IndicatorPanel(QFrame):
    indicatorChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("indicatorPanel")

        # Создаем вертикальный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        title = QLabel("Indicators")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # Индикаторы
        self.ma_check = QCheckBox("Moving Average")
        self.ma_check.setObjectName("indicatorCheck")
        self.ma_check.stateChanged.connect(self.on_indicator_changed)

        self.ema_check = QCheckBox("EMA")
        self.ema_check.setObjectName("indicatorCheck")
        self.ema_check.stateChanged.connect(self.on_indicator_changed)

        self.rsi_check = QCheckBox("RSI")
        self.rsi_check.setObjectName("indicatorCheck")
        self.rsi_check.stateChanged.connect(self.on_indicator_changed)

        self.macd_check = QCheckBox("MACD")
        self.macd_check.setObjectName("indicatorCheck")
        self.macd_check.stateChanged.connect(self.on_indicator_changed)

        self.bollinger_check = QCheckBox("Bollinger Bands")
        self.bollinger_check.setObjectName("indicatorCheck")
        self.bollinger_check.stateChanged.connect(self.on_indicator_changed)

        # Добавляем индикаторы в layout
        layout.addWidget(self.ma_check)
        layout.addWidget(self.ema_check)
        layout.addWidget(self.rsi_check)
        layout.addWidget(self.macd_check)
        layout.addWidget(self.bollinger_check)
        layout.addStretch()

    def on_indicator_changed(self):
        self.indicatorChanged.emit()


class InfoTab(QWidget):
    def __init__(self, api_client, request_queue):
        super().__init__()
        self.api_client = api_client
        self.request_queue = request_queue
        self.data = None  # Для хранения текущих данных
        self.current_symbol = "BTC/USDT"  # Пара по умолчанию
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Верхняя панель с контролами
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_layout = QHBoxLayout(controls_frame)

        # Селектор торговой пары
        pair_layout = QVBoxLayout()
        pair_label = QLabel("Trading Pair")
        pair_label.setObjectName("controlLabel")
        self.pair_selector = PairSelector(self.api_client)
        self.pair_selector.pairSelected.connect(self.on_pair_selected)
        pair_layout.addWidget(pair_label)
        pair_layout.addWidget(self.pair_selector)
        controls_layout.addLayout(pair_layout)

        # Выбор таймфрейма
        timeframe_layout = QVBoxLayout()
        timeframe_label = QLabel("Timeframe")
        timeframe_label.setObjectName("controlLabel")
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        self.timeframe_combo.setCurrentText("1h")
        self.timeframe_combo.setObjectName("styledComboBox")
        timeframe_layout.addWidget(timeframe_label)
        timeframe_layout.addWidget(self.timeframe_combo)
        controls_layout.addLayout(timeframe_layout)

        # Выбор даты
        date_layout = QVBoxLayout()
        date_label = QLabel("From Date")
        date_label.setObjectName("controlLabel")
        self.date_edit = QDateEdit(QDateTime.currentDateTime().addDays(-7).date())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setObjectName("styledDateEdit")
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        controls_layout.addLayout(date_layout)

        # Кнопка загрузки
        load_layout = QVBoxLayout()
        # Добавляем пустую метку для выравнивания
        load_layout.addWidget(QLabel(""))
        self.load_btn = QPushButton("Load Data")
        self.load_btn.setObjectName("primaryButton")
        self.load_btn.setIcon(QIcon("resources/icons/download.png"))
        self.load_btn.clicked.connect(self.load_data)
        load_layout.addWidget(self.load_btn)
        controls_layout.addLayout(load_layout)

        # Добавляем растягивающийся элемент для выравнивания
        controls_layout.addStretch(1)

        # Добавляем верхнюю панель в основной layout
        layout.addWidget(controls_frame)

        # Создаем сплиттер для графика и панели индикаторов
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("mainSplitter")

        # Создаем контейнер для графика
        chart_container = QFrame()
        chart_container.setObjectName("chartContainer")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        # Добавляем панель инструментов для графика
        self.chart_toolbar = ChartToolBar()
        chart_layout.addWidget(self.chart_toolbar)

        # Область для графика
        self.browser = QWebEngineView()
        chart_layout.addWidget(self.browser)

        # Панель индикаторов
        self.indicator_panel = IndicatorPanel()
        self.indicator_panel.indicatorChanged.connect(self.update_indicators)

        # Добавляем в сплиттер
        splitter.addWidget(chart_container)
        splitter.addWidget(self.indicator_panel)

        # Устанавливаем соотношение размеров
        splitter.setSizes([800, 200])

        # Добавляем сплиттер в основной layout
        layout.addWidget(splitter)

        # Инициализируем пустой график
        self.create_empty_chart()

        # Подключаем события к тулбару
        self.chart_toolbar.save_img_btn.clicked.connect(self.save_chart_image)

        # Загружаем данные для пары по умолчанию
        self.load_data()

    def on_pair_selected(self, symbol):
        """Обработчик выбора торговой пары"""
        self.current_symbol = symbol
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

    def load_data(self):
        symbol = self.current_symbol
        timeframe = self.timeframe_combo.currentText()
        since = self.date_edit.date().toPyDate()

        # Изменяем текст кнопки
        self.load_btn.setText("Loading...")
        self.load_btn.setEnabled(False)

        # Детальное логирование
        print(f"DEBUG: Загружаем {symbol} с таймфреймом {timeframe} с {since}")

        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage(f"Загрузка {symbol}, таймфрейм: {timeframe}")

        # Показываем загрузочное сообщение с деталями
        loading_fig = go.Figure()
        loading_fig.add_annotation(
            text=f"Загрузка данных для {symbol}",
            xref="paper", yref="paper",
            x=0.5, y=0.6, showarrow=False,
            font=dict(size=20, color="#4CAF50")
        )

        loading_fig.add_annotation(
            text=f"Таймфрейм: {timeframe}, с даты: {since.strftime('%d.%m.%Y')}",
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

        # Добавляем запрос в очередь
        task_id = self.request_queue.add_request(
            task_type="fetch_ohlcv",
            exchange="kucoin",  # Только KuCoin
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            callback=self.update_chart
        )
        print(f"DEBUG: Запрос добавлен в очередь, ID задачи: {task_id}")

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

    def update_chart(self, data, error=None):
        # Восстанавливаем кнопку
        self.load_btn.setText("Load Data")
        self.load_btn.setEnabled(True)

        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().clearMessage()

        if error:
            error_message = f"Ошибка: {error}"
            print(f"DEBUG: Ошибка при обновлении графика: {error}")

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

            return

        # Сохраняем данные
        self.data = data
        print(f"DEBUG: Данные успешно получены, количество записей: {len(data)}")
        print(f"DEBUG: Диапазон данных: с {data['timestamp'].min()} по {data['timestamp'].max()}")

        # Обновляем график с данными и индикаторами
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
        fig.add_trace(go.Candlestick(
            x=data['timestamp'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name="OHLC"
        ))
        fig.update_layout(title=f"{self.current_symbol} Price Chart")
        html = plot(fig, output_type='div', include_plotlyjs='cdn')
        self.browser.setHtml(html)
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

        # Отображаем график
        html = plot(fig, output_type='div', include_plotlyjs='cdn', config={'responsive': True})
        self.browser.setHtml(html)

    def save_chart_image(self):
        # Заглушка для функции сохранения изображения
        print("Save chart as image functionality would go here")
        # В реальной реализации здесь был бы код для сохранения текущего графика