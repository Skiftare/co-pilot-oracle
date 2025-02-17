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

    async def get_kline_data(self, symbol: str, kline_type: str = '1min', size: int = 60) -> List:
        """
        Получает исторические данные свечей
        
        Args:
            symbol: Торговая пара (например, 'BTC-USDT')
            kline_type: Интервал свечей ('1min', '3min', '5min', '15min', '30min', '1hour', '2hour', '4hour', '6hour', '8hour', '12hour', '1day', '1week')
            size: Количество свечей (максимум 1500)
        
        Returns:
            List of klines [timestamp, open, close, high, low, volume, turnover]
        """
        try:
            self.logger.debug(f"Запрашиваем kline данные для {symbol}, тип: {kline_type}, размер: {size}")
            
            # Исправляем вызов API метода на правильное название
            klines = self.client.get_klines(symbol, kline_type)
            
            if not klines:
                self.logger.warning(f"Нет данных для {symbol}")
                return []
                
            # Берем только нужное количество свечей
            klines = klines[:size]
                
            # Преобразуем строковые значения в числовые
            processed_klines = []
            for kline in klines:
                try:
                    processed_kline = [
                        int(kline[0]),      # timestamp
                        float(kline[1]),    # open
                        float(kline[2]),    # close
                        float(kline[3]),    # high
                        float(kline[4]),    # low
                        float(kline[5]),    # volume
                        float(kline[6])     # turnover
                    ]
                    processed_klines.append(processed_kline)
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Ошибка обработки свечи: {e}, данные: {kline}")
                    continue
            
            self.logger.debug(f"Получено и обработано {len(processed_klines)} свечей")
            return processed_klines
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении kline данных для {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получает данные тикера"""
        try:
            self.logger.debug(f"Запрашиваем тикер для {symbol}")
            # KuCoin API возвращает данные в формате {'ticker': {...}}
            response = self.client.get_ticker(symbol)
            self.logger.debug(f"Получен ответ от API: {response}")
            
            if not response:
                self.logger.warning(f"Пустой ответ от API для {symbol}")
                return None

            # Преобразуем данные в нужный формат
            ticker_data = {
                'symbol': symbol,
                'price': response.get('price', '0'),
                'volume': response.get('vol', '0'),  # в KuCoin используется 'vol' вместо 'volume'
                'time': response.get('time', str(int(datetime.now().timestamp() * 1000))),
                'best_bid': response.get('buy', '0'),  # в KuCoin 'buy' это best_bid
                'best_ask': response.get('sell', '0'),  # в KuCoin 'sell' это best_ask
                'best_bid_size': response.get('buySize', '0'),
                'best_ask_size': response.get('sellSize', '0')
            }

            # Сохраняем в кэш
            self._last_tickers[symbol] = ticker_data
            
            self.logger.debug(f"Обработанные данные тикера: {ticker_data}")
            return ticker_data

        except Exception as e:
            self.logger.error(f"Ошибка при получении тикера для {symbol}: {e}")
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
