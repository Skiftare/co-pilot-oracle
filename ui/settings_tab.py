from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QCheckBox, QGroupBox, QLineEdit,
                             QRadioButton, QSpinBox, QFormLayout, QComboBox,
                             QTabWidget, QSlider, QColorDialog, QFrame)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor


class ColorSelector(QFrame):
    def __init__(self, default_color="#4CAF50", parent=None):
        super().__init__(parent)
        self.setObjectName("colorSelector")
        self.color = QColor(default_color)

        # Минимальный размер селектора
        self.setMinimumSize(QSize(30, 20))
        self.setMaximumSize(QSize(30, 20))

        # Делаем рамку вокруг цвета
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Plain)

        # Устанавливаем цвет фона
        self.setStyleSheet(f"background-color: {default_color};")

        # Разрешаем клик
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        # Показываем диалог выбора цвета
        color = QColorDialog.getColor(self.color, self, "Select Color")

        if color.isValid():
            self.color = color
            self.setStyleSheet(f"background-color: {color.name()};")


class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Создаем вкладки настроек
        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")

        # Вкладка API настроек
        api_tab = self.create_api_settings()
        tabs.addTab(api_tab, QIcon("resources/icons/api_settings.png"), "API Settings")

        # Вкладка настроек внешнего вида
        display_tab = self.create_display_settings()
        tabs.addTab(display_tab, QIcon("resources/icons/display_settings.png"), "Display")

        # Вкладка настроек экспорта
        export_tab = self.create_export_settings()
        tabs.addTab(export_tab, QIcon("resources/icons/export_settings.png"), "Export")

        # Добавляем вкладки в основной layout
        layout.addWidget(tabs)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.setIcon(QIcon("resources/icons/reset.png"))

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setIcon(QIcon("resources/icons/save.png"))

        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.save_btn)

        # Добавляем кнопки в основной layout
        layout.addLayout(buttons_layout)

    def create_api_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Группа общих настроек API
        general_group = QGroupBox("General API Settings")
        general_group.setObjectName("settingsGroup")
        general_layout = QFormLayout(general_group)

        # Выбор API источника
        api_source = QComboBox()
        api_source.addItems(["ccxt", "CoinAPI", "CryptoCompare", "Custom API"])
        api_source.setObjectName("styledComboBox")
        general_layout.addRow(QLabel("API Source:"), api_source)

        # Настройки rate limit
        auto_retry = QCheckBox("Enabled")
        auto_retry.setChecked(True)
        general_layout.addRow(QLabel("Auto retry on rate limit:"), auto_retry)

        # Задержка между запросами
        delay_spin = QSpinBox()
        delay_spin.setRange(0, 5000)
        delay_spin.setValue(200)
        delay_spin.setSuffix(" ms")
        delay_spin.setObjectName("styledSpinBox")
        general_layout.addRow(QLabel("Delay between requests:"), delay_spin)

        # Максимальное число повторов
        retry_spin = QSpinBox()
        retry_spin.setRange(0, 10)
        retry_spin.setValue(3)
        retry_spin.setObjectName("styledSpinBox")
        general_layout.addRow(QLabel("Maximum retries:"), retry_spin)

        # Добавляем группу общих настроек
        layout.addWidget(general_group)

        # Группа настроек API ключей
        keys_group = QGroupBox("API Keys")
        keys_group.setObjectName("settingsGroup")
        keys_layout = QFormLayout(keys_group)

        # Binance API ключи
        binance_key = QLineEdit()
        binance_key.setPlaceholderText("Enter your Binance API key")
        binance_key.setObjectName("styledLineEdit")
        keys_layout.addRow(QLabel("Binance API Key:"), binance_key)

        binance_secret = QLineEdit()
        binance_secret.setPlaceholderText("Enter your Binance API secret")
        binance_secret.setObjectName("styledLineEdit")
        binance_secret.setEchoMode(QLineEdit.Password)
        keys_layout.addRow(QLabel("Binance API Secret:"), binance_secret)

        # Coinbase API ключи
        coinbase_key = QLineEdit()
        coinbase_key.setPlaceholderText("Enter your Coinbase API key")
        coinbase_key.setObjectName("styledLineEdit")
        keys_layout.addRow(QLabel("Coinbase API Key:"), coinbase_key)

        coinbase_secret = QLineEdit()
        coinbase_secret.setPlaceholderText("Enter your Coinbase API secret")
        coinbase_secret.setObjectName("styledLineEdit")
        coinbase_secret.setEchoMode(QLineEdit.Password)
        keys_layout.addRow(QLabel("Coinbase API Secret:"), coinbase_secret)

        # Добавляем группу настроек ключей
        layout.addWidget(keys_group)

        # Добавляем растягивающийся элемент внизу
        layout.addStretch()

        return widget

    def create_display_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Группа настроек графиков
        chart_group = QGroupBox("Chart Settings")
        chart_group.setObjectName("settingsGroup")
        chart_layout = QFormLayout(chart_group)

        # Настройка темы
        theme_combo = QComboBox()
        theme_combo.addItems(["Dark Theme", "Light Theme", "Blue Theme", "Monochrome"])
        theme_combo.setObjectName("styledComboBox")
        chart_layout.addRow(QLabel("Chart Theme:"), theme_combo)

        # Тип графика по умолчанию
        chart_type = QComboBox()
        chart_type.addItems(["Candlestick", "OHLC", "Line", "Area"])
        chart_type.setObjectName("styledComboBox")
        chart_layout.addRow(QLabel("Default Chart Type:"), chart_type)

        # Настройки временных интервалов
        timeframe = QComboBox()
        timeframe.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        timeframe.setCurrentText("1h")
        timeframe.setObjectName("styledComboBox")
        chart_layout.addRow(QLabel("Default Timeframe:"), timeframe)

        # Количество свечей по умолчанию
        candles_spin = QSpinBox()
        candles_spin.setRange(50, 1000)
        candles_spin.setValue(100)
        candles_spin.setObjectName("styledSpinBox")
        chart_layout.addRow(QLabel("Default Number of Candles:"), candles_spin)

        # Настройки отображения
        show_volume = QCheckBox("Enabled")
        show_volume.setChecked(True)
        chart_layout.addRow(QLabel("Show Volume by Default:"), show_volume)

        show_tooltips = QCheckBox("Enabled")
        show_tooltips.setChecked(True)
        chart_layout.addRow(QLabel("Show Tooltips:"), show_tooltips)

        # Добавляем группу настроек графиков
        layout.addWidget(chart_group)

        # Группа настроек цветов
        color_group = QGroupBox("Color Settings")
        color_group.setObjectName("settingsGroup")
        color_layout = QFormLayout(color_group)

        # Цвет свечей роста
        bullish_color = ColorSelector("#4CAF50")
        color_layout.addRow(QLabel("Bullish Candle Color:"), bullish_color)

        # Цвет свечей падения
        bearish_color = ColorSelector("#F44336")
        color_layout.addRow(QLabel("Bearish Candle Color:"), bearish_color)

        # Цвет MA
        ma_color = ColorSelector("#FFC107")
        color_layout.addRow(QLabel("Moving Average Color:"), ma_color)

        # Цвет EMA
        ema_color = ColorSelector("#2196F3")
        color_layout.addRow(QLabel("EMA Color:"), ema_color)

        # Цвет объема
        volume_color = ColorSelector("#607D8B")
        color_layout.addRow(QLabel("Volume Color:"), volume_color)

        # Добавляем группу настроек цветов
        layout.addWidget(color_group)

        # Добавляем растягивающийся элемент внизу
        layout.addStretch()

        return widget

    def create_export_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Группа настроек экспорта файлов
        file_group = QGroupBox("File Export Settings")
        file_group.setObjectName("settingsGroup")
        file_layout = QFormLayout(file_group)

        # Формат файла по умолчанию
        file_format = QComboBox()
        file_format.addItems(["CSV", "JSON", "Excel", "SQLite"])
        file_format.setObjectName("styledComboBox")
        file_layout.addRow(QLabel("Default Export Format:"), file_format)

        # Путь по умолчанию
        default_path = QLineEdit()
        default_path.setText("~/crypto_data")
        default_path.setObjectName("styledLineEdit")
        file_layout.addRow(QLabel("Default Export Path:"), default_path)

        # Добавляем группу настроек файлов
        layout.addWidget(file_group)

        # Группа настроек удаленного сервера
        remote_group = QGroupBox("Remote Server Settings")
        remote_group.setObjectName("settingsGroup")
        remote_layout = QFormLayout(remote_group)

        # Настройки хоста
        host = QLineEdit()
        host.setText("127.0.0.1")
        host.setObjectName("styledLineEdit")
        remote_layout.addRow(QLabel("Default Remote Host:"), host)

        # Настройки порта
        port = QSpinBox()
        port.setRange(1, 65535)
        port.setValue(8000)
        port.setObjectName("styledSpinBox")
        remote_layout.addRow(QLabel("Default Remote Port:"), port)

        # Протокол передачи
        protocol_layout = QHBoxLayout()
        http_radio = QRadioButton("HTTP")
        tcp_radio = QRadioButton("TCP")
        http_radio.setChecked(True)
        http_radio.setObjectName("styledRadio")
        tcp_radio.setObjectName("styledRadio")

        protocol_layout.addWidget(http_radio)
        protocol_layout.addWidget(tcp_radio)
        protocol_layout.addStretch()

        remote_layout.addRow(QLabel("Transport Protocol:"), protocol_layout)

        # Безопасное соединение
        secure = QCheckBox("Enable SSL/TLS")
        secure.setChecked(True)
        remote_layout.addRow(QLabel("Secure Connection:"), secure)

        # Путь к API на удаленном сервере
        api_path = QLineEdit()
        api_path.setText("/api/v1/crypto/data")
        api_path.setObjectName("styledLineEdit")
        remote_layout.addRow(QLabel("API Endpoint Path:"), api_path)

        # Добавляем группу настроек удаленного сервера
        layout.addWidget(remote_group)

        # Добавляем растягивающийся элемент внизу
        layout.addStretch()

        return widget