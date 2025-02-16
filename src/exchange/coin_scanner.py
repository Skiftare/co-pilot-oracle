from typing import List, Dict
import logging

class CoinScanner:
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
    async def find_shitcoins(self) -> List[str]:
        """Поиск потенциальных шиткоинов на основе характеристик"""
        try:
            # Получаем все тикеры
            response = await self.client.get_all_tickers()
            
            # В KuCoin API тикеры находятся в поле 'ticker'
            all_tickers = response.get('ticker', [])
            potential_shitcoins = []
            
            for ticker in all_tickers:
                try:
                    symbol = ticker.get('symbol', '')
                    last_price = float(ticker.get('last', '0'))
                    vol_value = float(ticker.get('volValue', '0'))  # объем в базовой валюте
                    

                    if (symbol.endswith('USDT') and 
                        last_price < 0.01 and  # цена меньше цента
                        vol_value < 100000):   # объем меньше 100k USDT
                        
                        potential_shitcoins.append(symbol)
                        self.logger.info(f"Найден потенциальный шиткоин: {symbol} "
                                       f"(цена: {last_price}, объем: {vol_value})")
                
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Ошибка при обработке тикера: {e}")
                    continue
            
            return potential_shitcoins
            
        except Exception as e:
            self.logger.error(f"Ошибка при сканировании монет: {e}")
            return []

    async def get_new_listings(self) -> List[str]:
        """Получение списка новых листингов"""
        try:
            # KuCoin API предоставляет эндпоинт для новых листингов
            new_coins = await self.client.get_new_listing_coins()
            return [coin['symbol'] for coin in new_coins if 'symbol' in coin]
        except Exception as e:
            self.logger.error(f"Ошибка при получении новых листингов: {e}")
            return [] 