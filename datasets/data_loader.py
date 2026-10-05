import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class DataLoader:
    """Load and preprocess datasets from CSV files.

    Row limits keep ingestion fast and are configurable; pass ``0`` (or a
    negative number) to disable a limit entirely.
    """

    def __init__(
        self,
        datasets_dir: str = "datasets",
        max_products: int = 1000,
        max_reviews: int = 1500,
        max_customers: int = 1000,
    ):
        self.datasets_dir = Path(datasets_dir)
        self.max_products = max_products
        self.max_reviews = max_reviews
        self.max_customers = max_customers
        self.sales_df: Optional[pd.DataFrame] = None
        self.reviews_df: Optional[pd.DataFrame] = None
        self.customer_df: Optional[pd.DataFrame] = None

    @staticmethod
    def _apply_limit(df: pd.DataFrame, limit: int) -> pd.DataFrame:
        """Return ``df`` truncated to ``limit`` rows (no truncation if <= 0)."""
        if limit and limit > 0:
            return df.head(limit)
        return df

    def load_sales(self, filename: str = "sales.csv") -> pd.DataFrame:
        path = self.datasets_dir / "sales" / filename
        if not path.exists():
            raise FileNotFoundError(f"Sales data not found at {path}")
        self.sales_df = pd.read_csv(path)
        self._clean_sales()
        logger.info(f"Loaded {len(self.sales_df)} sales records")
        return self.sales_df

    def _clean_sales(self):
        df = self.sales_df
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        if "ratings" in df.columns:
            df["ratings"] = pd.to_numeric(df["ratings"], errors="coerce")
        if "no_of_ratings" in df.columns:
            df["no_of_ratings"] = df["no_of_ratings"].astype(str).str.replace(",", "", regex=False)
            df["no_of_ratings"] = pd.to_numeric(df["no_of_ratings"], errors="coerce")
        if "discount_price" in df.columns:
            df["discount_price"] = df["discount_price"].astype(str).str.replace(r"[^\d.]", "", regex=True)
            df["discount_price"] = pd.to_numeric(df["discount_price"], errors="coerce")
        if "actual_price" in df.columns:
            df["actual_price"] = df["actual_price"].astype(str).str.replace(r"[^\d.]", "", regex=True)
            df["actual_price"] = pd.to_numeric(df["actual_price"], errors="coerce")
        df = df.fillna({"ratings": 0, "no_of_ratings": 0, "discount_price": 0, "actual_price": 0})
        df = self._apply_limit(df, self.max_products)
        self.sales_df = df

    def load_reviews(self, filename: str = "reviews.csv") -> pd.DataFrame:
        path = self.datasets_dir / "reviews" / filename
        if not path.exists():
            raise FileNotFoundError(f"Reviews data not found at {path}")
        self.reviews_df = pd.read_csv(path)
        self._clean_reviews()
        logger.info(f"Loaded {len(self.reviews_df)} review records")
        return self.reviews_df

    def _clean_reviews(self):
        df = self.reviews_df
        col_map = {
            "reviews.rating": "rating",
            "reviews.text": "text",
            "reviews.title": "title",
            "reviews.username": "username",
            "reviews.date": "date",
            "name": "product_name",
            "asins": "asins",
            "brand": "brand",
            "categories": "categories",
            "primaryCategories": "primary_category",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "text" not in df.columns:
            for c in df.columns:
                if "text" in c.lower():
                    df = df.rename(columns={c: "text"})
                    break
        if "rating" not in df.columns:
            for c in df.columns:
                if "rating" in c.lower():
                    df = df.rename(columns={c: "rating"})
                    break
        keep = [c for c in ["product_name", "brand", "rating", "text", "title", "username", "date", "categories", "primary_category", "asins"] if c in df.columns]
        df = df[keep].copy()
        if "text" in df.columns:
            df = df.dropna(subset=["text"])
        df = self._apply_limit(df, self.max_reviews)
        self.reviews_df = df

    def load_customer_behaviour(self, filename: str = "customerbehaviour.csv") -> pd.DataFrame:
        path = self.datasets_dir / "customerbehaviour" / filename
        if not path.exists():
            raise FileNotFoundError(f"Customer behaviour data not found at {path}")
        self.customer_df = pd.read_csv(path)
        self.customer_df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in self.customer_df.columns]
        self.customer_df = self._apply_limit(self.customer_df, self.max_customers)
        logger.info(f"Loaded {len(self.customer_df)} customer records")
        return self.customer_df

    def get_product_catalog(self) -> List[Dict]:
        if self.sales_df is None:
            self.load_sales()
        df = self.sales_df
        products = []
        for _, row in df.iterrows():
            price = float(row.get("discount_price", 0) or 0)
            price = price if price > 0 else float(row.get("actual_price", 0) or 0)
            products.append({
                "name": str(row.get("name", "")),
                "category": str(row.get("main_category", "")).lower(),
                "subcategory": str(row.get("sub_category", "")).lower(),
                "price": price,
                "description": str(row.get("name", "")),
                "features": [],
                "image_link": str(row.get("image", "")),
                "product_link": str(row.get("link", "")),
                "ratings": float(row.get("ratings", 0) or 0),
                "no_of_ratings": int(row.get("no_of_ratings", 0) or 0),
            })
        return products

    def get_user_reviews(self) -> List[Dict]:
        if self.reviews_df is None:
            self.load_reviews()
        df = self.reviews_df
        reviews = []
        for _, row in df.iterrows():
            reviews.append({
                "user_id": str(row.get("username", row.get("user_id", ""))),
                "product_id": "",
                "product_name": str(row.get("product_name", "")),
                "rating": int(row.get("rating", 3) or 3),
                "text": str(row.get("text", "")),
                "title": str(row.get("title", "")),
                "date": str(row.get("date", "")),
                "brand": str(row.get("brand", "")),
                "categories": str(row.get("categories", "")),
                "primary_category": str(row.get("primary_category", "")),
            })
        return reviews

    def get_customer_profiles(self) -> List[Dict]:
        if self.customer_df is None:
            self.load_customer_behaviour()
        df = self.customer_df
        profiles = []
        for _, row in df.iterrows():
            profiles.append({
                "customer_id": str(row.get("customer_id", "")),
                "gender": str(row.get("gender", "")),
                "age": int(row.get("age", 0) or 0),
                "city": str(row.get("city", "")),
                "membership_type": str(row.get("membership_type", "")),
                "total_spend": float(row.get("total_spend", 0) or 0),
                "items_purchased": int(row.get("items_purchased", 0) or 0),
                "average_rating": float(row.get("average_rating", 0) or 0),
                "discount_applied": str(row.get("discount_applied", "")),
                "days_since_last_purchase": int(row.get("days_since_last_purchase", 0) or 0),
                "satisfaction_level": str(row.get("satisfaction_level", "")),
            })
        return profiles
