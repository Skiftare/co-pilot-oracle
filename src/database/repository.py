import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from typing import List, Dict
import logging

class MarketRepository:
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # кэш для trading_pair_id
        
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
        
    async def ensure_trading_pair_exists(self, symbol: str) -> int:
        """Проверяет существование торговой пары и создает её при необходимости"""
        # Проверяем кэш
        if symbol in self._cache:
            return self._cache[symbol]
            
        query_select = "SELECT id FROM trading_pairs WHERE symbol = %s"
        query_insert = """
            INSERT INTO trading_pairs (symbol, base_currency, quote_currency)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        
        currencies = symbol.split('-')
        if len(currencies) != 2:
            self.logger.error(f"Неверный формат символа: {symbol}")
            return None
            
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Сначала пробуем найти существующую пару
                cur.execute(query_select, (symbol,))
                result = cur.fetchone()
                
                if result:
                    self._cache[symbol] = result[0]
                    return result[0]
                    
                # Если не нашли, создаем новую
                cur.execute(query_insert, (symbol, currencies[0], currencies[1]))
                new_id = cur.fetchone()[0]
                self._cache[symbol] = new_id
                return new_id

    async def save_ticker(self, ticker_data: Dict):
        """Сохраняет данные тикера"""
        try:
            pair_id = await self.ensure_trading_pair_exists(ticker_data['symbol'])
            if not pair_id:
                return

            query = """
                INSERT INTO price_tickers (
                    time, trading_pair_id, price, volume, 
                    best_bid, best_ask, best_bid_size, best_ask_size,
                    sequence, price_change, volume_change
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        datetime.fromtimestamp(ticker_data['time'] / 1000),
                        pair_id,
                        float(ticker_data['price']),
                        float(ticker_data['volume']),
                        float(ticker_data['best_bid']),
                        float(ticker_data['best_ask']),
                        float(ticker_data['best_bid_size']),
                        float(ticker_data['best_ask_size']),
                        ticker_data['sequence'],
                        ticker_data.get('price_change', 0),
                        ticker_data.get('volume_change', 0)
                    ))
                    
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении тикера {ticker_data['symbol']}: {e}")

    async def save_trades(self, trades: List[Dict]):
        """Сохраняет значимые сделки пакетно"""
        if not trades:
            return
            
        try:
            symbol = trades[0]['symbol']
            pair_id = await self.ensure_trading_pair_exists(symbol)
            if not pair_id:
                return

            query = """
                INSERT INTO significant_trades (
                    time, trading_pair_id, trade_id, price,
                    quantity, volume, side, is_significant
                )
                VALUES %s
                ON CONFLICT (trade_id, trading_pair_id) DO NOTHING
            """
            
            # Подготавливаем данные для пакетной вставки
            values = [(
                datetime.fromtimestamp(trade['time'] / 1000),
                pair_id,
                trade['trade_id'],
                float(trade['price']),
                float(trade['quantity']),
                float(trade['volume']),
                trade['side'],
                trade.get('is_significant', False)
            ) for trade in trades]
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(cur, query, values)
                    
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении сделок для {symbol}: {e}")

    async def get_recent_prices(self, symbol: str, minutes: int) -> List[Dict]:
        """Получение цен за последние N минут"""
        query = """
            SELECT pt.price, pt.timestamp
            FROM price_tickers pt
            JOIN trading_pairs tp ON pt.trading_pair_id = tp.id
            WHERE tp.symbol = %s
            AND pt.timestamp > NOW() - INTERVAL '%s minutes'
            ORDER BY pt.timestamp ASC
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, minutes))
                return cur.fetchall()

    async def get_recent_price_volume(self, symbol: str, minutes: int) -> List[Dict]:
        """Получение цен и объемов за последние N минут"""
        query = """
            SELECT pt.price, pt.volume, pt.timestamp
            FROM price_tickers pt
            JOIN trading_pairs tp ON pt.trading_pair_id = tp.id
            WHERE tp.symbol = %s
            AND pt.timestamp > NOW() - INTERVAL '%s minutes'
            ORDER BY pt.timestamp ASC
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, minutes))
                return cur.fetchall()

    async def get_collection_states(self, symbols: List[str] = None) -> Dict:
        """Получает состояние сбора данных для указанных символов"""
        query = """
            SELECT 
                tp.symbol,
                cs.*
            FROM collection_state cs
            JOIN trading_pairs tp ON tp.id = cs.trading_pair_id
            WHERE tp.symbol = ANY(%s)
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (symbols,))
                    results = cur.fetchall()
                    
                    states = {}
                    for row in results:
                        states[row[0]] = {
                            'trading_pair_id': row[1],
                            'last_ticker_time': row[2],
                            'last_trade_time': row[3],
                            'last_sequence': row[4],
                            'errors_count': row[5],
                            'total_records_collected': row[6],
                            'last_price': row[7],
                            'last_volume': row[8],
                            'is_active': row[9],
                            'updated_at': row[10]
                        }
                    return states
                    
        except Exception as e:
            self.logger.error(f"Ошибка при получении состояний: {e}")
            return {}

    async def initialize_collection_state(self, symbol: str, ticker: Dict):
        """Инициализирует состояние сбора для новой пары"""
        pair_id = await self.ensure_trading_pair_exists(symbol)
        if not pair_id:
            return
            
        query = """
            INSERT INTO collection_state (
                trading_pair_id, last_ticker_time, last_sequence,
                last_price, last_volume, is_active
            )
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (trading_pair_id) DO UPDATE SET
                last_ticker_time = EXCLUDED.last_ticker_time,
                last_sequence = EXCLUDED.last_sequence,
                last_price = EXCLUDED.last_price,
                last_volume = EXCLUDED.last_volume,
                is_active = TRUE,
                updated_at = NOW()
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        pair_id,
                        datetime.fromtimestamp(int(ticker['time']) / 1000),
                        ticker['sequence'],
                        float(ticker['price']),
                        float(ticker['volume'])
                    ))
                    
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации состояния для {symbol}: {e}")

    async def update_collection_state(self, symbol: str, ticker: Dict):
        """Обновляет состояние сбора данных"""
        pair_id = await self.ensure_trading_pair_exists(symbol)
        if not pair_id:
            return
            
        query = """
            UPDATE collection_state
            SET 
                last_ticker_time = %s,
                last_sequence = %s,
                last_price = %s,
                last_volume = %s,
                total_records_collected = total_records_collected + 1,
                updated_at = NOW()
            WHERE trading_pair_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        datetime.fromtimestamp(int(ticker['time']) / 1000),
                        ticker['sequence'],
                        float(ticker['price']),
                        float(ticker['volume']),
                        pair_id
                    ))
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении состояния для {symbol}: {e}")

    async def increment_error_count(self, symbol: str):
        """Увеличивает счетчик ошибок для пары"""
        pair_id = await self.ensure_trading_pair_exists(symbol)
        if not pair_id:
            return
            
        query = """
            UPDATE collection_state
            SET 
                errors_count = errors_count + 1,
                updated_at = NOW()
            WHERE trading_pair_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (pair_id,))
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении счетчика ошибок для {symbol}: {e}") 