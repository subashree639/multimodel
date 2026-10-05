"""
Sample dataset loaders for multimodal recommendation system.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List

from datasets.data_loader import DataLoader

logger = logging.getLogger(__name__)


def load_all_datasets(datasets_dir: str = "datasets") -> Dict:
    loader = DataLoader(datasets_dir)
    data = {
        "sales": loader.load_sales(),
        "reviews": loader.load_reviews(),
        "customer_behaviour": loader.load_customer_behaviour(),
        "products": loader.get_product_catalog(),
        "reviews_list": loader.get_user_reviews(),
        "customers": loader.get_customer_profiles(),
    }
    logger.info("All datasets loaded successfully")
    return data


def get_sample_data(n_products: int = 100, n_reviews: int = 200) -> Dict:
    loader = DataLoader()
    products = loader.get_product_catalog()[:n_products]
    reviews = loader.get_user_reviews()[:n_reviews]
    customers = loader.get_customer_profiles()[:50]
    return {"products": products, "reviews": reviews, "customers": customers}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = load_all_datasets()
    for k, v in data.items():
        if isinstance(v, pd.DataFrame):
            print(f"{k}: {len(v)} rows, columns: {list(v.columns)}")
        elif isinstance(v, list):
            print(f"{k}: {len(v)} items")
