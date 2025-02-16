from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QRadioButton, QLineEdit, QPushButton, QLabel, 
                            QButtonGroup, QFrame)
from PyQt6.QtCore import Qt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.graph_objs import Figure
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional
import sys
import numpy as np

class CryptoAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crypto Analyzer")
        self.setMinimumSize(1200, 800)
        
        # Основной виджет и layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Верхняя панель с выбором режима
        mode_panel = QFrame()
        mode_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        mode_layout = QHBoxLayout(mode_panel)
        
        # Группа радиокнопок для выбора режима
        self.mode_group = QButtonGroup()
        
        self.anomaly_mode = QRadioButton("Поиск аномалий")
        self.pair_mode = QRadioButton("Анализ пары")
        self.mode_group.addButton(self.anomaly_mode)
        self.mode_group.addButton(self.pair_mode)
        
        mode_layout.addWidget(self.anomaly_mode)
        mode_layout.addWidget(self.pair_mode)
        
        # Поле ввода пары
        self.pair_input = QLineEdit()
        self.pair_input.setPlaceholderText("Введите пару (например: BTC-USDT)")
        self.pair_input.setEnabled(False)
        mode_layout.addWidget(self.pair_input)
        
        # Кнопка обновления
        self.update_btn = QPushButton("Обновить")
        mode_layout.addWidget(self.update_btn)
        
        layout.addWidget(mode_panel)
        
        # Область графика
        self.chart_frame = QFrame()
        self.chart_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        chart_layout = QVBoxLayout(self.chart_frame)
        
        # Plotly виджет
        self.chart_widget = QWidget()
        chart_layout.addWidget(self.chart_widget)
        
        layout.addWidget(self.chart_frame)
        
        # Область предсказания
        predict_panel = QFrame()
        predict_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        predict_layout = QVBoxLayout(predict_panel)
        
        predict_label = QLabel("Предсказание:")
        predict_layout.addWidget(predict_label)
        
        self.predict_text = QLabel("Ожидание данных...")
        predict_layout.addWidget(self.predict_text)
        
        layout.addWidget(predict_panel)
        
        # Подключаем сигналы
        self.mode_group.buttonClicked.connect(self.on_mode_change)
        self.pair_input.returnPressed.connect(self.update_data)
        self.update_btn.clicked.connect(self.update_data)
        
        # Устанавливаем режим по умолчанию
        self.anomaly_mode.setChecked(True)
        
        # Инициализируем график
        self.figure: Optional[Figure] = None
        self.init_chart()
        
    def on_mode_change(self):
        """Обработчик изменения режима"""
        self.pair_input.setEnabled(self.pair_mode.isChecked())
        self.update_data()
        
    def update_data(self):
        """Обновление данных и графика"""
        if self.anomaly_mode.isChecked():
            self.show_anomalies()
        else:
            pair = self.pair_input.text().strip().upper()
            if pair:
                self.show_pair_analysis(pair)
                
    def init_chart(self):
        """Инициализация графика"""
        self.figure = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.05,
            subplot_titles=('Price', 'Volume')
        )
        
        self.figure.update_layout(
            template='plotly_dark',
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        # Отображаем пустой график
        self.update_chart()
        
    def show_pair_analysis(self, pair: str):
        """Отображение анализа конкретной пары"""
        # Получаем данные из базы
        df = self.get_pair_data(pair)
        if df is None or df.empty:
            self.predict_text.setText(f"Нет данных для пары {pair}")
            return
            
        # Обновляем график
        self.figure = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.05,
            subplot_titles=(f'{pair} Price', 'Volume')
        )
        
        # Добавляем свечи
        self.figure.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='OHLC'
            ),
            row=1, col=1
        )
        
        # Добавляем объем
        self.figure.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume'
            ),
            row=2, col=1
        )
        
        self.figure.update_layout(
            template='plotly_dark',
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        self.update_chart()
        
    def show_anomalies(self):
        """Отображение найденных аномалий"""
        self.predict_text.setText("Поиск аномалий...")
        # TODO: Реализовать поиск аномалий
        
    def update_chart(self):
        """Обновление отображения графика"""
        if self.figure:
            self.figure.write_html("temp.html")
            # TODO: Встроить график в QWidget
            
    def get_pair_data(self, pair: str) -> Optional[pd.DataFrame]:
        """Получение данных пары из базы"""
        # TODO: Реализовать получение данных из базы
        # Временные тестовые данные
        dates = pd.date_range(start='2024-01-01', end='2024-02-16', freq='1H')
        df = pd.DataFrame(index=dates)
        df['open'] = 100 + np.random.randn(len(dates))*10
        df['high'] = df['open'] + abs(np.random.randn(len(dates))*2)
        df['low'] = df['open'] - abs(np.random.randn(len(dates))*2)
        df['close'] = df['open'] + np.random.randn(len(dates))*2
        df['volume'] = abs(np.random.randn(len(dates))*1000)
        return df 