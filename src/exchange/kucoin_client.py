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
        self._last_tickers = {}  # кэш для последних тикеров
        
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получает и анализирует данные тикера"""
        try:
            ticker = self.client.get_ticker(symbol)
            
            # Получаем предыдущий тикер
            last_ticker = self._last_tickers.get(symbol)
            
            # Рассчитываем изменения
            price_change = 0
            volume_change = 0
            if last_ticker:
                price_change = ((float(ticker['price']) - float(last_ticker['price'])) 
                              / float(last_ticker['price']) * 100)
                volume_change = ((float(ticker['size']) - float(last_ticker['size'])) 
                               / float(last_ticker['size']) * 100)
            
            # Сохраняем текущий тикер
            self._last_tickers[symbol] = ticker
            
            # Возвращаем данные только если есть значимые изменения
            if abs(price_change) >= 0.1 or abs(volume_change) >= 1.0:
                return {
                    'symbol': symbol,
                    'price': ticker['price'],
                    'volume': ticker['size'],
                    'time': int(ticker['time']),
                    'best_bid': ticker['bestBid'],
                    'best_ask': ticker['bestAsk'],
                    'best_bid_size': ticker['bestBidSize'],
                    'best_ask_size': ticker['bestAskSize'],
                    'sequence': ticker['sequence'],
                    'price_change': price_change,
                    'volume_change': volume_change
                }
            return None
            
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

    async def get_recent_trades(self, symbol: str, min_volume: float = 1000) -> List[Dict]:
        """Получает только значимые сделки"""
        try:
            trades_data = self.client.get_trade_histories(symbol)
            self.logger.debug(f"RAW TRADES DATA [{symbol}]: {json.dumps(trades_data[:5], indent=2)}")
            
            significant_trades = []
            for trade in trades_data:
                # Проверяем наличие всех необходимых полей
                if all(key in trade for key in ['price', 'size', 'side', 'time', 'sequence']):
                    volume = float(trade['price']) * float(trade['size'])
                    if volume >= min_volume:  # фильтруем малые объемы
                        significant_trades.append({
                            'symbol': symbol,
                            'trade_id': trade['sequence'],
                            'price': trade['price'],
                            'quantity': trade['size'],
                            'volume': volume,
                            'side': trade['side'],
                            'time': int(trade['time']) // 1000000,  # наносекунды -> миллисекунды
                            'is_significant': volume >= min_volume * 10  # помечаем особо крупные сделки
                        })
            
            return significant_trades
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении сделок {symbol}: {e}")
            self.logger.debug(f"Последняя ошибка для {symbol}: {str(e)}")
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