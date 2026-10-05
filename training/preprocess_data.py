import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, Tuple

from datasets.data_loader import DataLoader

logger = logging.getLogger(__name__)


class DataPreprocessor:
    def __init__(self, datasets_dir: str = "datasets", output_dir: str = "datasets/processed"):
        self.datasets_dir = Path(datasets_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.loader = DataLoader(datasets_dir)

    def run(self) -> Dict[str, Path]:
        sales = self.loader.load_sales()
        reviews = self.loader.load_reviews()
        customers = self.loader.load_customer_behaviour()
        products = self._build_products(sales)
        review_texts = self._build_review_texts(reviews)
        user_profiles = self._build_user_profiles(customers)
        products_path = self.output_dir / "products.parquet"
        reviews_path = self.output_dir / "reviews.parquet"
        customers_path = self.output_dir / "customers.parquet"
        pd.DataFrame(products).to_parquet(products_path, index=False)
        pd.DataFrame(review_texts).to_parquet(reviews_path, index=False)
        pd.DataFrame(user_profiles).to_parquet(customers_path, index=False)
        logger.info("Saved processed data to %s", self.output_dir)
        return {"products": products_path, "reviews": reviews_path, "customers": customers_path}

    def _build_products(self, sales: pd.DataFrame) -> list:
        rows = []
        for _, r in sales.iterrows():
            price = float(r.get("discount_price", 0) or 0)
            if price <= 0:
                price = float(r.get("actual_price", 0) or 0)
            rows.append({
                "product_id": str(r.get("unnamed:_0", "")),
                "name": str(r.get("name", "")),
                "category": str(r.get("main_category", "")),
                "subcategory": str(r.get("sub_category", "")),
                "price": price,
                "rating": float(r.get("ratings", 0) or 0),
                "num_ratings": int(r.get("no_of_ratings", 0) or 0),
                "image": str(r.get("image", "")),
                "link": str(r.get("link", "")),
            })
        return rows

    def _build_review_texts(self, reviews: pd.DataFrame) -> list:
        if "text" not in reviews.columns:
            return []
        out = []
        for _, r in reviews.iterrows():
            text = r.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue
            out.append({
                "review_id": str(_),
                "product_name": str(r.get("product_name", "")),
                "brand": str(r.get("brand", "")),
                "rating": int(r.get("rating", 3) or 3),
                "text": text,
                "title": str(r.get("title", "")),
                "username": str(r.get("username", "")),
                "date": str(r.get("date", "")),
            })
        return out

    def _build_user_profiles(self, customers: pd.DataFrame) -> list:
        rows = []
        for _, r in customers.iterrows():
            rows.append({
                "customer_id": str(r.get("customer_id", "")),
                "gender": str(r.get("gender", "")),
                "age": int(r.get("age", 0) or 0),
                "city": str(r.get("city", "")),
                "membership_type": str(r.get("membership_type", "")),
                "total_spend": float(r.get("total_spend", 0) or 0),
                "items_purchased": int(r.get("items_purchased", 0) or 0),
                "average_rating": float(r.get("average_rating", 0) or 0),
                "discount_applied": str(r.get("discount_applied", "")),
                "days_since_last_purchase": int(r.get("days_since_last_purchase", 0) or 0),
                "satisfaction_level": str(r.get("satisfaction_level", "")),
            })
        return rows


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    preprocessor = DataPreprocessor()
    paths = preprocessor.run()
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
