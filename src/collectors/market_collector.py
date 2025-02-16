import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from exchange.kucoin_client import KuCoinMarketClient
from database.repository import MarketRepository

class MarketDataCollector:
    def __init__(self, 
                 client: KuCoinMarketClient,
                 repository: MarketRepository,
                 collection_interval: int = 60):  # увеличили интервал до 1 минуты
        self.client = client
        self.repository = repository
        self.collection_interval = collection_interval
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.stats = {
            'tickers_processed': 0,
            'tickers_saved': 0,
            'trades_processed': 0,
            'trades_saved': 0,
            'errors': 0,
            'start_time': None,
            'data_size': 0  # примерный размер собранных данных в байтах
        }
        
    async def start_collection(self, symbols: Optional[List[str]] = None):
        """Запускает сбор данных с учетом последнего состояния"""
        self.is_running = True
        
        self.logger.info("Получаем состояния коллекции...")
        # Получаем последнее состояние для всех пар
        states = await self.repository.get_collection_states(symbols)
        self.logger.info(f"Получено {len(states)} состояний")
        
        # Группируем символы по времени последнего обновления
        current_time = datetime.now()
        groups = {
            'new': [],      # новые пары
            'active': [],   # недавно обновленные
            'delayed': [],  # давно не обновлялись
            'inactive': []  # неактивные
        }
        
        self.logger.info("Группируем символы...")
        for symbol in symbols:
            state = states.get(symbol)
            if not state:
                groups['new'].append(symbol)
            elif state.get('last_ticker_time') and (current_time - state['last_ticker_time']).total_seconds() < 3600:
                groups['active'].append(symbol)
            elif state.get('is_active'):
                groups['delayed'].append(symbol)
            else:
                groups['inactive'].append(symbol)
                
        self.logger.info(f"""
Распределение символов:
- Новые: {len(groups['new'])}
- Активные: {len(groups['active'])}
- С задержкой: {len(groups['delayed'])}
- Неактивные: {len(groups['inactive'])}
""")
                
        # Обрабатываем группы с разными приоритетами
        self.logger.info("Обработка новых пар...")
        await self._process_new_pairs(groups['new'])
        
        self.logger.info("Обработка активных пар...")
        await self._process_active_pairs(groups['active'])
        
        self.logger.info("Обработка отложенных пар...")
        await self._process_delayed_pairs(groups['delayed'])
        
        self.logger.info("Запуск основного цикла сбора...")
        # Основной цикл сбора данных
        cycle_count = 0
        while self.is_running:
            cycle_start = datetime.now()
            cycle_count += 1
            
            self.logger.info(f"\n=== Начало цикла сбора данных #{cycle_count} ===")
            
            try:
                # Собираем данные для всех активных пар
                active_symbols = groups['active'] + groups['delayed']
                if active_symbols:
                    self.logger.info(f"Сбор данных для {len(active_symbols)} активных пар")
                    await self._collect_batch(active_symbols)
                    
                # Периодически проверяем новые пары
                if cycle_count % 60 == 0:  # каждый час
                    self.logger.info("Проверка неактивных пар...")
                    await self._process_new_pairs(groups['inactive'])
                    
            except Exception as e:
                self.logger.error(f"Ошибка в цикле сбора: {e}")
                
            finally:
                # Ждем до следующего цикла
                await self._wait_until_next_cycle(cycle_start)

    async def _process_new_pairs(self, symbols: List[str]):
        """Обработка новых пар"""
        for symbol in symbols:
            try:
                # Получаем базовую информацию
                ticker = await self.client.get_ticker(symbol)
                if ticker:
                    await self.repository.initialize_collection_state(symbol, ticker)
            except Exception as e:
                self.logger.error(f"Ошибка при обработке новой пары {symbol}: {e}")

    async def _process_active_pairs(self, symbols: List[str]):
        """Обработка активных пар"""
        if not symbols:
            return
        await self._collect_batch(symbols)

    async def _process_delayed_pairs(self, symbols: List[str]):
        """Обработка пар с задержкой обновления"""
        if not symbols:
            return
        self.logger.info(f"Обработка {len(symbols)} пар с задержкой")
        await self._collect_batch(symbols)

    async def _collect_batch(self, symbols: List[str], batch_size: int = 20):
        """Собирает данные для группы символов"""
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            tasks = [self._collect_symbol_data(symbol) for symbol in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _collect_symbol_data(self, symbol: str):
        """Собирает данные с учетом состояния"""
        try:
            # Получаем текущее состояние
            states = await self.repository.get_collection_states([symbol])
            state = states.get(symbol)
            
            # Собираем тикеры
            ticker_data = await self.client.get_ticker(symbol)
            if ticker_data:
                # Проверяем, что данные новее последних сохраненных
                if not state or not state.get('last_ticker_time') or \
                   int(ticker_data['time']) > int(state['last_ticker_time'].timestamp() * 1000):
                    await self.repository.save_ticker(ticker_data)
                    await self.repository.update_collection_state(symbol, ticker_data)
                    
            # Собираем сделки
            last_trade_time = state['last_trade_time'] if state else None
            trades = await self.client.get_recent_trades(symbol)
            if trades:
                await self.repository.save_trades(trades)
                
        except Exception as e:
            self.logger.error(f"Ошибка при сборе данных для {symbol}: {e}")
            await self.repository.increment_error_count(symbol)
            raise e

    async def _wait_until_next_cycle(self, cycle_start: datetime):
        """Ожидание до следующего цикла сбора"""
        elapsed = (datetime.now() - cycle_start).total_seconds()
        if elapsed < 60:  # интервал 1 минута
            await asyncio.sleep(60 - elapsed)

    def stop_collection(self):
        """Останавливает сбор данных"""
        self.is_running = False

    async def _update_metrics(self, symbol: str):
        """Обновляет метрики для монеты"""
        # Обновляем часовые метрики
        await self.repository.update_coin_metrics(symbol, interval='1 hour')
        
        # Проверяем на "взлет"
        metrics = await self.repository.get_recent_metrics(symbol)
        if self._detect_pump(metrics):
            await self.repository.record_pump(symbol, metrics)

    async def _log_statistics(self, cycle_count: int, cycle_start: datetime):
        """Выводит статистику сбора данных"""
        duration = (datetime.now() - cycle_start).total_seconds()
        total_duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        self.logger.info(f"""
=== Статистика сбора данных (Цикл #{cycle_count}) ===
Длительность цикла: {duration:.2f} сек
Общее время работы: {total_duration/3600:.1f} часов

Обработано тикеров: {self.stats['tickers_processed']}
Сохранено тикеров: {self.stats['tickers_saved']}
Обработано сделок: {self.stats['trades_processed']}
Сохранено сделок: {self.stats['trades_saved']}
Ошибок: {self.stats['errors']}

Собрано данных: {self.stats['data_size']/1024/1024:.2f} MB
Скорость сбора: {self.stats['data_size']/1024/1024/total_duration:.2f} MB/сек
================================""")

    def _detect_pump(self, metrics: Dict) -> bool:
        # Реализация метода для обнаружения "взлета"
        # Этот метод должен быть реализован в соответствии с конкретными требованиями
        # В данном примере он возвращает всегда True
        return True  