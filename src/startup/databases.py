import psycopg2
from psycopg2 import sql

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

def connect():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def create_tables():
    commands = [
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
            id SERIAL PRIMARY KEY,
            trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
            price NUMERIC NOT NULL,
            volume NUMERIC NOT NULL,
            timestamp TIMESTAMP DEFAULT NOW(),
            best_bid NUMERIC NOT NULL,
            best_ask NUMERIC NOT NULL,
            sequence VARCHAR(50),
            best_bid_size NUMERIC,
            best_ask_size NUMERIC
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS trade_history (
            id SERIAL PRIMARY KEY,
            trading_pair_id INTEGER REFERENCES trading_pairs(id) ON DELETE CASCADE,
            trade_id VARCHAR(100) UNIQUE NOT NULL,
            price NUMERIC NOT NULL,
            quantity NUMERIC NOT NULL,
            side VARCHAR(10) CHECK (side IN ('buy', 'sell')),
            timestamp TIMESTAMP DEFAULT NOW()
        )
        """
    ]
    
    conn = None
    try:
        conn = connect()
        cur = conn.cursor()
        
        # Сначала удаляем существующие таблицы
        cur.execute("""
            DROP TABLE IF EXISTS price_tickers CASCADE;
            DROP TABLE IF EXISTS trade_history CASCADE;
            DROP TABLE IF EXISTS trading_pairs CASCADE;
        """)
        
        # Создаем таблицы заново
        for command in commands:
            cur.execute(command)
            
        cur.close()
        conn.commit()
        print("Database tables created successfully.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
    finally:
        if conn:
            conn.close()

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
    ensure_database_exists()
    create_tables()

if __name__ == "__main__":
    main() 