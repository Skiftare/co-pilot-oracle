import sys
import os

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import CryptoAnalyzerGUI
from src.exchange.kucoin_client import KuCoinMarketClient
from src.database.repository import MarketRepository

async def main():
    app = QApplication(sys.argv)
    
    # Инициализируем компоненты
    client = KuCoinMarketClient()
    repository = MarketRepository({
        'dbname': 'postgres',
        'user': 'postgres',
        'password': 'postgres',
        'host': 'localhost',
        'port': '5432'
    })
    
    window = CryptoAnalyzerGUI(client, repository)
    window.show()
    
    # Создаем event loop для асинхронных операций
    while True:
        app.processEvents()
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main()) 