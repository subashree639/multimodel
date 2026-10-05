"""
Explainable AI module for recommendation explanations.
Provides human-readable reasons for each recommendation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class ExplainableAI:
    """Generates explanations for product recommendations."""

    def __init__(self):
        self.explanation_templates = {
            'content_similarity': "Similar to products you viewed",
            'category_match': "Matches your preferred category: {category}",
            'high_rating': "Highly rated ({rating:.1f}/5 by {num_reviews} users)",
            'popular': "Popular choice with {num_reviews} reviews",
            'feature_match': "Matches features you like: {features}",
            'price_range': "Fits your budget (${price})",
            'collaborative': "Recommended by users with similar taste",
            'sentiment_positive': "Has positive reviews sentiment",
            'history_based': "Based on your purchase history",
            'trending': "Currently trending in {category}"
        }

    def generate_explanation(
        self,
        product_id: str,
        product_info: Dict[str, Any],
        user_preferences: Dict[str, Any],
        user_history: List[str],
        scores: Dict[str, float],
        total_score: float
    ) -> Dict[str, Any]:
        """
        Generate a detailed explanation for a recommendation.

        Args:
            product_id: The recommended product ID
            product_info: Product details from database
            user_preferences: User's preference settings
            user_history: User's interaction history
            scores: Individual scores from different algorithms
            total_score: Combined confidence score

        Returns:
            Explanation dictionary with reasons and confidence
        """
        reasons = []
        confidence_factors = []

        # Content-based reasons
        category = product_info.get('category', '')
        subcategory = product_info.get('subcategory', '')
        avg_rating = product_info.get('avg_rating', 0)
        num_reviews = product_info.get('num_reviews', 0)
        price = product_info.get('price', 0)
        features = product_info.get('features', [])

        # Category match
        preferred_cats = user_preferences.get('preferred_categories', [])
        if not preferred_cats:
            preferred_cats = [user_preferences.get('category', '')]
        preferred_cats = [c for c in preferred_cats if c]

        if category in preferred_cats or subcategory in preferred_cats:
            reasons.append(self.explanation_templates['category_match'].format(category=category))
            confidence_factors.append(('category_match', 0.3))

        # Feature match
        preferred_features = user_preferences.get('preferred_features', [])
        matched_features = [f for f in features if f in preferred_features] if preferred_features else []
        if matched_features:
            reasons.append(
                self.explanation_templates['feature_match'].format(
                    features=', '.join(matched_features[:3])
                )
            )
            confidence_factors.append(('feature_match', 0.2))

        # High rating
        if avg_rating >= 4.0:
            reasons.append(
                self.explanation_templates['high_rating'].format(
                    rating=avg_rating, num_reviews=num_reviews
                )
            )
            confidence_factors.append(('high_rating', 0.15))

        # Popularity
        if num_reviews > 50:
            reasons.append(
                self.explanation_templates['popular'].format(num_reviews=num_reviews)
            )
            confidence_factors.append(('popular', 0.1))

        # Price range
        budget = user_preferences.get('budget_range', {})
        if budget:
            min_budget = budget.get('min', 0)
            max_budget = budget.get('max', float('inf'))
            if min_budget <= price <= max_budget:
                reasons.append(self.explanation_templates['price_range'].format(price=price))
                confidence_factors.append(('price_match', 0.1))

        # Collaborative filtering score
        collab_score = scores.get('collaborative', 0)
        if collab_score > 0.5:
            reasons.append(self.explanation_templates['collaborative'])
            confidence_factors.append(('collaborative', 0.15))

        # Content similarity score
        content_score = scores.get('content', 0)
        if content_score > 0.3:
            reasons.append(self.explanation_templates['content_similarity'])
            confidence_factors.append(('content_similarity', 0.1))

        # History-based
        if product_id in user_history or len(user_history) > 0:
            similar_count = self._count_history_similarity(product_id, user_history, product_info)
            if similar_count > 0:
                reasons.append(self.explanation_templates['history_based'])
                confidence_factors.append(('history', 0.1))

        # Sentiment-based
        sentiment_score = scores.get('sentiment', 0)
        if sentiment_score > 0.6:
            reasons.append(self.explanation_templates['sentiment_positive'])
            confidence_factors.append(('sentiment', 0.1))

        explanation = {
            'product_id': product_id,
            'product_name': product_info.get('name', ''),
            'reasons': reasons[:5],
            'confidence': min(total_score, 1.0),
            'confidence_factors': confidence_factors,
            'final_score': round(total_score, 4)
        }

        return explanation

    def _count_history_similarity(
        self,
        product_id: str,
        user_history: List[str],
        current_product: Dict
    ) -> int:
        """Count how many historical products are similar to current product."""
        count = 0
        current_cat = current_product.get('category', '')
        current_subcat = current_product.get('subcategory', '')

        for hist_id in user_history:
            if (current_cat in hist_id or
                current_subcat in hist_id or
                str(current_cat) in str(hist_id)):
                count += 1

        return count

    def batch_explain(
        self,
        recommendations: List[Tuple[str, float, Dict]],
        products: Dict[str, Dict],
        user_preferences: Dict,
        user_history: List[str]
    ) -> List[Dict]:
        """
        Generate explanations for a batch of recommendations.

        Args:
            recommendations: List of (product_id, score, scores_dict) tuples
            products: Dictionary mapping product_id to product info
            user_preferences: User preference dictionary
            user_history: User interaction history

        Returns:
            List of explanation dictionaries
        """
        explanations = []

        for product_id, total_score, scores in recommendations:
            product_info = products.get(product_id, {})

            explanation = self.generate_explanation(
                product_id=product_id,
                product_info=product_info,
                user_preferences=user_preferences,
                user_history=user_history,
                scores=scores,
                total_score=total_score
            )
            explanations.append(explanation)

        return explanations

    def format_recommendation_response(
        self,
        recommendations_with_explanations: List[Dict]
    ) -> str:
        """
        Format recommendations as a human-readable string.

        Args:
            recommendations_with_explanations: List of explanation dicts

        Returns:
            Formatted string for display
        """
        lines = ["Top Recommendations:\n"]

        for i, rec in enumerate(recommendations_with_explanations, 1):
            name = rec.get('product_name', 'Unknown Product')
            confidence = rec.get('confidence', 0)
            reasons = rec.get('reasons', [])

            lines.append(f"{i}. {name} (Confidence: {confidence:.0%})")
            if reasons:
                for reason in reasons[:3]:
                    lines.append(f"   - {reason}")
            lines.append("")

        return "\n".join(lines)
