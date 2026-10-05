from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from config import settings
from database.mongodb import db_manager
from utils.logging_config import setup_logging
from utils.exceptions import setup_exception_handlers
from api.auth import router as auth_router
from api.products import router as products_router
from api.recommendations import router as recommendations_router
from api.images import router as images_router
from api.reviews import router as reviews_router
from api.chat import router as chat_router
from api.admin import router as admin_router
from api.cart import router as cart_router
from api.wishlist import router as wishlist_router
from api.orders import router as orders_router

setup_logging(getattr(settings, "LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


async def _run_startup_jobs() -> None:
    """Run blocking analytics/segmentation jobs without freezing the event loop."""
    logger.info("[STARTUP] Starting background analytics jobs...")
    try:
        from training.sales_analytics import SalesAnalyzer
        logger.info("[STARTUP] Running sales analytics...")
        analyzer = SalesAnalyzer()
        await asyncio.to_thread(analyzer.update_database_trends)
        logger.info("[STARTUP] Sales trends updated (background)")
    except Exception as e:
        logger.warning(f"[STARTUP] Could not run sales analytics: {e}")

    try:
        from nlp.customer_segmentation import CustomerSegmenter
        logger.info("[STARTUP] Running customer segmentation...")
        segmenter = CustomerSegmenter()
        await asyncio.to_thread(segmenter.update_database_segments)
        logger.info("[STARTUP] Customer segments updated (background)")
    except Exception as e:
        logger.warning(f"[STARTUP] Could not run segmentation: {e}")
    logger.info("[STARTUP] Background analytics jobs complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[STARTUP] Connecting to MongoDB...")
    connected = False
    try:
        connected = await asyncio.wait_for(db_manager.connect_async(), timeout=10)
    except asyncio.TimeoutError:
        logger.error("[STARTUP] MongoDB connection TIMED OUT after 10s")
    except Exception as e:
        logger.error(f"[STARTUP] MongoDB connection error: {e}")

    if not connected:
        logger.error(
            "[STARTUP] MongoDB connection FAILED — check MONGODB_URL in .env and that the server is reachable."
        )
    else:
        logger.info("[STARTUP] MongoDB connected")
        logger.info("[STARTUP] Creating indexes...")
        try:
            await asyncio.wait_for(asyncio.to_thread(db_manager.create_indexes), timeout=15)
            logger.info("[STARTUP] Indexes created")
        except asyncio.TimeoutError:
            logger.error("[STARTUP] Index creation TIMED OUT after 15s")
        except Exception as e:
            logger.error(f"[STARTUP] Index creation failed: {e}")
        # Heavy analytics must NOT block startup — run in background.
        asyncio.create_task(_run_startup_jobs())
        logger.info("[STARTUP] Background jobs scheduled")

    logger.info("[STARTUP] Application startup complete")

    yield

    await db_manager.disconnect_async()
    logger.info("MongoDB disconnected")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MultiModal Product Recommendation System with AI Shopping Assistant",
    version=settings.VERSION,
    lifespan=lifespan,
)

setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(products_router, prefix=f"{settings.API_V1_PREFIX}/products", tags=["Products"])
app.include_router(recommendations_router, prefix=f"{settings.API_V1_PREFIX}/recommendations", tags=["Recommendations"])
app.include_router(images_router, prefix=f"{settings.API_V1_PREFIX}/images", tags=["Image Search"])
app.include_router(reviews_router, prefix=f"{settings.API_V1_PREFIX}/reviews", tags=["Reviews"])
app.include_router(chat_router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Chatbot"])
app.include_router(admin_router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])
app.include_router(cart_router, prefix=f"{settings.API_V1_PREFIX}/cart", tags=["Cart"])
app.include_router(wishlist_router, prefix=f"{settings.API_V1_PREFIX}/wishlist", tags=["Wishlist"])
app.include_router(orders_router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])


@app.get("/health")
async def health_check():
    """Fast liveness probe — never blocks on heavy init.

    Returns healthy when MongoDB pings, degraded otherwise (no hang).
    """
    try:
        if not db_manager.is_connected or db_manager.async_db is None:
            return {"status": "degraded", "version": settings.VERSION, "database": "disconnected"}
        await asyncio.wait_for(db_manager.async_db.command("ping"), timeout=2)
        return {"status": "healthy", "version": settings.VERSION, "database": "connected"}
    except asyncio.TimeoutError:
        return {"status": "degraded", "version": settings.VERSION, "database": "timeout"}
    except Exception as e:
        logger.warning(f"[STARTUP] Health check DB ping failed: {e}")
        return {"status": "degraded", "version": settings.VERSION, "database": "unavailable"}


@app.get(f"{settings.API_V1_PREFIX}/")
async def root():
    return {
        "message": "Welcome to MultiModal Product Recommendation API",
        "docs": "/docs",
        "version": settings.VERSION,
    }


@app.get("/health/chat")
async def chat_health():
    """Chatbot readiness: the production assistant (api/chat.py) answers from
    live MongoDB data, so readiness == database reachability."""
    try:
        if not db_manager.is_connected or db_manager.async_db is None:
            return {"chatbot_ready": False, "reason": "database disconnected"}
        await asyncio.wait_for(db_manager.async_db.command("ping"), timeout=2)
        return {"chatbot_ready": True, "mode": "mongodb_grounded"}
    except Exception as e:
        return {"chatbot_ready": False, "reason": str(e)[:120]}
