import asyncio
from datetime import datetime
from typing import List, Optional, Dict
import logging
from database.repository import MarketRepository
from exchange.kucoin_client import KuCoinMarketClient

class MarketDataCollector:
    def __init__(self, 
                 client: KuCoinMarketClient,
                 repository: MarketRepository,
                 collection_interval: int = 5):  # уменьшаем до 5 секунд
        self.client = client
        self.repository = repository
        self.collection_interval = collection_interval
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.stats = {
            'tickers_by_symbol': {},
            'trades_by_symbol': {},
            'errors_by_symbol': {}
        }
        
    async def start_collection(self, symbols: Optional[List[str]] = None):
        """Запускает сбор данных для указанных символов или всех доступных"""
        self.is_running = True
        cycle_count = 0
        
        while self.is_running:
            cycle_count += 1
            cycle_start = datetime.now()
            
            try:
                if symbols:
                    self.logger.info(f"\n=== Начало цикла сбора данных #{cycle_count} ===")
                    for symbol in symbols:
                        try:
                            # Сбор тикеров
                            ticker_data = await self.client.get_ticker(symbol)
                            if ticker_data:
                                await self.repository.save_ticker(ticker_data)
                                self.stats['tickers_by_symbol'][symbol] = self.stats['tickers_by_symbol'].get(symbol, 0) + 1
                                
                            # Сбор сделок
                            trades = await self.client.get_recent_trades(symbol)
                            if trades:
                                await self.repository.save_trades(trades)
                                self.stats['trades_by_symbol'][symbol] = self.stats['trades_by_symbol'].get(symbol, 0) + len(trades)
                                
                        except Exception as e:
                            self.logger.error(f"Ошибка при сборе данных для {symbol}: {e}")
                            self.stats['errors_by_symbol'][symbol] = self.stats['errors_by_symbol'].get(symbol, 0) + 1
                            continue
                            
                    cycle_duration = (datetime.now() - cycle_start).total_seconds()
                    
                    # Подробная статистика
                    self.logger.info(f"""
=== Статистика сбора данных (Цикл #{cycle_count}) ===
Длительность цикла: {cycle_duration:.2f} сек

Тикеры по символам:
{self._format_stats_dict(self.stats['tickers_by_symbol'])}

Сделки по символам:
{self._format_stats_dict(self.stats['trades_by_symbol'])}

Ошибки по символам:
{self._format_stats_dict(self.stats['errors_by_symbol'])}

Средняя скорость: {(cycle_duration/len(symbols)):.2f} сек/символ
Ожидание {self.collection_interval} секунд перед следующим циклом...
================================""")
                    
                    # Ожидание с индикацией
                    for i in range(self.collection_interval):
                        if not self.is_running:
                            break
                        self.logger.info(f"Ожидание... {self.collection_interval - i} сек")
                        await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Ошибка при сборе данных: {e}")
                await asyncio.sleep(5)
                
    def _format_stats_dict(self, stats_dict: Dict) -> str:
        """Форматирует словарь статистики для вывода"""
        if not stats_dict:
            return "Нет данных"
        return "\n".join([f"  {k}: {v}" for k, v in stats_dict.items()])
                
    def stop_collection(self):
        """Останавливает сбор данных"""
        self.is_running = False  