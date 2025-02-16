from kucoin.client import Market
from datetime import datetime
import asyncio
import logging
import json
from typing import List, Dict, Optional

class KuCoinMarketClient:
    def __init__(self):
        # Инициализация без ключей API
        self.client = Market()
        self.logger = logging.getLogger(__name__)
        
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получает текущие данные тикера для указанного символа"""
        try:
            ticker = self.client.get_ticker(symbol)
            self.logger.info(f"RAW TICKER DATA [{symbol}]: {json.dumps(ticker, indent=2)}")
            
            return {
                'symbol': symbol,
                'price': ticker['price'],
                'volume': ticker['size'],
                'time': int(ticker['time']),  # оставляем как 'time' для совместимости
                'timestamp': int(ticker['time']),  # добавляем 'timestamp' для совместимости
                'best_bid': ticker['bestBid'],
                'best_ask': ticker['bestAsk'],
                'best_bid_size': ticker['bestBidSize'],
                'best_ask_size': ticker['bestAskSize'],
                'sequence': ticker['sequence']
            }
        except Exception as e:
            self.logger.error(f"Ошибка при получении тикера {symbol}: {e}")
            return None

    async def get_all_tickers(self) -> Dict:
        """Получает данные всех тикеров"""
        try:
            response = self.client.get_all_tickers()
            self.logger.info(f"RAW ALL TICKERS DATA: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех тикеров: {e}")
            return {'ticker': []}

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Получает последние сделки по символу"""
        try:
            trades = self.client.get_trade_histories(symbol)
            self.logger.info(f"RAW TRADES DATA [{symbol}]: {json.dumps(trades[:5], indent=2)}")
            
            formatted_trades = []
            for trade in trades[:limit]:
                formatted_trades.append({
                    'symbol': symbol,
                    'trade_id': trade['sequence'],
                    'price': trade['price'],
                    'quantity': trade['size'],
                    'side': trade['side'],
                    'timestamp': int(trade['time'] / 1000000)  # конвертируем наносекунды в миллисекунды
                })
            return formatted_trades
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении истории торгов {symbol}: {e}")
            return []

    async def create_test_order(self, symbol: str, side: str, price: float, size: float) -> Dict:
        """Создает тестовый ордер через mock API"""
        try:
            # Используем тестовый эндпоинт для создания ордера
            endpoint = '/api/v1/spot-test/order'
            params = {
                'symbol': symbol,
                'side': side,
                'price': str(price),
                'size': str(size),
                'type': 'limit'
            }
            return await self.client.post(endpoint, params)
        except Exception as e:
            self.logger.error(f"Ошибка при создании тестового ордера: {e}")
            return None 