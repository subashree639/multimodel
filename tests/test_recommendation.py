"""Unit tests: hybrid weights, cold start, explanations, evaluation metrics.

No MongoDB required — all pure-function / in-memory checks.
"""
import sys
sys.path.insert(0, r'C:\Users\Admin\Desktop\MultiModel')

from config import settings
from recommendation.hybrid_recommender import HybridRecommender
from recommendation import evaluation as ev


def _products(n=6):
    out = []
    for i in range(n):
        out.append({
            '_id': f'p{i}',
            'name': f'Product {i} widget gadget',
            'description': f'A useful widget number {i} for home',
            'category': 'appliances' if i % 2 == 0 else 'electronics',
            'subcategory': 'test',
            'features': ['widget', f'feat{i}'],
            'price': 100.0 + i * 10,
            'avg_rating': 4.0 + (i % 3) * 0.3,
            'num_reviews': 10 + i * 5,
        })
    return out


def _reviews():
    return [
        {'user_id': 'u1', 'product_id': 'p0', 'rating': 5},
        {'user_id': 'u1', 'product_id': 'p1', 'rating': 4},
        {'user_id': 'u1', 'product_id': 'p2', 'rating': 2},
        {'user_id': 'u2', 'product_id': 'p0', 'rating': 5},
        {'user_id': 'u2', 'product_id': 'p3', 'rating': 4},
    ]


def test_baseline_weights_unchanged():
    assert settings.COLLABORATIVE_FILTER_WEIGHT == 0.40
    assert settings.CONTENT_BASED_WEIGHT == 0.25
    assert settings.SENTIMENT_WEIGHT == 0.20
    assert settings.SALES_TREND_WEIGHT == 0.15
    r = HybridRecommender()
    assert (r.svd_weight, r.similarity_weight, r.sentiment_weight, r.sales_trend_weight) == (0.40, 0.25, 0.20, 0.15)


def test_hybrid_fit_and_explanations():
    r = HybridRecommender()
    r.fit(_products(), _reviews(), ['p0'])
    assert r.is_fitted
    recs = r.get_recommendations('u1', {}, ['p0'], top_n=3)
    assert len(recs) > 0
    for pid, score, exp in recs:
        assert 0.0 <= score <= 1.0
        assert 'reasons' in exp and 'signals' in exp
        assert set(exp['signals']) == {'collaborative', 'content', 'sentiment', 'trend'}
        assert pid != 'p0'  # history excluded


def test_cold_start_never_empty():
    r = HybridRecommender()
    r.fit(_products(), _reviews(), [])
    recs = r.get_recommendations('new-user-xyz', {}, [], top_n=5)
    assert len(recs) == 5  # popularity fallback fills
    assert all(exp['cold_start'] for _, _, exp in recs)


def test_content_profile_with_preferences_no_crash():
    """Regression: pref vector (5000) vs full matrix (5003) broadcast."""
    r = HybridRecommender()
    r.fit(_products(), _reviews(), [])
    prefs = {'preferred_categories': ['appliances'], 'preferred_features': ['widget']}
    recs = r.get_recommendations('u1', prefs, [], top_n=3)
    assert len(recs) > 0


def test_empty_catalogue_returns_empty_gracefully():
    r = HybridRecommender()
    r.fit([], [], [])
    assert r.get_recommendations('u1', {}, [], top_n=5) == []


def test_evaluation_metrics():
    assert ev.precision_at_k(['a', 'b', 'c'], {'b', 'x'}, 3) == 1 / 3
    assert ev.recall_at_k(['a', 'b', 'c'], {'b', 'x'}, 3) == 0.5
    assert ev.hit_rate_at_k(['a', 'b'], {'x'}, 2) == 0.0
    assert ev.hit_rate_at_k(['a', 'b'], {'b'}, 2) == 1.0
    assert ev.ndcg_at_k(['x', 'y'], {'a'}, 2) == 0.0
    assert ev.ndcg_at_k(['a', 'b'], {'a', 'b'}, 2) == 1.0
    assert ev.average_precision_at_k([], set(), 5) == 0.0


def test_train_test_split_no_leakage():
    reviews = _reviews()
    train, test = ev.train_test_split(reviews, n_holdout=1, seed=1)
    for u, held in test.items():
        for p in held:
            assert not any(str(r.get('user_id')) == u and str(r.get('product_id')) == p for r in train)
