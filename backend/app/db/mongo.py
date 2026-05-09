"""
Cliente Mongo compartido (Motor async) — MetanoSRGAN Elite v5.0
Soporta modo mock cuando MongoDB no está disponible (desarrollo/demo).
"""
import asyncio
import logging
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

log = logging.getLogger("metavision.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_mock_db = None


def _get_mock_db():
    """Retorna una base de datos mock en memoria usando mongomock."""
    global _mock_db
    if _mock_db is None:
        try:
            import mongomock
            mock_client = mongomock.MongoClient()
            _mock_db = mock_client[settings.db_name]
            log.warning("Using mongomock in-memory database (MongoDB not available)")
        except ImportError:
            log.error("mongomock not installed, DB operations will fail")
            raise
    return _mock_db


def get_db():
    """Retorna la base de datos (real o mock)."""
    global _client, _db
    if _db is None:
        try:
            _client = AsyncIOMotorClient(
                settings.mongo_url,
                serverSelectionTimeoutMS=2000,  # timeout rápido
            )
            _db = _client[settings.db_name]
            log.info("Connected to MongoDB at %s", settings.mongo_url)
        except Exception as e:
            log.warning("MongoDB connection failed (%s), using mock", e)
            return _get_mock_db()
    return _db


async def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
