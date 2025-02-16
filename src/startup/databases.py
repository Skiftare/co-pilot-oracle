import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

def connect():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def create_tables(use_timescale: bool = False):
    """Создает таблицы с или без TimescaleDB"""
    commands = []
    
    if use_timescale:
        commands.append("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    
    commands.extend([
        """
        CREATE TABLE IF NOT EXISTS trading_pairs (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(50) UNIQUE NOT NULL,
            base_currency VARCHAR(20) NOT NULL,
            quote_currency VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS price_tickers (
            time TIMESTAMPTZ NOT NULL,
            trading_pair_id INTEGER NOT NULL,
            price NUMERIC NOT NULL,
            volume NUMERIC NOT NULL,
            best_bid NUMERIC NOT NULL,
            best_ask NUMERIC NOT NULL,
            best_bid_size NUMERIC,
            best_ask_size NUMERIC,
            sequence VARCHAR(50),
            price_change NUMERIC,
            volume_change NUMERIC
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS significant_trades (
            time TIMESTAMPTZ NOT NULL,
            trading_pair_id INTEGER NOT NULL,
            trade_id VARCHAR(100) NOT NULL,
            price NUMERIC NOT NULL,
            quantity NUMERIC NOT NULL,
            volume NUMERIC NOT NULL,
            side VARCHAR(10),
            is_significant BOOLEAN DEFAULT FALSE
        )
        """,
        
        """
        CREATE TABLE collection_state (
            trading_pair_id INTEGER PRIMARY KEY,
            last_ticker_time TIMESTAMPTZ,
            last_trade_time TIMESTAMPTZ,
            last_sequence VARCHAR(50),
            errors_count INTEGER DEFAULT 0,
            total_records_collected BIGINT DEFAULT 0,
            last_price NUMERIC,
            last_volume NUMERIC,
            is_active BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE coin_metrics (
            id SERIAL PRIMARY KEY,
            trading_pair_id INTEGER NOT NULL,
            time_window INTERVAL NOT NULL,  -- например '1 hour', '1 day'
            time TIMESTAMPTZ NOT NULL,
            price_high NUMERIC,
            price_low NUMERIC,
            price_open NUMERIC,
            price_close NUMERIC,
            volume_total NUMERIC,
            trades_count INTEGER,
            significant_trades_count INTEGER,
            price_volatility NUMERIC,       -- стандартное отклонение цены
            volume_volatility NUMERIC,      -- стандартное отклонение объема
            largest_trade_volume NUMERIC,
            buy_volume_ratio NUMERIC,       -- соотношение объемов покупок/продаж
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE coin_pumps (
            id SERIAL PRIMARY KEY,
            trading_pair_id INTEGER NOT NULL,
            start_time TIMESTAMPTZ NOT NULL,
            end_time TIMESTAMPTZ,
            start_price NUMERIC NOT NULL,
            peak_price NUMERIC,
            price_increase_percent NUMERIC,
            volume_increase_percent NUMERIC,
            duration INTERVAL,
            significant_trades_before INTEGER,
            significant_trades_during INTEGER,
            pattern_type VARCHAR(50),       -- например 'pump_and_dump', 'organic_growth'
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    ])
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tickers_time_pair ON price_tickers (time DESC, trading_pair_id);",
        "CREATE INDEX IF NOT EXISTS idx_trades_time_pair ON significant_trades (time DESC, trading_pair_id);",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_id ON significant_trades (trade_id, trading_pair_id);"
    ]
    
    with psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, 
        password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    ) as conn:
        
        conn.autocommit = True
        cur = conn.cursor()
        
        # Удаляем старые таблицы
        cur.execute("""
            DROP TABLE IF EXISTS price_tickers CASCADE;
            DROP TABLE IF EXISTS significant_trades CASCADE;
            DROP TABLE IF EXISTS trading_pairs CASCADE;
            DROP TABLE IF EXISTS collection_state CASCADE;
            DROP TABLE IF EXISTS coin_metrics CASCADE;
            DROP TABLE IF EXISTS coin_pumps CASCADE;
        """)
        
        # Создаем новые таблицы
        for command in commands:
            cur.execute(command)
            
        # Создаем индексы
        for index in indexes:
            cur.execute(index)
            
        if use_timescale:
            # Создаем гипертаблицы
            cur.execute("SELECT create_hypertable('price_tickers', 'time', if_not_exists => TRUE);")
            cur.execute("SELECT create_hypertable('significant_trades', 'time', if_not_exists => TRUE);")
            
            # Настраиваем сжатие
            cur.execute("""
                ALTER TABLE price_tickers SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'trading_pair_id'
                );
            """)
            cur.execute("""
                ALTER TABLE significant_trades SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'trading_pair_id'
                );
            """)
            
        logger.info(f"База данных успешно инициализирована {'с' if use_timescale else 'без'} TimescaleDB")

def ensure_database_exists():
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(DB_NAME)))
        print("Database created successfully.")
    cur.close()
    conn.close()

def main():
    try:
        create_tables(use_timescale=False)  # используем обычный PostgreSQL
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")

if __name__ == "__main__":
    main() 