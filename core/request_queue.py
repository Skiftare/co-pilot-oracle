import queue
import threading
import time
import uuid
from PyQt5.QtCore import QObject, pyqtSignal


class RequestQueue(QObject):
    progress_updated = pyqtSignal(int, int, int)  # (task_id, progress, total)
    queue_status_changed = pyqtSignal(dict)  # статус очереди

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.task_queue = queue.PriorityQueue()
        self.active_tasks = {}
        self.completed_tasks = []
        self.is_running = True
        self.paused = False
        self.last_task_id = 0

        # Запускаем обработчик очереди в отдельном потоке
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        # Подключаем сигналы от API клиента
        self.api_client.request_complete.connect(self._on_request_complete)
        self.api_client.rate_limit_hit.connect(self._on_rate_limit_hit)

    def add_request(self, task_type, symbol=None, timeframe=None, since=None,
                    callback=None, priority=1, limit=None, exchange="kucoin"):
        """Добавляет запрос в очередь"""
        self.last_task_id += 1
        task_id = self.last_task_id

        task = {
            'id': task_id,
            'task_type': task_type,
            'symbol': symbol,
            'timeframe': timeframe,
            'since': since,
            'limit': limit,
            'callback': callback,
            'priority': priority,
            'status': 'queued',
            'created_at': time.time(),
            'exchange': exchange  # Добавляем поле exchange
        }
        print(f"Добавляем задачу {task_id} в очередь: {task}")

        # Добавляем в очередь с приоритетом (меньшее число = высший приоритет)
        self.task_queue.put((priority, task))

        # Сохраняем для отслеживания
        self.active_tasks[task_id] = task

        # Уведомляем об изменении очереди
        self._notify_queue_status()

        return task_id

    def _process_queue(self):
        """Основной цикл обработки очереди запросов"""
        while self.is_running:
            if self.paused:
                time.sleep(0.5)
                continue

            try:
                # Пытаемся получить задачу из очереди с таймаутом
                priority, task = self.task_queue.get(timeout=0.5)
                print(f"Обрабатываем задачу {task['id']} с приоритетом {priority}: {task}")

                # Проверяем ограничения по запросам
                if self.api_client.is_rate_limited():
                    # Если биржа в режиме ограничения, возвращаем задачу обратно в очередь
                    reset_time = self.api_client.get_reset_time()
                    task['status'] = 'rate_limited'
                    print(f"Задача {task['id']} возвращена в очередь из-за ограничения запросов. Время сброса: {reset_time}")
                    self.task_queue.put((priority, task))
                    self._notify_queue_status()
                    time.sleep(1)  # Небольшая задержка перед следующей попыткой
                    continue

                # Обновляем статус и запускаем запрос
                task['status'] = 'in_progress'
                self._notify_queue_status()
                print(f"Запускаем задачу {task['id']}... и task_type: {task['task_type']}")
                # Запускаем API запрос в отдельном потоке на основе типа задачи
                if task['task_type'] == 'fetch_ohlcv':
                    
                    task_thread = threading.Thread(
                        target=self.api_client.fetch_ohlcv,
                        args=(task['id'], task['symbol'], task['timeframe'], task['since'])
                    )
                elif task['task_type'] == 'fetch_trending_coins':
                    task_thread = threading.Thread(
                        target=self.api_client.fetch_trending_coins,
                        args=(task['id'], task['timeframe'], task.get('limit', 20))
                    )
                elif task['task_type'] == 'fetch_ticker':
                    task_thread = threading.Thread(
                        target=self.api_client.fetch_ticker,
                        args=(task['id'], task['symbol'])
                    )
                else:
                    # Неизвестный тип задачи
                    self._on_request_complete(task['id'], None, f"Unknown task type: {task['task_type']}")
                    continue

                task_thread.daemon = True
                task_thread.start()

            except queue.Empty:
                # Очередь пуста, ничего не делаем
                pass

            except Exception as e:
                # Обрабатываем любые другие ошибки
                print(f"Error processing queue: {e}")
                time.sleep(1)

    def _on_request_complete(self, task_id, data, error):
        """Обработчик завершения запроса"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]

            if error:
                task['status'] = 'error'
                task['error'] = error
            else:
                task['status'] = 'completed'
                task['completed_at'] = time.time()

                # Вызываем callback, если он задан
                if task['callback']:
                    try:
                        task['callback'](data, error)
                    except Exception as e:
                        print(f"Error in callback for task {task_id}: {e}")

            # Перемещаем задачу в завершенные
            self.completed_tasks.append(task)
            del self.active_tasks[task_id]

            # Уведомляем об изменении очереди
            self._notify_queue_status()

    def _on_rate_limit_hit(self, exchange, reset_time):
        """Обработчик достижения лимита запросов"""
        # Уведомляем об изменении очереди
        self._notify_queue_status()

    def _notify_queue_status(self):
        """Формирует и отправляет статус очереди"""
        active_tasks = list(self.active_tasks.values())

        # Сортируем задачи по приоритету
        tasks = sorted(active_tasks, key=lambda x: x['priority'])

        # Добавляем последние 10 завершенных задач
        tasks.extend(self.completed_tasks[-10:])

        # Собираем статистику
        queue_size = self.task_queue.qsize()
        processing = len([t for t in active_tasks if t['status'] == 'in_progress'])
        waiting = len([t for t in active_tasks if t['status'] == 'queued'])

        # Используем "kucoin" как биржу по умолчанию
        exchange = "kucoin"
        rate_limited = self.api_client.is_rate_limited(exchange)
        max_reset_time = self.api_client.get_reset_time(exchange) if rate_limited else 0

        # Вычисляем общий прогресс
        total = queue_size + len(active_tasks)
        done = len(self.completed_tasks)
        if total + done > 0:
            progress = int(done / (total + done) * 100)
        else:
            progress = 100

        stats = {
            'queue_size': queue_size,
            'processing': processing,
            'waiting': waiting,
            'rate_limited': rate_limited,
            'reset_time': max_reset_time,
            'progress': progress,
            'tasks': tasks,
            'paused': self.paused
        }

        # Отправляем сигнал
        self.queue_status_changed.emit(stats)

    def get_stats(self):
        """Возвращает текущую статистику очереди"""
        active_tasks = list(self.active_tasks.values())

        # Собираем статистику
        queue_size = self.task_queue.qsize()
        processing = len([t for t in active_tasks if t['status'] == 'in_progress'])
        waiting = len([t for t in active_tasks if t['status'] == 'queued'])
        rate_limited = self.api_client.is_rate_limited()
        max_reset_time = self.api_client.get_reset_time() if rate_limited else 0

        # Вычисляем общий прогресс
        total = queue_size + len(active_tasks)
        done = len(self.completed_tasks)
        if total + done > 0:
            progress = int(done / (total + done) * 100)
        else:
            progress = 100

        # Сортируем задачи по приоритету
        tasks = sorted(active_tasks, key=lambda x: x['priority'])

        # Добавляем последние 10 завершенных задач
        tasks.extend(self.completed_tasks[-10:])

        return {
            'queue_size': queue_size,
            'processing': processing,
            'waiting': waiting,
            'rate_limited': rate_limited,
            'reset_time': max_reset_time,
            'progress': progress,
            'tasks': tasks,
            'paused': self.paused
        }

    def pause(self):
        """Приостанавливает обработку очереди"""
        self.paused = True
        self._notify_queue_status()

    def resume(self):
        """Возобновляет обработку очереди"""
        self.paused = False
        self._notify_queue_status()

    def is_paused(self):
        """Возвращает статус паузы"""
        return self.paused

    def clear(self):
        """Очищает очередь"""
        # Создаем новую очередь
        self.task_queue = queue.PriorityQueue()

        # Отмечаем все активные задачи как отмененные
        for task_id in list(self.active_tasks.keys()):
            task = self.active_tasks[task_id]
            if task['status'] == 'queued':
                task['status'] = 'cancelled'
                self.completed_tasks.append(task)
                del self.active_tasks[task_id]

        self._notify_queue_status()

    def stop(self):
        """Останавливает обработку очереди"""
        self.is_running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(1.0)