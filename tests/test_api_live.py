"""Live API tests against a running backend (default http://127.0.0.1:8000).

Skipped automatically when the server is unreachable, so `pytest` stays
green in offline environments. Start the backend first for full coverage:
    venv\\Scripts\\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
"""
import io
import json
import os
import socket
import urllib.request
import urllib.error

import pytest

BASE = os.environ.get('TEST_API_BASE', 'http://127.0.0.1:8000')


def _server_up() -> bool:
    try:
        host = BASE.split('://')[1].split(':')[0]
        port = int(BASE.split(':')[-1].split('/')[0])
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _server_up(), reason='backend not running')


def _get(path, timeout=30):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def _post(path, body, timeout=60):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_health():
    s, d = _get('/health')
    assert s == 200 and d['status'] in ('healthy', 'degraded')
    assert d['database'] in ('connected', 'disconnected', 'timeout', 'unavailable')


def test_chat_health():
    s, d = _get('/health/chat')
    assert s == 200 and 'chatbot_ready' in d


def test_products_trending_shape():
    s, d = _get('/api/v1/products/trending?limit=2')
    assert s == 200 and len(d['products']) >= 1
    assert 'id' in d['products'][0]


def test_reco_cold_start_never_empty():
    s, d = _get('/api/v1/recommendations/pytest-guest-xyz?top_n=5')
    assert s == 200
    # Contract: never an unexplained empty list — recs or trending fallback.
    assert len(d['recommendations']) > 0 or len(d.get('trending', [])) > 0
    for r in d['recommendations']:
        assert set(r['explanation']['signals']) == {'collaborative', 'content', 'sentiment', 'trend'}


def test_chat_grounded_no_hallucination():
    s, d = _post('/api/v1/chat/', {'user_id': 'guest', 'message': 'What is the capital of France?'})
    assert s == 200 and d['relevant_products'] == []
    assert 'shopping assistant' in d['response']
    s, d = _post('/api/v1/chat/', {'user_id': 'guest', 'message': 'Tell me the price of Sony PlayStation 99 XYZ that does not exist'})
    assert s == 200 and d['relevant_products'] == []


def test_chat_empty():
    s, d = _post('/api/v1/chat/', {'user_id': 'guest', 'message': ''})
    assert s == 200


def test_images_status_and_invalid_upload():
    s, d = _get('/api/v1/images/status')
    assert s == 200 and d['available'] is True
    import uuid
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="q.png"\r\n'
            f'Content-Type: image/png\r\n\r\n').encode() + b'garbage-bytes' + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(BASE + '/api/v1/images/search', data=body,
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        urllib.request.urlopen(req, timeout=60)
        raise AssertionError('expected 400')
    except urllib.error.HTTPError as e:
        assert e.code == 400
