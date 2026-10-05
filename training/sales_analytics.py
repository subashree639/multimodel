"""Trending-product analytics.

Fits a small Random Forest over product features to rank a "sales velocity"
proxy and flags the top results as ``is_trending`` in MongoDB.

Note: the catalogue has no historical unit-sales series, so the regression
target is derived from ``num_reviews`` and ``avg_rating`` with seeded noise —
the randomness is fixed (``seed=42``) so trending flags are stable across
restarts instead of reshuffling on every boot.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database.mongodb import db_manager

logger = logging.getLogger(__name__)


class SalesAnalyzer:
    """Predicts trending products using a Random Forest regressor."""

    def __init__(self, seed: int = 42, top_n: int = 20):
        self.seed = seed
        self.top_n = top_n
        self.model = RandomForestRegressor(n_estimators=100, random_state=seed)
        self.is_fitted = False
        self.trending_products: List[str] = []

    def fit(self, products_data: List[Dict]) -> None:
        """Fit on product documents and compute the trending top-N."""
        self.is_fitted = False
        self.trending_products = []
        if not products_data:
            logger.warning("No product data for sales analytics.")
            return

        # Only documents that carry both an id and the numeric features are usable.
        usable = [
            p for p in products_data
            if p.get("_id") is not None
            and p.get("num_reviews") is not None
            and p.get("avg_rating") is not None
        ]
        if len(usable) < 2:
            logger.warning("Not enough usable product rows for sales analytics.")
            return

        df = pd.DataFrame(usable)
        df["price"] = pd.to_numeric(df.get("price"), errors="coerce").fillna(0)

        rng = np.random.default_rng(self.seed)
        df["sales_velocity"] = (
            df["num_reviews"].astype(float) * (df["avg_rating"].astype(float) / 5.0)
            + rng.normal(0, 5, len(df))
        )

        features = [f for f in ("price", "avg_rating", "num_reviews") if f in df.columns]
        X = df[features].fillna(0)
        y = df["sales_velocity"].fillna(0)

        self.model.fit(X, y)
        df["predicted_trend"] = self.model.predict(X)

        top = df.sort_values("predicted_trend", ascending=False).head(self.top_n)
        self.trending_products = [str(_id) for _id in top["_id"].tolist()]
        self.is_fitted = True
        logger.info(
            "Sales analyzer fitted. Identified %d trending products.",
            len(self.trending_products),
        )

    def is_trending(self, product_id: str) -> bool:
        """Check if a product is currently trending."""
        return product_id in self.trending_products

    def get_trending_products(self) -> List[str]:
        """Return the current trending product ids."""
        return self.trending_products

    def update_database_trends(self) -> None:
        """Fetch products, run analytics, and update ``is_trending`` flags."""
        db = db_manager.get_sync_db()
        products = list(db.products.find({}))

        self.fit(products)
        if not self.is_fitted:
            return

        from bson import ObjectId

        db.products.update_many({}, {"$set": {"is_trending": False}})
        object_ids = []
        for pid in self.trending_products:
            try:
                object_ids.append(ObjectId(pid))
            except Exception:
                continue
        if object_ids:
            db.products.update_many(
                {"_id": {"$in": object_ids}}, {"$set": {"is_trending": True}}
            )
        logger.info("Updated product trends in database.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SalesAnalyzer().update_database_trends()
