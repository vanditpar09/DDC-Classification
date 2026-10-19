"""Verify the sharing boundary without exposing a real tunnel or model."""
import httpx
import pytest
from fastapi.testclient import TestClient
from prototype.gateway import COOKIE, create_gateway

ORIGIN = 'https://research.example.test'
CODE = 'test-only-access-code-12345'


def make_client(handler=None):
    handler = handler or (lambda request: httpx.Response(200, json={'ok': True}))
    return TestClient(create_gateway(ORIGIN, 'http://127.0.0.1:8012', CODE,
                                     transport=httpx.MockTransport(handler)), base_url=ORIGIN, follow_redirects=False)


def login(client):
    return client.post('/__access', data={'code': CODE}, headers={'Origin': ORIGIN})


@pytest.mark.parametrize('path', ['/api/status', '/api/sessions', '/api/sessions/book/export', '/api/sessions/book/pages/page/image'])
def test_all_research_data_requires_access(path):
    with make_client() as client:
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers['cache-control'] == 'no-store'


def test_assets_redirect_to_access_and_wrong_code_fails():
    with make_client() as client:
        for path in ['/', '/app.js', '/samples/small_text.png', '/sw.js', '/docs']:
            assert client.get(path).headers['location'] == '/__access'
        assert client.get('/__access').status_code == 200
        assert client.post('/__access', data={'code': 'wrong'}, headers={'Origin': ORIGIN}).status_code == 401
        assert client.get('/api/sessions').status_code == 401


def test_cookie_and_proxy_preserve_operation_identity_without_forwarding_secrets():
    captured = []
    def backend(request):
        captured.append(request)
        return httpx.Response(200, json={'revision': 2}, headers={'Content-Disposition': 'attachment; filename="record.json"'})
    with make_client(backend) as client:
        response = login(client)
        assert response.status_code == 303
        cookie = response.headers['set-cookie']
        assert all(flag in cookie for flag in ('HttpOnly', 'Secure', 'SameSite=strict', 'Path=/'))
        assert client.cookies.get(COOKIE)
        result = client.post('/api/sessions/book/text', json={'text': 'कंप्यूटर'}, headers={
            'Origin': ORIGIN, 'Idempotency-Key': 'operation123', 'X-Book-Revision': '1',
            'Authorization': 'do-not-forward', 'X-Forwarded-Host': 'evil.example'})
        assert result.json()['revision'] == 2
        sent = captured[0]
        assert sent.url == 'http://127.0.0.1:8012/api/sessions/book/text'
        assert sent.headers['origin'] == 'http://127.0.0.1:8012'
        assert sent.headers['idempotency-key'] == 'operation123'
        assert sent.headers['x-book-revision'] == '1'
        assert 'cookie' not in sent.headers and 'authorization' not in sent.headers
        assert 'x-forwarded-host' not in sent.headers
        assert 'कंप्यूटर' in sent.content.decode()
        assert result.headers['content-disposition'].startswith('attachment')
        assert result.headers['permissions-policy'] == 'camera=(self), microphone=()'


def test_foreign_origin_host_and_missing_origin_rejected():
    with make_client() as client:
        login(client)
        assert client.post('/api/sessions', headers={'Origin': 'https://evil.example'}).status_code == 403
        assert client.post('/api/sessions').status_code == 403
        assert client.get('/', headers={'Host': 'evil.example'}).status_code == 400
        assert client.post('/__access', data={'code': CODE}, headers={'Origin': 'https://evil.example'}).status_code == 403


def test_invalid_cookie_and_expired_session(monkeypatch):
    with make_client() as client:
        login(client)
        assert client.get('/api/status').status_code == 200
        import prototype.gateway as gateway
        now = gateway.time.monotonic()
        monkeypatch.setattr(gateway.time, 'monotonic', lambda: now + gateway.SESSION_SECONDS + 1)
        assert client.get('/api/status').status_code == 401
    with make_client() as client:
        client.cookies.set(COOKIE, 'forged')
        assert client.get('/api/status').status_code == 401


def test_login_rate_and_size_limits():
    with make_client() as client:
        assert client.post('/__access', content=b'x'*1025, headers={'Origin': ORIGIN}).status_code == 413
        for _ in range(9):
            assert client.post('/__access', data={'code':'bad'}, headers={'Origin':ORIGIN}).status_code == 401
        assert login(client).status_code == 429


def test_upload_body_limit():
    with make_client() as client:
        login(client)
        assert client.post('/api/sessions/book/image', content=b'x'*(13*1024*1024+1), headers={'Origin':ORIGIN}).status_code == 413


@pytest.mark.parametrize('error,code', [(httpx.ConnectError,503),(httpx.ReadTimeout,504)])
def test_upstream_outage(error,code):
    def backend(request):
        raise error('unavailable', request=request)
    with make_client(backend) as client:
        login(client)
        assert client.get('/api/status').status_code == code


@pytest.mark.parametrize('origin,backend', [('http://research.test','http://127.0.0.1:8012'),
    ('https://research.test/path','http://127.0.0.1:8012'),(ORIGIN,'http://remote.example'),
    (ORIGIN,'http://127.0.0.1:8012/path')])
def test_exact_origins_and_loopback_only(origin,backend):
    with pytest.raises(ValueError):
        create_gateway(origin,backend,CODE)
