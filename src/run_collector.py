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
    
    if not potential_coins:
        logger.error("Не найдено монет для анализа!")
        return
        
    logger.info(f"Начинаем сбор данных для монет: {potential_coins[:5]}")
    
    # Создаем коллектор данных с меньшим интервалом
    collector = MarketDataCollector(
        client=client,
        repository=repository,
        collection_interval=16  # 5 секунд между циклами
    )
    
    try:
        # Запускаем сбор данных
        await collector.start_collection(symbols=potential_coins[:5])
    except KeyboardInterrupt:
        logger.info("Останавливаем сбор данных...")
    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {e}")
    finally:
        collector.stop_collection()

if __name__ == "__main__":
    asyncio.run(main()) 