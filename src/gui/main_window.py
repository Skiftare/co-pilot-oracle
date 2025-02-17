from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QRadioButton, QLineEdit, QPushButton, QLabel, 
                            QButtonGroup, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import asyncio
from src.exchange.kucoin_client import KuCoinMarketClient
from src.database.repository import MarketRepository

class CryptoAnalyzerGUI(QMainWindow):
    def __init__(self, client: KuCoinMarketClient, repository: MarketRepository):
        super().__init__()
        self.client = client
        self.repository = repository
        self.current_symbol = None
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
        # Настройка внешнего вида
        self.setWindowTitle("Crypto Analyzer")
        self.setMinimumSize(1200, 800)
        
        # Основной виджет и layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Верхняя панель управления
        control_panel = QFrame()
        control_layout = QHBoxLayout(control_panel)
        
        self.pair_input = QLineEdit()
        self.pair_input.setPlaceholderText("Введите криптовалюту (например: BTC)")
        control_layout.addWidget(self.pair_input)
        
        analyze_button = QPushButton("Анализировать")
        analyze_button.clicked.connect(self.update_data)
        control_layout.addWidget(analyze_button)
        
        layout.addWidget(control_panel)
        
        # Настройка графиков
        pg.setConfigOptions(antialias=True)
        
        # График цены
        self.price_plot = pg.PlotWidget(title="Price Chart")
        self.price_plot.showGrid(x=True, y=True)
        self.price_plot.setLabel('left', 'Price', units='USDT')
        self.price_plot.setLabel('bottom', 'Time')
        layout.addWidget(self.price_plot)
        
        # График объема
        self.volume_plot = pg.PlotWidget(title="Volume")
        self.volume_plot.showGrid(x=True, y=True)
        self.volume_plot.setLabel('left', 'Volume')
        self.volume_plot.setLabel('bottom', 'Time')
        layout.addWidget(self.volume_plot)
        
        # Область для текста
        self.predict_text = QLabel()
        self.predict_text.setWordWrap(True)
        layout.addWidget(self.predict_text)
        
        # Таймер для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.setInterval(5000)  # обновление каждые 5 секунд
        
    def update_data(self):
        """Обновление данных и графика"""
        if self.current_symbol:
            asyncio.create_task(self.show_pair_analysis(self.current_symbol))
        else:
            base_currency = self.pair_input.text().strip().upper()
            if base_currency:
                self.current_symbol = f"{base_currency}-USDT"
                self.update_timer.start()  # запускаем автообновление
                asyncio.create_task(self.show_pair_analysis(self.current_symbol))

    async def show_pair_analysis(self, symbol: str):
        """Отображение анализа конкретной пары"""
        self.logger.info(f"Обновление данных для {symbol}")
        try:
            # Получаем исторические данные за последний час
            klines = await self.client.get_kline_data(symbol, kline_type='1min', size=60)
            
            if klines:
                # Преобразуем данные в DataFrame
                df = pd.DataFrame(klines, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                df['price'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                self.logger.debug(f"Получено {len(df)} точек данных")
                
                # Обновляем графики
                self.update_charts(df)
                
                # Анализируем данные
                mean_price = df['price'].mean()
                std_price = df['price'].std()
                current_price = df['price'].iloc[-1]
                z_score = (current_price - mean_price) / std_price if std_price != 0 else 0
                
                analysis_text = f"""
Текущая цена: {current_price:.2f}
Среднее значение: {mean_price:.2f}
Стандартное отклонение: {std_price:.2f}
Z-score: {z_score:.2f}

Анализ: {'Возможна перекупленность' if z_score > 2 else 'Возможна перепроданность' if z_score < -2 else 'Нормальный диапазон'}
"""
                self.predict_text.setText(analysis_text)
                
            else:
                self.logger.warning("Нет данных для анализа")
                self.predict_text.setText("Нет данных для анализа")
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе {symbol}: {e}")
            self.update_timer.stop()
            QMessageBox.warning(
                self,
                "Ошибка анализа",
                f"Не удалось проанализировать пару {symbol}: {str(e)}"
            )

    def update_charts(self, df: pd.DataFrame):
        """Обновление графиков"""
        try:
            # Конвертируем время в timestamp для pyqtgraph
            timestamps = df['time'].apply(lambda x: x.timestamp())
            
            # Очищаем предыдущие графики
            self.price_plot.clear()
            self.volume_plot.clear()
            
            # Отрисовка графика цены
            self.price_plot.plot(timestamps, df['price'].values, pen='b')
            
            # Отрисовка графика объема
            self.volume_plot.plot(timestamps, df['volume'].values, pen='r')
            
            # Обновляем подписи времени
            self.price_plot.getAxis('bottom').setTicks([[(t, df['time'][i].strftime('%H:%M')) 
                                                        for i, t in enumerate(timestamps)]])
            self.volume_plot.getAxis('bottom').setTicks([[(t, df['time'][i].strftime('%H:%M')) 
                                                         for i, t in enumerate(timestamps)]])
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении графиков: {e}") 