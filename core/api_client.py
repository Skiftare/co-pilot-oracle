import ccxt
import pandas as pd
from datetime import datetime, date, timedelta
import time
from PyQt5.QtCore import QObject, pyqtSignal
import os
import json
import hashlib


class ApiClient(QObject):
    # Сигналы для уведомления о событиях
    rate_limit_hit = pyqtSignal(str, int)  # (exchange, reset_time)
    request_complete = pyqtSignal(int, object, str)  # (task_id, data, error)

    def __init__(self):
        super().__init__()
        # Создаем только экземпляр KuCoin
        self.exchange = self.create_exchange()
        self.rate_limits = {}  # Отслеживание ограничений по запросам
        
        # Инициализация кэша
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".kucoin_viewer", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"Cache directory: {self.cache_dir}")
        
        # Словарь с базовыми настройками timeframes
        self.timeframe_configs = {
            '1m': {'limit': 1000, 'days_back': 1},
            '5m': {'limit': 1000, 'days_back': 5},
            '15m': {'limit': 1000, 'days_back': 10},
            '30m': {'limit': 1000, 'days_back': 15},
            '1h': {'limit': 1000, 'days_back': 30},
            '4h': {'limit': 1000, 'days_back': 60},
            '1d': {'limit': 500, 'days_back': 365},
            '1w': {'limit': 200, 'days_back': 730}
        }

    def create_exchange(self):
        """Создает экземпляр биржи KuCoin"""
        return ccxt.kucoin({
            'enableRateLimit': True,  # Автоматическая задержка для соблюдения лимитов API
            'timeout': 30000,  # Увеличенный таймаут для надежности
        })

    def fetch_ohlcv(self, task_id, symbol, timeframe, since, limit=None, append_mode=False):
        """
        Получает OHLCV данные для KuCoin с обработкой rate limits и кэшированием
        
        Parameters:
        - task_id: ID задачи
        - symbol: Торговая пара (например, 'BTC/USDT')
        - timeframe: Временной интервал ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
        - since: Начальная дата/время для данных
        - limit: Максимальное количество свечей (если None, используется значение из конфигурации)
        - append_mode: Если True, данные предназначены для добавления к существующим
        """
        print(f"Запрос OHLCV для {symbol} с таймфреймом {timeframe} с {since}, limit={limit}, append_mode={append_mode}")
        
        try:
            # Используем стандартные настройки для timeframe, если limit не указан
            if limit is None:
                if timeframe in self.timeframe_configs:
                    limit = self.timeframe_configs[timeframe]['limit']
                else:
                    limit = 500  # Значение по умолчанию, если таймфрейм не в конфигурации
            
            # Преобразуем дату в timestamp
            if isinstance(since, datetime):
                since_datetime = since
                since_timestamp = int(since.timestamp() * 1000)
            elif isinstance(since, date):
                since_datetime = datetime.combine(since, datetime.min.time())
                since_timestamp = int(since_datetime.timestamp() * 1000)
            else:
                since_timestamp = int(since * 1000)
                since_datetime = datetime.fromtimestamp(since)

            # Формируем ключ кэша с учетом лимита
            cache_key = f"{symbol}_{timeframe}_{since_datetime.strftime('%Y-%m-%d')}_{limit}"
            
            # Проверяем кэш перед запросом, только если не в режиме добавления
            cached_data = None
            if not append_mode:
                cached_data = self.get_cached_data(cache_key)
            
            if cached_data is not None:
                print(f"Использованы кэшированные данные для {symbol}")
                self.request_complete.emit(task_id, cached_data, "")
                return cached_data

            # Попытка получить данные
            try:
                print(f"Отправляем запрос на KuCoin для {symbol} с таймфреймом {timeframe} с {since}, limit={limit}")
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_timestamp, limit=limit)

                # Если данных нет или очень мало, попробуем более новые данные
                if len(ohlcv) < 5:
                    print(f"Получено слишком мало данных ({len(ohlcv)}), пробуем более новую дату")
                    # Пробуем запрос за более свежий период, сдвигаемся вперед на половину от запрошенного периода
                    time_shift = self._get_time_shift_for_timeframe(timeframe)
                    new_since = since_timestamp + time_shift
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=new_since, limit=limit)
                    
                # Если все еще мало данных, последний шанс - запросить последние свечи
                if len(ohlcv) < 5:
                    print(f"Все еще мало данных ({len(ohlcv)}), запрашиваем последние свечи")
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

                # Преобразуем в DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                print(f"Получены данные для {symbol}: {len(df)} записей")
                print(f"Диапазон дат: с {df['timestamp'].min()} по {df['timestamp'].max()}")
                
                # Сохраняем в кэш, только если это не режим добавления
                if not append_mode:
                    self.save_to_cache(cache_key, df)
                
                # Помечаем данные как предназначенные для добавления, если это режим добавления
                if append_mode:
                    df.attrs['append_mode'] = True
                
                # Сигнал об успешном завершении
                self.request_complete.emit(task_id, df, "")
                return df

            except ccxt.RateLimitExceeded as e:
                print(f"Rate limit exceeded for {symbol}: {e}")
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
            print(f"Error fetching OHLCV data for {symbol}: {e}")
            # Любые другие ошибки
            self.request_complete.emit(task_id, None, str(e))
            return None

    def _get_time_shift_for_timeframe(self, timeframe):
        """Вычисляет временной сдвиг в миллисекундах для timeframe"""
        if timeframe == '1m':
            return 60 * 1000 * 500  # 500 минут
        elif timeframe == '5m':
            return 5 * 60 * 1000 * 500  # 2500 минут
        elif timeframe == '15m':
            return 15 * 60 * 1000 * 500  # 7500 минут
        elif timeframe == '30m':
            return 30 * 60 * 1000 * 500  # 15000 минут
        elif timeframe == '1h':
            return 60 * 60 * 1000 * 500  # 500 часов
        elif timeframe == '4h':
            return 4 * 60 * 60 * 1000 * 300  # 1200 часов
        elif timeframe == '1d':
            return 24 * 60 * 60 * 1000 * 200  # 200 дней
        elif timeframe == '1w':
            return 7 * 24 * 60 * 60 * 1000 * 100  # 100 недель
        else:
            return 24 * 60 * 60 * 1000 * 7  # 7 дней по умолчанию

    def get_cached_data(self, cache_key):
        """Получает данные из кэша по ключу"""
        try:
            # Создаем хэш ключа для имени файла
            hashed_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"{hashed_key}.json")
            
            # Проверяем существование файла
            if not os.path.exists(cache_file):
                return None
                
            # Проверяем возраст кэша (24 часа)
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age > 86400:  # 24 часа в секундах
                print(f"Cache expired for {cache_key}")
                return None
                
            # Загружаем данные из файла
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Преобразуем в DataFrame
            df = pd.DataFrame(cache_data['data'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"Loaded from cache: {cache_key}")
            return df
            
        except Exception as e:
            print(f"Error reading from cache: {e}")
            # При ошибке чтения кэша возвращаем None
            return None

    def save_to_cache(self, cache_key, data):
        """Сохраняет данные в кэш"""
        try:
            # Создаем хэш ключа для имени файла
            hashed_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"{hashed_key}.json")
            
            # Подготовка данных для сохранения
            # Преобразуем timestamp в строки ISO для корректной сериализации
            data_copy = data.copy()
            data_copy['timestamp'] = data_copy['timestamp'].astype(str)
            
            cache_data = {
                "key": cache_key,
                "timestamp": datetime.now().isoformat(),
                "data": data_copy.to_dict(orient='records')
            }
            
            # Сохранение в файл
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
            print(f"Saved to cache: {cache_key}")
            
        except Exception as e:
            print(f"Error saving to cache: {e}")

    def clear_cache(self):
        """Очищает весь кэш или старые записи"""
        try:
            count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    # Проверяем возраст файла
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age > 86400:  # Старше 24 часов
                        os.remove(file_path)
                        count += 1
            print(f"Cleared {count} old cache entries")
            return count
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return 0

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