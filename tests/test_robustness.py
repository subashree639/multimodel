"""Robustness unit tests: images, FAISS-empty, aspects, NLP fallback.

No MongoDB / no torch required.
"""
import io
import sys
sys.path.insert(0, r'C:\Users\Admin\Desktop\MultiModel')

from PIL import Image


def _img_bytes(fmt='PNG', color=(10, 200, 30)):
    buf = io.BytesIO()
    Image.new('RGB', (64, 64), color).save(buf, format=fmt)
    return buf.getvalue()


def test_image_validation_rejects_non_image():
    from fastapi import HTTPException
    import api.images as im
    from fastapi import UploadFile
    import asyncio

    async def _run(raw, ctype):
        from starlette.datastructures import Headers
        f = UploadFile(
            file=io.BytesIO(raw),
            filename='x.bin',
            headers=Headers({'content-type': ctype}),
        )
        try:
            im._validate_upload(f, raw)
            return 'ok'
        except HTTPException as e:
            return e.status_code

    assert asyncio.run(_run(b'', 'image/png')) == 400
    assert asyncio.run(_run(b'not-an-image', 'image/png')) == 400
    assert asyncio.run(_run(b'abc', 'text/plain')) == 400
    assert asyncio.run(_run(_img_bytes(), 'image/png')) is not None


def test_faiss_empty_search_returns_empty():
    from computer_vision.similarity_search import SimilaritySearch
    s = SimilaritySearch(embedding_dim=8)
    import numpy as np
    assert s.search(np.zeros(8, dtype='float32'), top_k=5) == []
    assert s.load_index() is False  # missing files handled


def test_aspect_detection_covers_required_aspects():
    from nlp.aspect_extraction import detect_aspects, aggregate_aspect_profile
    found = detect_aspects('Battery life is great but delivery was slow and price is high.')
    assert 'battery' in found and 'delivery' in found and 'price' in found
    prof = aggregate_aspect_profile([
        {'aspect_sentiments': {'battery': {'positive': 0.9, 'negative': 0.05, 'neutral': 0.05}}},
        {'aspect_sentiments': {'battery': {'positive': 0.7, 'negative': 0.2, 'neutral': 0.1}}},
    ])
    assert prof['battery']['count'] == 2
    assert prof['battery']['dominant'] == 'positive'


def test_sentiment_never_raises():
    from nlp.sentiment_analysis import SentimentAnalyzer
    a = SentimentAnalyzer.__new__(SentimentAnalyzer)
    a.classifier = None
    assert set(a.analyze('great product').keys()) == {'positive', 'negative', 'neutral'}
    assert a.analyze('') == {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
