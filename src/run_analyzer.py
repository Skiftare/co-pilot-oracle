import asyncio
import logging
from dotenv import load_dotenv
import os
from exchange.kucoin_client import KuCoinMarketClient
from collectors.market_collector import MarketDataCollector
from database.repository import MarketRepository
from analysis.market_analyzer import MarketAnalyzer
from exchange.coin_scanner import CoinScanner

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Инициализируем компоненты
    client = KuCoinMarketClient()
    repository = MarketRepository({
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    })
    
    # Создаем сканер для поиска шиткоинов
    scanner = CoinScanner(client)
    
    # Находим потенциальные шиткоины
    potential_coins = await scanner.find_shitcoins()
    logger.info(f"Найдено {len(potential_coins)} потенциальных шиткоинов")
    
    # Создаем коллектор данных
    collector = MarketDataCollector(
        client=client,
        repository=repository,
        collection_interval=30
    )
    
    # Создаем анализатор
    analyzer = MarketAnalyzer(repository)
    
    # Запускаем сбор данных в фоновом режиме
    collection_task = asyncio.create_task(
        collector.start_collection(symbols=potential_coins[:5])  # начнем с 5 монет
    )
    
    # Основной цикл анализа
    try:
        while True:
            for symbol in potential_coins[:5]:
                # Проверяем возможности возврата к среднему
                mean_reversion = await analyzer.find_mean_reversion_opportunities(symbol)
                if mean_reversion:
                    logger.info(f"Найдена возможность возврата к среднему: {mean_reversion}")
                
                # Проверяем паттерны памп-и-дамп
                pump_dump = await analyzer.detect_pump_and_dump_pattern(symbol)
                if pump_dump:
                    logger.info(f"Обнаружен потенциальный памп: {pump_dump}")
                
            await asyncio.sleep(60)  # анализируем каждую минуту
            
    except KeyboardInterrupt:
        logger.info("Останавливаем работу...")
        collector.stop_collection()
        await collection_task

if __name__ == "__main__":
    asyncio.run(main()) 