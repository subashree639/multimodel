"""Customer segmentation with K-Means clustering.

Segments users from the numeric fields stored in ``users.preferences``
(``age``, ``total_spend``, ``items_purchased``, ``days_since_last_purchase``)
and writes the resulting label back to ``preferences.segment``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: F401  (ensures settings/.env are loaded)
from database.mongodb import db_manager

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["age", "total_spend", "items_purchased", "days_since_last_purchase"]


class CustomerSegmenter:
    """K-Means clustering over customer behavioural features."""

    def __init__(self, n_clusters: int = 3):
        self.n_clusters = n_clusters
        self.kmeans: Optional[KMeans] = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_columns: List[str] = []
        self.cluster_names: Dict[int, str] = {
            0: "Budget Shoppers",
            1: "Loyal Customers",
            2: "Premium Buyers",
        }

    def fit(self, customers_data: List[Dict[str, Any]]) -> None:
        """Fit scaler + K-Means on the numeric feature columns.

        Stores the exact column list used so :meth:`predict` feeds the same
        features (mismatch here raises ``X has 4 features...`` otherwise).
        """
        self.is_fitted = False
        if not customers_data:
            logger.warning("No customer data provided for segmentation.")
            return

        df = pd.DataFrame(customers_data)
        available = [f for f in FEATURE_COLUMNS if f in df.columns]
        if len(available) < 2:
            logger.warning("Not enough numerical features for clustering.")
            return

        X = df[available].fillna(0)
        if len(X) < 2:
            logger.warning("Not enough customers for clustering (%d rows).", len(X))
            return

        self.feature_columns = available
        # Fit on a plain ndarray so `predict` (which passes a list) does not
        # trigger sklearn's "does not have valid feature names" warning.
        X_scaled = self.scaler.fit_transform(X.to_numpy(dtype=float))

        n_clusters = min(self.n_clusters, len(X))
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.kmeans.fit(X_scaled)

        # Name clusters from the spend centre (lowest = Budget, highest = Premium)
        if "total_spend" in available:
            spend_idx = available.index("total_spend")
            spend_centers = self.kmeans.cluster_centers_[:, spend_idx]
            order = spend_centers.argsort()
            self.cluster_names[int(order[0])] = "Budget Shoppers"
            if n_clusters > 2:
                self.cluster_names[int(order[1])] = "Frequent Buyers"
            elif n_clusters == 2:
                self.cluster_names[int(order[1])] = "Frequent Buyers"
            self.cluster_names[int(order[-1])] = "Premium Buyers"

        self.is_fitted = True
        logger.info("Customer segmentation fitted with %d clusters.", n_clusters)

    def predict(self, customer_data: Dict[str, Any]) -> str:
        """Predict the segment label for one customer."""
        if not self.is_fitted or self.kmeans is None:
            return "General Buyer"

        row = [[float(customer_data.get(f, 0) or 0) for f in self.feature_columns]]
        X_scaled = self.scaler.transform(row)
        cluster_id = int(self.kmeans.predict(X_scaled)[0])
        return self.cluster_names.get(cluster_id, f"Group {cluster_id}")

    def update_database_segments(self) -> None:
        """Fetch all users, segment them, and write ``preferences.segment``."""
        db = db_manager.get_sync_db()
        users = list(db.users.find({}))
        if not users:
            logger.warning("No users to segment.")
            return

        dataset: List[Dict[str, Any]] = []
        for u in users:
            prefs = u.get("preferences", {}) or {}
            dataset.append({
                "_id": u["_id"],
                "age": prefs.get("age", 30),
                "total_spend": prefs.get("total_spend", 0),
                "items_purchased": prefs.get("items_purchased", 0),
                "days_since_last_purchase": prefs.get("days_since_last_purchase", 10),
            })

        self.fit(dataset)
        if not self.is_fitted:
            return

        from pymongo import UpdateOne

        ops = [
            UpdateOne({"_id": d["_id"]}, {"$set": {"preferences.segment": self.predict(d)}})
            for d in dataset
        ]
        if ops:
            db.users.bulk_write(ops, ordered=False)
        logger.info("Updated segments for %d users.", len(ops))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    CustomerSegmenter().update_database_segments()
