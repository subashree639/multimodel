"""
MongoDB connection manager for the MultiModal recommendation system.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import logging

from config import settings

logger = logging.getLogger(__name__)


def _client_options(uri: str) -> dict:
    """Build client options.

    TLS with the bundled CA store is only enabled for URIs that actually
    require it (`mongodb+srv://` or an explicit `tls=true`). Applying
    ``tlsCAFile`` unconditionally forces TLS on plaintext ``mongodb://``
    connections, which breaks local development.
    """
    if uri.startswith("mongodb+srv://") or "tls=true" in uri or "ssl=true" in uri:
        import certifi
        return {"tlsCAFile": certifi.where()}
    return {}


class MongoDBManager:
    """Manages MongoDB connections for both sync and async operations."""

    def __init__(self):
        self.sync_client: Optional[MongoClient] = None
        self.async_client: Optional[AsyncIOMotorClient] = None
        self.sync_db = None
        self.async_db = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Whether an async connection has been successfully established."""
        return self._connected

    def connect_sync(self):
        """Establish synchronous MongoDB connection."""
        try:
            self.sync_client = MongoClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                **_client_options(settings.MONGODB_URL),
            )
            self.sync_client.admin.command("ping")
            self.sync_db = self.sync_client[settings.MONGODB_DB_NAME]
            logger.info("Sync MongoDB connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (sync): {e}")
            self.sync_client = None
            self.sync_db = None
            return False

    async def connect_async(self):
        """Establish asynchronous MongoDB connection."""
        try:
            self.async_client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                **_client_options(settings.MONGODB_URL),
            )
            self.async_db = self.async_client[settings.MONGODB_DB_NAME]
            await self.async_db.command("ping")
            self._connected = True
            logger.info("Async MongoDB connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (async): {e}")
            self.async_client = None
            self.async_db = None
            self._connected = False
            return False

    def disconnect_sync(self):
        """Close synchronous MongoDB connection."""
        if self.sync_client:
            self.sync_client.close()
            logger.info("Sync MongoDB connection closed")

    async def disconnect_async(self):
        """Close asynchronous MongoDB connection."""
        if self.async_client:
            self.async_client.close()
            self._connected = False
            logger.info("Async MongoDB connection closed")

    def get_sync_db(self):
        """Get synchronous database instance, connecting on first use."""
        if self.sync_db is None:
            self.connect_sync()
        if self.sync_db is None:
            raise RuntimeError(
                "MongoDB is not available. Check MONGODB_URL in .env and that the server is running."
            )
        return self.sync_db

    def get_async_db(self):
        """Get asynchronous database instance.

        Must be called from a running event loop (i.e. inside a request).
        Never calls ``run_until_complete`` — that raises inside a live loop.
        """
        if self.async_db is None:
            raise RuntimeError(
                "MongoDB async connection not initialised. Connect during application startup."
            )
        return self.async_db

    def get_collection(self, collection_name: str):
        """Get a specific collection from the sync database."""
        db = self.get_sync_db()
        return db[collection_name]

    def get_async_collection(self, collection_name: str):
        """Get a specific collection from the async database."""
        db = self.get_async_db()
        return db[collection_name]

    def create_indexes(self):
        """Create indexes for optimized query performance."""
        try:
            db = self.get_sync_db()

            # Users collection indexes
            db.users.create_index("email", unique=True)

            # Products collection indexes
            db.products.create_index("category")
            db.products.create_index("subcategory")
            db.products.create_index("price")

            # Reviews collection indexes
            db.reviews.create_index([("product_id", 1), ("user_id", 1)], unique=True)
            db.reviews.create_index("product_id")
            db.reviews.create_index("user_id")
            db.reviews.create_index("sentiment")

            # Recommendations collection indexes
            db.recommendations.create_index([("user_id", 1), ("timestamp", -1)])

            # Image embeddings collection indexes
            db.image_embeddings.create_index("product_id", unique=True)

            # Cart collection indexes (unique per user+product prevents duplicate rows)
            db.cart.create_index("user_id")
            db.cart.create_index(
                [("user_id", 1), ("product_id", 1)], unique=True
            )

            # Wishlist collection indexes
            db.wishlist.create_index("user_id")
            db.wishlist.create_index(
                [("user_id", 1), ("product_id", 1)], unique=True
            )

            # Orders collection indexes
            db.orders.create_index("user_id")
            db.orders.create_index("created_at")

            # User behavior collection indexes
            db.user_behavior.create_index("user_id")
            db.user_behavior.create_index("product_id")
            db.user_behavior.create_index("timestamp")

            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")


# Global MongoDB manager instance
db_manager = MongoDBManager()
