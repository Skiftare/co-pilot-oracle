import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from typing import List, Dict
import logging

class MarketRepository:
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
        
    async def ensure_trading_pair_exists(self, symbol: str) -> int:
        """Проверяет существование торговой пары и создает её при необходимости"""
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
                    return result[0]
                    
                # Если не нашли, создаем новую
                cur.execute(query_insert, (symbol, currencies[0], currencies[1]))
                new_id = cur.fetchone()[0]
                conn.commit()
                return new_id

    async def save_ticker(self, ticker_data: Dict):
        """Сохраняет данные тикера"""
        try:
            # Получаем или создаем trading_pair_id
            pair_id = await self.ensure_trading_pair_exists(ticker_data['symbol'])
            if not pair_id:
                self.logger.error(f"Не удалось получить/создать trading_pair_id для {ticker_data['symbol']}")
                return

            query = """
                INSERT INTO price_tickers (
                    trading_pair_id, price, volume, timestamp, 
                    best_bid, best_ask, best_bid_size, best_ask_size, sequence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        pair_id,
                        float(ticker_data['price']),
                        float(ticker_data['volume']),
                        datetime.fromtimestamp(ticker_data['timestamp'] / 1000),
                        float(ticker_data['best_bid']),
                        float(ticker_data['best_ask']),
                        float(ticker_data['best_bid_size']),
                        float(ticker_data['best_ask_size']),
                        ticker_data['sequence']
                    ))
                    self.logger.info(f"Сохранен тикер для {ticker_data['symbol']} (pair_id: {pair_id})")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении тикера {ticker_data['symbol']}: {e}")

    async def save_trades(self, trades: List[Dict]):
        """Сохраняет историю сделок"""
        query = """
            INSERT INTO trade_history (
                trading_pair_id, trade_id, price, quantity, side, timestamp
            )
            VALUES (
                (SELECT id FROM trading_pairs WHERE symbol = %s),
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (trade_id) DO NOTHING
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for trade in trades:
                    try:
                        cur.execute(query, (
                            trade['symbol'],
                            trade['trade_id'],
                            float(trade['price']),
                            float(trade['quantity']),
                            trade['side'],
                            datetime.fromtimestamp(trade['timestamp'] / 1000)  # конвертируем миллисекунды в datetime
                        ))
                    except Exception as e:
                        self.logger.error(f"Ошибка при сохранении сделки: {e}")
                        continue

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