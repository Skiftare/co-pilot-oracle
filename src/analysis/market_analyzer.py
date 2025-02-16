import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from scipy import stats
from datetime import datetime, timedelta
import logging

class MarketAnalyzer:
    def __init__(self, repository, lookback_period: int = 30):
        """
        lookback_period: количество минут для анализа исторических данных
        """
        self.repository = repository
        self.lookback_period = lookback_period
        self.logger = logging.getLogger(__name__)

    async def find_mean_reversion_opportunities(self, symbol: str) -> Optional[Dict]:
        """Поиск возможностей по стратегии возврата к среднему"""
        try:
            # Получаем исторические данные
            data = await self.repository.get_recent_prices(
                symbol, 
                minutes=self.lookback_period
            )
            
            if len(data) < 10:  # минимальное количество точек для анализа
                return None
                
            df = pd.DataFrame(data)
            
            # Рассчитываем базовые статистики
            current_price = df['price'].iloc[-1]
            mean_price = df['price'].mean()
            std_dev = df['price'].std()
            
            # Z-score текущей цены
            z_score = (current_price - mean_price) / std_dev
            
            # Если цена значительно отклонилась от среднего (>2 std)
            if abs(z_score) > 2:
                return {
                    'symbol': symbol,
                    'signal': 'buy' if z_score < 0 else 'sell',
                    'confidence': min(abs(z_score) / 4, 1),  # нормализуем уверенность
                    'current_price': current_price,
                    'mean_price': mean_price,
                    'deviation': z_score
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе {symbol}: {e}")
            return None

    async def detect_pump_and_dump_pattern(self, symbol: str) -> Optional[Dict]:
        """Определение паттерна памп-и-дамп"""
        try:
            # Получаем данные о ценах и объемах
            data = await self.repository.get_recent_price_volume(
                symbol, 
                minutes=self.lookback_period
            )
            
            df = pd.DataFrame(data)
            
            # Рассчитываем изменение цены и объема
            price_change = df['price'].pct_change()
            volume_change = df['volume'].pct_change()
            
            # Признаки пампа:
            # 1. Резкий рост цены
            # 2. Резкий рост объема
            # 3. Высокая волатильность
            
            recent_price_change = price_change.tail(5).mean()
            recent_volume_change = volume_change.tail(5).mean()
            recent_volatility = price_change.tail(5).std()
            
            if (recent_price_change > 0.05 and  # >5% рост цены
                recent_volume_change > 0.5 and  # >50% рост объема
                recent_volatility > 0.02):      # высокая волатильность
                
                return {
                    'symbol': symbol,
                    'pattern': 'potential_pump',
                    'price_change': recent_price_change,
                    'volume_change': recent_volume_change,
                    'volatility': recent_volatility,
                    'confidence': min(
                        (recent_price_change * 10 + 
                         recent_volume_change + 
                         recent_volatility * 20) / 3, 
                        1
                    )
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе памп-паттерна {symbol}: {e}")
            return None

    async def find_correlated_pairs(self, base_symbol: str) -> List[Dict]:
        """Поиск коррелирующих пар"""
        try:
            # Получаем все активные пары
            all_symbols = await self.repository.get_active_trading_pairs()
            correlations = []
            
            base_data = await self.repository.get_recent_prices(
                base_symbol, 
                minutes=self.lookback_period
            )
            base_df = pd.DataFrame(base_data)
            
            for symbol in all_symbols:
                if symbol == base_symbol:
                    continue
                    
                pair_data = await self.repository.get_recent_prices(
                    symbol, 
                    minutes=self.lookback_period
                )
                pair_df = pd.DataFrame(pair_data)
                
                # Рассчитываем корреляцию
                if len(base_df) == len(pair_df) and len(base_df) > 5:
                    correlation = base_df['price'].corr(pair_df['price'])
                    if abs(correlation) > 0.7:  # сильная корреляция
                        correlations.append({
                            'base_symbol': base_symbol,
                            'correlated_symbol': symbol,
                            'correlation': correlation
                        })
            
            return correlations
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске корреляций: {e}")
            return [] 