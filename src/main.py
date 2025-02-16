import asyncio
from exchange.kucoin_client import KuCoinMarketClient
from collectors.market_collector import MarketDataCollector
from database.repository import MarketRepository

async def main():
    # Инициализация компонентов
    client = KuCoinMarketClient()
    repository = MarketRepository({
        'dbname': 'postgres',
        'user': 'postgres',
        'password': 'postgres',
        'host': 'localhost',
        'port': '5432'
    })
    
    collector = MarketDataCollector(
        client=client,
        repository=repository,
        collection_interval=30  # сбор данных каждые 30 секунд
    )
    
    # Режим фокуса на конкретных парах
    focus_symbols = ['BTC-USDT', 'ETH-USDT']
    await collector.start_collection(symbols=focus_symbols)
    
    # Или режим поиска аномалий
    # await collector.start_collection()

if __name__ == "__main__":
    asyncio.run(main()) 