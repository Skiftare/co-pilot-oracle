import ccxt
import pandas as pd
from datetime import datetime
import time
from PyQt5.QtCore import QObject, pyqtSignal


class ApiClient(QObject):
    # Сигналы для уведомления о событиях
    rate_limit_hit = pyqtSignal(str, int)  # (exchange, reset_time)
    request_complete = pyqtSignal(int, object, str)  # (task_id, data, error)

    def __init__(self):
        super().__init__()
        # Создаем только экземпляр KuCoin
        self.exchange = self.create_exchange()
        self.rate_limits = {}  # Отслеживание ограничений по запросам

    def create_exchange(self):
        """Создает экземпляр биржи KuCoin"""
        return ccxt.kucoin({
            'enableRateLimit': True,  # Автоматическая задержка для соблюдения лимитов API
            'timeout': 30000,  # Увеличенный таймаут для надежности
        })

    def fetch_ohlcv(self, task_id, symbol, timeframe, since):
        """Получает OHLCV данные для KuCoin с обработкой rate limits"""
        try:
            # Преобразуем дату в timestamp
            if isinstance(since, datetime):
                since_timestamp = int(since.timestamp() * 1000)
            else:
                since_timestamp = int(since * 1000)

            # Попытка получить данные
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_timestamp)

                # Преобразуем в DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

                # Сигнал об успешном завершении
                self.request_complete.emit(task_id, df, "")
                return df

            except ccxt.RateLimitExceeded as e:
                # Обрабатываем ограничение запросов
                reset_time = self.extract_reset_time(e)
                self.rate_limits['kucoin'] = {
                    'limited': True,
                    'reset_time': reset_time,
                    'timestamp': time.time()
                }

                # Отправляем сигнал о достижении лимита
                self.rate_limit_hit.emit('kucoin', reset_time)

                # Возвращаем ошибку обработчику
                self.request_complete.emit(task_id, None, f"Rate limit exceeded: wait {reset_time} seconds")
                return None

        except Exception as e:
            # Любые другие ошибки
            self.request_complete.emit(task_id, None, str(e))
            return None

    def extract_reset_time(self, exception):
        """Извлекает время сброса ограничения из исключения KuCoin"""
        try:
            # Попробуем получить время сброса из сообщения об ошибке
            error_message = str(exception)

            # Для KuCoin часто указывается время в секундах
            import re
            numbers = re.findall(r'\d+', error_message)
            if numbers:
                # Предполагаем, что первое число - это время в секундах
                return int(numbers[0])

            # Если не удалось определить, используем стандартное значение
            return 60

        except:
            # В случае ошибки используем стандартное значение
            return 60

    def fetch_markets(self, task_id=None):
        """Получает информацию о всех доступных торговых парах на KuCoin"""
        try:
            markets = self.exchange.fetch_markets()

            # Преобразуем в более удобный формат
            df = pd.DataFrame([{
                'symbol': market['symbol'],
                'base': market['base'],
                'quote': market['quote'],
                'active': market['active'],
                'precision': market['precision']['price'],
                'minAmount': market.get('limits', {}).get('amount', {}).get('min', 0)
            } for market in markets])

            # Фильтруем только активные пары
            df = df[df['active'] == True]

            if task_id is not None:
                self.request_complete.emit(task_id, df, "")

            return df

        except Exception as e:
            if task_id is not None:
                self.request_complete.emit(task_id, None, str(e))
            return None

    def fetch_ticker(self, task_id, symbol):
        """Получает текущий тикер для указанной пары"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)

            # Преобразуем в DataFrame для единообразия
            df = pd.DataFrame([{
                'symbol': ticker['symbol'],
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['volume'],
                'change': ticker['percentage'],
                'timestamp': pd.to_datetime(ticker['timestamp'], unit='ms')
            }])

            self.request_complete.emit(task_id, df, "")
            return df

        except Exception as e:
            self.request_complete.emit(task_id, None, str(e))
            return None

    def fetch_trending_coins(self, task_id, timeframe='1h', limit=20):
        """Находит монеты с наибольшим ростом за указанный период"""
        try:
            # Получаем все доступные пары с USDT
            markets_df = self.fetch_markets()
            usdt_markets = markets_df[markets_df['quote'] == 'USDT']

            # Берем выборку пар (ограничиваем для скорости)
            sample_size = min(100, len(usdt_markets))
            sampled_markets = usdt_markets.sample(n=sample_size)

            results = []

            # Для каждой пары получаем данные за период
            for symbol in sampled_markets['symbol']:
                try:
                    # Получаем OHLCV данные
                    since = int((datetime.now().timestamp() - 3600 * 24) * 1000)  # За последние 24 часа
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)

                    if len(ohlcv) > 0:
                        first_price = ohlcv[0][4]  # Цена закрытия первой свечи
                        last_price = ohlcv[-1][4]  # Цена закрытия последней свечи

                        # Вычисляем изменение в процентах
                        if first_price > 0:
                            percent_change = (last_price - first_price) / first_price * 100
                            volume_usd = ohlcv[-1][5] * last_price

                            results.append({
                                'symbol': symbol,
                                'price': last_price,
                                'change': percent_change,
                                'volume': ohlcv[-1][5],
                                'volume_usd': volume_usd
                            })
                except Exception:
                    # Пропускаем пары с ошибками
                    continue

            # Преобразуем в DataFrame и сортируем по изменению цены
            if results:
                trends_df = pd.DataFrame(results)

                # Фильтруем по минимальному объему для отсечения низколиквидных монет
                min_volume_usd = 10000  # Минимальный объем в USDT
                trends_df = trends_df[trends_df['volume_usd'] > min_volume_usd]

                # Сортируем по изменению цены (по убыванию)
                trends_df = trends_df.sort_values('change', ascending=False)

                # Ограничиваем количество результатов
                trends_df = trends_df.head(limit)

                self.request_complete.emit(task_id, trends_df, "")
                return trends_df
            else:
                self.request_complete.emit(task_id, None, "No data available")
                return None

        except Exception as e:
            self.request_complete.emit(task_id, None, str(e))
            return None

    def is_rate_limited(self, exchange="kucoin"):
        """Проверяет, действует ли ограничение запросов"""
        if exchange not in self.rate_limits:
            return False

        limit_info = self.rate_limits[exchange]

        if not limit_info['limited']:
            return False

        # Проверяем, не истекло ли время ограничения
        elapsed = time.time() - limit_info['timestamp']
        remaining = limit_info['reset_time'] - elapsed

        if remaining <= 0:
            # Ограничение истекло, обновляем статус
            self.rate_limits[exchange]['limited'] = False
            return False

        return True

    def get_reset_time(self, exchange="kucoin"):
        """Возвращает оставшееся время до сброса ограничения"""
        if not self.is_rate_limited(exchange):
            return 0

        limit_info = self.rate_limits[exchange]
        elapsed = time.time() - limit_info['timestamp']
        remaining = max(0, limit_info['reset_time'] - elapsed)

        return int(remaining)