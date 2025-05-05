from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QCheckBox, QGroupBox, QLineEdit,
                             QRadioButton, QSpinBox, QFormLayout, QComboBox,
                             QTabWidget, QSlider, QColorDialog, QFrame,
                             QScrollArea, QSizePolicy)
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
        self.setObjectName("settingsTab")  # Add this for easier reference
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
        self.reset_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setIcon(QIcon("resources/icons/save.png"))
        self.save_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.save_btn)

        # Добавляем кнопки в основной layout
        layout.addLayout(buttons_layout)

    def create_api_settings(self):
        # Создаем прокручиваемую область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Группа общих настроек API
        general_group = QGroupBox("General API Settings")
        general_group.setObjectName("settingsGroup")
        general_layout = QFormLayout(general_group)
        general_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Выбор API источника
        api_source = QComboBox()
        api_source.addItems(["KuCoin (ccxt)", "CryptoCompare", "Custom API"])
        api_source.setCurrentText("KuCoin (ccxt)")
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
        keys_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # KuCoin API ключи
        kucoin_key = QLineEdit()
        kucoin_key.setPlaceholderText("Введите ваш KuCoin API ключ")
        kucoin_key.setObjectName("styledLineEdit")
        keys_layout.addRow(QLabel("KuCoin API Key:"), kucoin_key)

        kucoin_secret = QLineEdit()
        kucoin_secret.setPlaceholderText("Введите ваш KuCoin API секрет")
        kucoin_secret.setObjectName("styledLineEdit")
        kucoin_secret.setEchoMode(QLineEdit.Password)
        keys_layout.addRow(QLabel("KuCoin API Secret:"), kucoin_secret)

        kucoin_passphrase = QLineEdit()
        kucoin_passphrase.setPlaceholderText("Введите вашу KuCoin API passphrase")
        kucoin_passphrase.setObjectName("styledLineEdit")
        kucoin_passphrase.setEchoMode(QLineEdit.Password)
        keys_layout.addRow(QLabel("KuCoin API Passphrase:"), kucoin_passphrase)

        # Добавляем группу настроек ключей
        layout.addWidget(keys_group)

        # Группа настроек кэша
        cache_group = QGroupBox("Cache Settings")
        cache_group.setObjectName("settingsGroup")
        cache_layout = QFormLayout(cache_group)
        cache_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Включение/выключение кэша
        enable_cache = QCheckBox("Enabled")
        enable_cache.setChecked(True)
        cache_layout.addRow(QLabel("Use Local Cache:"), enable_cache)

        # Максимальный размер кэша
        cache_size = QSpinBox()
        cache_size.setRange(10, 1000)
        cache_size.setValue(100)
        cache_size.setSuffix(" MB")
        cache_size.setObjectName("styledSpinBox")
        cache_layout.addRow(QLabel("Maximum Cache Size:"), cache_size)

        # Время жизни кэша
        cache_ttl = QSpinBox()
        cache_ttl.setRange(1, 30)
        cache_ttl.setValue(1)
        cache_ttl.setSuffix(" day(s)")
        cache_ttl.setObjectName("styledSpinBox")
        cache_layout.addRow(QLabel("Cache Lifetime:"), cache_ttl)

        # Кнопка очистки кэша
        clear_cache_btn = QPushButton("Clear Cache Now")
        clear_cache_btn.setObjectName("secondaryButton")
        clear_cache_btn.clicked.connect(self.clear_cache)
        cache_layout.addRow("", clear_cache_btn)

        # Добавляем группу настроек кэша
        layout.addWidget(cache_group)

        # Добавляем растягивающийся элемент внизу
        layout.addStretch()
        
        # Устанавливаем виджет в область прокрутки
        scroll.setWidget(widget)
        return scroll

    def create_display_settings(self):
        # Создаем прокручиваемую область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Группа настроек графиков
        chart_group = QGroupBox("Chart Settings")
        chart_group.setObjectName("settingsGroup")
        chart_layout = QFormLayout(chart_group)
        chart_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

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

        # Группа настроек цветов с адаптивным макетом
        color_group = QGroupBox("Color Settings")
        color_group.setObjectName("settingsGroup")
        color_layout = QFormLayout(color_group)
        color_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

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
        
        # Устанавливаем виджет в область прокрутки
        scroll.setWidget(widget)
        return scroll

    def create_export_settings(self):
        # Создаем прокручиваемую область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Группа настроек экспорта файлов
        file_group = QGroupBox("File Export Settings")
        file_group.setObjectName("settingsGroup")
        file_layout = QFormLayout(file_group)
        file_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

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
        
        # Опция сохранения только на локальной машине
        self.save_locally = QCheckBox("Save on local machine only")
        self.save_locally.setChecked(True)
        self.save_locally.stateChanged.connect(self.toggle_remote_settings)
        file_layout.addRow("", self.save_locally)

        # Добавляем группу настроек файлов
        layout.addWidget(file_group)

        # Группа настроек удаленного сервера
        self.remote_group = QGroupBox("Remote Server Settings")
        self.remote_group.setObjectName("settingsGroup")
        remote_layout = QFormLayout(self.remote_group)
        remote_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Настройки хоста
        self.host = QLineEdit()
        self.host.setText("127.0.0.1")
        self.host.setObjectName("styledLineEdit")
        remote_layout.addRow(QLabel("Default Remote Host:"), self.host)

        # Настройки порта
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(8000)
        self.port.setObjectName("styledSpinBox")
        remote_layout.addRow(QLabel("Default Remote Port:"), self.port)

        # Протокол передачи - адаптивный layout
        protocol_widget = QWidget()
        protocol_layout = QHBoxLayout(protocol_widget)
        protocol_layout.setContentsMargins(0, 0, 0, 0)
        
        self.http_radio = QRadioButton("HTTP")
        self.tcp_radio = QRadioButton("TCP")
        self.http_radio.setChecked(True)
        self.http_radio.setObjectName("styledRadio")
        self.tcp_radio.setObjectName("styledRadio")

        protocol_layout.addWidget(self.http_radio)
        protocol_layout.addWidget(self.tcp_radio)
        protocol_layout.addStretch()

        remote_layout.addRow(QLabel("Transport Protocol:"), protocol_widget)

        # Безопасное соединение
        self.secure = QCheckBox("Enable SSL/TLS")
        self.secure.setChecked(True)
        remote_layout.addRow(QLabel("Secure Connection:"), self.secure)

        # Путь к API на удаленном сервере
        self.api_path = QLineEdit()
        self.api_path.setText("/api/v1/crypto/data")
        self.api_path.setObjectName("styledLineEdit")
        remote_layout.addRow(QLabel("API Endpoint Path:"), self.api_path)

        # Добавляем группу настроек удаленного сервера
        layout.addWidget(self.remote_group)
        
        # Инициализируем состояние удаленных настроек в соответствии с чекбоксом
        self.toggle_remote_settings(self.save_locally.isChecked())

        # Добавляем растягивающийся элемент внизу
        layout.addStretch()
        
        # Устанавливаем виджет в область прокрутки
        scroll.setWidget(widget)
        return scroll
        
    def toggle_remote_settings(self, checked):
        """Включает/выключает настройки удаленного сервера в зависимости от флажка локального сохранения"""
        self.remote_group.setEnabled(not checked)
        
        # Дополнительно можно изменить внешний вид для лучшей обратной связи
        if checked:
            self.remote_group.setStyleSheet("color: gray;")
        else:
            self.remote_group.setStyleSheet("")

    def clear_cache(self):
        """Очищает кэш API через api_client"""
        try:
            # Получаем api_client из главного окна
            api_client = self.main_window.api_client
            
            # Очищаем кэш
            count = api_client.clear_cache()
            
            # Показываем сообщение об успехе
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Cache Cleared", 
                                   f"Successfully cleared {count} cache entries.")
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to clear cache: {str(e)}")