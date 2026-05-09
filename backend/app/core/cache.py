"""
Sistema de caché para tRPC - Optimización de consultas frecuentes
Implementa caché en memoria con TTL configurable
"""

from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json
import asyncio

T = TypeVar('T')


class CacheEntry:
    """Entrada individual en el caché"""
    def __init__(self, value: Any, ttl_seconds: int = 300):
        self.value = value
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Verificar si la entrada ha expirado"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def __repr__(self):
        return f"CacheEntry(created={self.created_at}, ttl={self.ttl_seconds}s, expired={self.is_expired()})"


class MemoryCache:
    """Caché en memoria con TTL y limpieza automática"""

    def __init__(self, max_size: int = 1000, cleanup_interval: int = 60):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.hits = 0
        self.misses = 0
        self._cleanup_task = None

    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """Generar clave única basada en namespace y parámetros"""
        key_data = {
            'namespace': namespace,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del caché"""
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Guardar valor en el caché"""
        # Limpiar si se alcanza el tamaño máximo
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = CacheEntry(value, ttl_seconds)

    def delete(self, key: str):
        """Eliminar entrada del caché"""
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """Limpiar todo el caché"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def _evict_oldest(self):
        """Evict la entrada más antigua cuando se alcanza el límite"""
        if not self.cache:
            return
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        del self.cache[oldest_key]

    def cleanup_expired(self):
        """Limpiar entradas expiradas"""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del caché"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f'{hit_rate:.2f}%',
            'total_requests': total_requests
        }


# Instancia global del caché
_global_cache = MemoryCache(max_size=1000, cleanup_interval=60)


def cached(namespace: str, ttl_seconds: int = 300):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        namespace: Nombre del espacio de caché (ej: 'stats.overview')
        ttl_seconds: Tiempo de vida en segundos (default: 5 minutos)
    
    Ejemplo:
        @cached('stats.overview', ttl_seconds=300)
        async def get_overview():
            return {...}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generar clave
            cache_key = _global_cache._generate_key(namespace, *args, **kwargs)

            # Intentar obtener del caché
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Ejecutar función
            result = await func(*args, **kwargs)

            # Guardar en caché
            _global_cache.set(cache_key, result, ttl_seconds)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generar clave
            cache_key = _global_cache._generate_key(namespace, *args, **kwargs)

            # Intentar obtener del caché
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Ejecutar función
            result = func(*args, **kwargs)

            # Guardar en caché
            _global_cache.set(cache_key, result, ttl_seconds)

            return result

        # Retornar la versión correcta
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(namespace: str = None):
    """Invalidar caché por namespace"""
    if namespace is None:
        _global_cache.clear()
    else:
        # Limpiar todas las claves que contengan el namespace
        keys_to_delete = [k for k in _global_cache.cache.keys() if namespace in k]
        for key in keys_to_delete:
            _global_cache.delete(key)


def get_cache_stats() -> Dict[str, Any]:
    """Obtener estadísticas del caché global"""
    return _global_cache.get_stats()


def cleanup_cache():
    """Limpiar entradas expiradas del caché"""
    return _global_cache.cleanup_expired()
