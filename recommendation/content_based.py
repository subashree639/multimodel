"""
Content-based filtering recommendation system.
Uses product features and user preferences to find similar products.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)


class ContentBasedRecommender:
    """Content-based filtering recommender using product features and text."""

    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.scaler = MinMaxScaler()
        self.feature_matrix = None
        self.product_ids = []
        self.product_features = {}
        self.is_fitted = False

    def prepare_product_features(self, products: List[Dict]) -> pd.DataFrame:
        """
        Prepare and combine product features into a unified feature string.

        Args:
            products: List of product dictionaries from database

        Returns:
            DataFrame with combined features for each product
        """
        feature_data = []

        for product in products:
            if product.get('_id') is None:
                continue
            # Combine textual features
            feature_parts = [
                product.get('name', ''),
                product.get('description', ''),
                product.get('category', ''),
                product.get('subcategory', ''),
                ' '.join(product.get('features', []) or []),
            ]

            combined_features = ' '.join(str(f) for f in feature_parts if f)
            feature_data.append({
                'product_id': str(product['_id']),
                'name': product.get('name', ''),
                'combined_features': combined_features,
                'category': product.get('category', ''),
                'subcategory': product.get('subcategory', ''),
                'price': product.get('price', 0),
                'avg_rating': product.get('avg_rating', 0),
                'num_reviews': product.get('num_reviews', 0)
            })

            # Store for later use
            self.product_features[str(product['_id'])] = {
                'name': product.get('name', ''),
                'category': product.get('category', ''),
                'subcategory': product.get('subcategory', ''),
                'price': product.get('price', 0),
                'avg_rating': product.get('avg_rating', 0),
                'num_reviews': product.get('num_reviews', 0),
                'features': product.get('features', [])
            }

        return pd.DataFrame(feature_data)

    def fit(self, products: List[Dict]) -> None:
        """
        Fit the recommender on the product catalog.

        Args:
            products: List of product dictionaries from database
        """
        logger.info(f"Fitting content-based recommender with {len(products)} products")
        self.is_fitted = False
        self.feature_matrix = None
        self.product_ids = []
        self.product_features = {}

        if not products:
            logger.warning("No products supplied to content-based recommender")
            return

        df = self.prepare_product_features(products)
        if df.empty:
            logger.warning("Product feature frame is empty")
            return

        self.product_ids = df['product_id'].tolist()

        # Text feature matrix using TF-IDF
        try:
            text_matrix = self.tfidf_vectorizer.fit_transform(df['combined_features'])
        except ValueError as e:
            # e.g. "empty vocabulary" when every title is a stop word
            logger.warning("TF-IDF could not be fitted: %s", e)
            self.product_ids = []
            return
        text_matrix = text_matrix.toarray()

        # Numeric features: price, rating, num_reviews
        numeric_features = df[['price', 'avg_rating', 'num_reviews']].fillna(0).values
        numeric_features = self.scaler.fit_transform(numeric_features)

        # Combine text and numeric features
        self.feature_matrix = np.hstack([text_matrix, numeric_features])

        self.is_fitted = True
        logger.info(f"Content-based recommender fitted. Feature matrix shape: {self.feature_matrix.shape}")

    def get_recommendations(
        self,
        user_preferences: Dict,
        user_history: List[str],
        top_n: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        """
        Get content-based recommendations for a user.

        Args:
            user_preferences: User preference dictionary (categories, features, etc.)
            user_history: List of product IDs the user has interacted with
            top_n: Number of recommendations to return

        Returns:
            List of tuples: (product_id, score, explanation)
        """
        if not self.is_fitted or self.feature_matrix is None:
            logger.warning("Recommender not fitted yet")
            return []

        # Build user profile from preferences and history
        user_profile = self._build_user_profile(user_preferences, user_history)

        # Calculate similarity scores
        similarities = cosine_similarity([user_profile], self.feature_matrix)[0]

        # Get recommendations, excluding items in user history
        recommendations = []
        explanation = []

        if user_preferences.get('preferred_categories'):
            for cat in user_preferences['preferred_categories']:
                explanation.append(f"Category match: {cat}")

        if user_preferences.get('preferred_features'):
            for feat in user_preferences['preferred_features']:
                explanation.append(f"Feature match: {feat}")

        history_set = set(user_history)
        ranked_indices = np.argsort(similarities)[::-1]

        for idx in ranked_indices:
            if len(recommendations) >= top_n:
                break

            product_id = self.product_ids[idx]
            if product_id in history_set:
                continue

            score = float(similarities[idx])
            product_info = self.product_features.get(product_id, {})

            rec_explanation = {
                'reason': 'Content-based match',
                'details': explanation.copy(),
                'similarity_score': score,
                'matched_category': product_info.get('category', ''),
                'matched_features': product_info.get('features', [])[:3]
            }

            recommendations.append((product_id, score, rec_explanation))

        return recommendations

    def _build_user_profile(self, preferences: Dict, history: List[str]) -> np.ndarray:
        """Build a user profile vector.

        * Interaction history contributes 60 % (when known product ids exist).
        * Declared preferences contribute 40 % whenever present — previously
          they were only consulted when history was *completely* empty, so a
          user with a few unknown/legacy history ids silently got an all-zero
          profile and every cosine score came back 0.0.
        """
        if not self.is_fitted:
            return np.zeros(self.feature_matrix.shape[1])

        profile = np.zeros(self.feature_matrix.shape[1])
        id_to_index = {pid: i for i, pid in enumerate(self.product_ids)}

        history_vectors = [
            self.feature_matrix[id_to_index[pid]]
            for pid in history
            if pid in id_to_index
        ]
        if history_vectors:
            profile += 0.6 * np.mean(history_vectors, axis=0)

        preference_text = ' '.join([
            ' '.join(preferences.get('preferred_categories', []) or []),
            ' '.join(preferences.get('preferred_features', []) or []),
            preferences.get('search_query', '') or '',
        ]).strip()

        if preference_text:
            pref_vector = self.tfidf_vectorizer.transform([preference_text]).toarray()[0]
            tfidf_dim = pref_vector.shape[0]
            weight = 0.4 if history_vectors else 1.0
            # feature_matrix = [TF-IDF (tfidf_dim) | numeric (rest)]; only the
            # text part gets the preference signal, numeric part stays 0.
            profile[:tfidf_dim] += weight * pref_vector

        return profile

    def get_similar_products(self, product_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Find products similar to a given product.

        Args:
            product_id: The product ID to find similar products for
            top_n: Number of similar products to return

        Returns:
            List of tuples: (product_id, similarity_score)
        """
        if not self.is_fitted:
            return []

        if product_id not in self.product_ids:
            return []

        idx = self.product_ids.index(product_id)
        target_vector = self.feature_matrix[idx].reshape(1, -1)
        similarities = cosine_similarity(target_vector, self.feature_matrix)[0]

        ranked_indices = np.argsort(similarities)[::-1]
        similar_products = []

        for i in ranked_indices:
            if len(similar_products) >= top_n:
                break
            if self.product_ids[i] != product_id:
                similar_products.append((self.product_ids[i], float(similarities[i])))

        return similar_products
