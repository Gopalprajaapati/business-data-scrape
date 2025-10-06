# app/optimization/__init__.py
import functools
import time
from functools import lru_cache
from threading import Lock
import redis
from flask import current_app


class CacheManager:
    def __init__(self):
        self.redis_client = None
        self.local_cache = {}
        self.cache_lock = Lock()
        self.setup_redis()

    def setup_redis(self):
        """Setup Redis connection for distributed caching"""
        try:
            self.redis_client = redis.Redis.from_url(
                current_app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
                decode_responses=True
            )
            self.redis_client.ping()  # Test connection
        except Exception as e:
            current_app.logger.warning(f"Redis not available: {e}. Using local cache only.")
            self.redis_client = None

    def get(self, key):
        """Get value from cache"""
        # Try local cache first
        with self.cache_lock:
            if key in self.local_cache:
                value, expiry = self.local_cache[key]
                if expiry is None or time.time() < expiry:
                    return value
                else:
                    del self.local_cache[key]

        # Try Redis
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    # Also store in local cache for faster access
                    with self.cache_lock:
                        self.local_cache[key] = (value, time.time() + 300)  # 5 minutes
                    return value
            except Exception as e:
                current_app.logger.warning(f"Redis get failed: {e}")

        return None

    def set(self, key, value, expire_seconds=3600):
        """Set value in cache"""
        expiry = time.time() + expire_seconds if expire_seconds else None

        # Store in local cache
        with self.cache_lock:
            self.local_cache[key] = (value, expiry)

        # Store in Redis if available
        if self.redis_client:
            try:
                if expire_seconds:
                    self.redis_client.setex(key, expire_seconds, value)
                else:
                    self.redis_client.set(key, value)
            except Exception as e:
                current_app.logger.warning(f"Redis set failed: {e}")

    def delete(self, key):
        """Delete value from cache"""
        with self.cache_lock:
            if key in self.local_cache:
                del self.local_cache[key]

        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                current_app.logger.warning(f"Redis delete failed: {e}")

    def clear(self):
        """Clear all cache"""
        with self.cache_lock:
            self.local_cache.clear()

        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                current_app.logger.warning(f"Redis clear failed: {e}")


class QueryOptimizer:
    def __init__(self, db):
        self.db = db
        self.cache_manager = CacheManager()

    def optimized_paginated_query(self, query, page, per_page, cache_key=None, cache_ttl=300):
        """Perform optimized paginated query with caching"""
        if cache_key:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result

        # Use window function for efficient pagination
        paginated_results = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        result = {
            'items': [item.to_dict() for item in paginated_results.items],
            'total': paginated_results.total,
            'pages': paginated_results.pages,
            'current_page': page
        }

        if cache_key:
            self.cache_manager.set(cache_key, result, cache_ttl)

        return result

    def batch_processing(self, model_class, batch_size=1000, condition=None):
        """Process large datasets in batches to avoid memory issues"""
        query = model_class.query
        if condition:
            query = query.filter(condition)

        total_processed = 0
        last_id = 0

        while True:
            batch = query.filter(model_class.id > last_id) \
                .order_by(model_class.id) \
                .limit(batch_size) \
                .all()

            if not batch:
                break

            for item in batch:
                yield item
                last_id = item.id

            total_processed += len(batch)
            current_app.logger.info(f"Processed {total_processed} records")

            # Clear session to prevent memory bloat
            self.db.session.expire_all()

    def create_optimized_indexes(self):
        """Create optimized database indexes"""
        indexes = [
            # Keyword indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_keywords_status_priority ON keywords(status, priority)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_keywords_created_status ON keywords(created_at, status)",

            # Search result indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_results_keyword_quality ON search_results(keyword_id, has_website, stars)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_results_website_status ON search_results(website, has_website)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_results_created_keyword ON search_results(created_at, keyword_id)",

            # Analysis indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_score_composite ON website_analyses(score, seo_score, performance_score)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_result_created ON website_analyses(result_id, created_at)",
        ]

        for index_sql in indexes:
            try:
                self.db.session.execute(index_sql)
                self.db.session.commit()
            except Exception as e:
                current_app.logger.warning(f"Failed to create index: {e}")
                self.db.session.rollback()


class MemoryOptimizer:
    def __init__(self):
        self.memory_threshold = 0.8  # 80% memory usage
        self.cleanup_interval = 300  # 5 minutes

    def should_cleanup_memory(self):
        """Check if memory cleanup is needed"""
        memory = psutil.virtual_memory()
        return memory.percent > self.memory_threshold * 100

    def perform_memory_cleanup(self):
        """Perform memory cleanup operations"""
        current_app.logger.info("Performing memory cleanup")

        # Clear SQLAlchemy session
        from app import db
        db.session.expunge_all()

        # Clear cache if memory is critical
        if self.should_cleanup_memory():
            cache_manager = CacheManager()
            cache_manager.clear()

        # Force garbage collection
        import gc
        gc.collect()

        current_app.logger.info("Memory cleanup completed")


class DatabaseConnectionPool:
    def __init__(self, db):
        self.db = db
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'max_connections': 0
        }

    def get_connection_stats(self):
        """Get database connection statistics"""
        try:
            result = self.db.session.execute("SHOW max_connections")
            max_conn = result.scalar()

            result = self.db.session.execute("SELECT count(*) FROM pg_stat_activity")
            active_conn = result.scalar()

            self.connection_stats.update({
                'max_connections': max_conn,
                'active_connections': active_conn,
                'connection_utilization': (active_conn / max_conn) * 100
            })

        except Exception as e:
            current_app.logger.warning(f"Could not get connection stats: {e}")

        return self.connection_stats


# Performance optimization decorators
def async_operation(func):
    """Decorator to run operations asynchronously"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import threading
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    return wrapper


def rate_limited(max_per_second):
    """Decorator to rate limit function calls"""
    min_interval = 1.0 / max_per_second

    def decorator(func):
        last_time_called = [0.0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)

            result = func(*args, **kwargs)
            last_time_called[0] = time.time()
            return result

        return wrapper

    return decorator


def background_task(func):
    """Decorator for background task execution"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from app import celery
        return celery.send_task(f'app.tasks.{func.__name__}', args=args, kwargs=kwargs)

    return wrapper