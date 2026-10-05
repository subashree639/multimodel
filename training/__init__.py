"""Training and data-ingestion package.

Submodules are imported lazily so that ``from training.sales_analytics import
SalesAnalyzer`` (used during application startup) does not eagerly pull in
pandas/the full preprocessing stack.
"""

from typing import Any

__all__ = ["DataPreprocessor"]


def __getattr__(name: str) -> Any:
    if name == "DataPreprocessor":
        from .preprocess_data import DataPreprocessor

        return DataPreprocessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
