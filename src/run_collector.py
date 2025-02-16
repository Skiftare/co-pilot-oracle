import asyncio
import logging
from dotenv import load_dotenv
import os
from exchange.kucoin_client import KuCoinMarketClient
from collectors.market_collector import MarketDataCollector
from database.repository import MarketRepository
from exchange.coin_scanner import CoinScanner

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Список основных монет для отслеживания
MAIN_COINS = [
    'BTC-USDT',
    'ETH-USDT',
    'TON-USDT',
    'TRUMP-USDT',
    'ATOM-USDT',
    'FIL-USDT',
    'DOGE-USDT',
    'FTM-USDT',
    'FUEL-USDT'
]

async def main():
    # Инициализируем компоненты
    client = KuCoinMarketClient()
    repository = MarketRepository({
        'dbname': os.getenv('DB_NAME', 'postgres'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    })
    
    # Создаем сканер для поиска шиткоинов
    scanner = CoinScanner(client)
    
    # Находим потенциальные шиткоины
    potential_coins = await scanner.find_shitcoins()
    logger.info(f"Найдено {len(potential_coins)} потенциальных шиткоинов")
    
    # Объединяем основные монеты и шиткоины
    all_coins = MAIN_COINS + potential_coins
    unique_coins = list(dict.fromkeys(all_coins))  # удаляем дубликаты, если есть
    
    logger.info(f"""
=== Начинаем сбор данных ===
Всего монет: {len(unique_coins)}
Основные монеты: {MAIN_COINS}
Первые 5 шиткоинов: {potential_coins[:5]}
=========================""")
    
    # Создаем коллектор данных
    collector = MarketDataCollector(
        client=client,
        repository=repository,
        collection_interval=16  # 5 секунд между циклами
    )
    
    try:
        # Запускаем сбор данных для всех монет
        await collector.start_collection(symbols=unique_coins)
    except KeyboardInterrupt:
        logger.info("Останавливаем сбор данных...")
    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {e}")
    finally:
        collector.stop_collection()

if __name__ == "__main__":
    asyncio.run(main()) 