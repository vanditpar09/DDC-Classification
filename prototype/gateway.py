"""Password-protected, same-origin proxy for a temporary laptop research session.

Only the gateway is exposed by the tunnel. The model server remains on loopback.
No engine import here: there must be only one model/SQLite serving process.
"""
from collections import deque
from contextlib import asynccontextmanager
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

COOKIE = '__Host-ddc_access'
SESSION_SECONDS = 8 * 60 * 60
MAX_BODY = 13 * 1024 * 1024
LOGIN_PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Book Classification — Access</title>
<style>*{box-sizing:border-box}body{margin:0;padding:24px;background:#f6f7f9;color:#243247;font:16px/1.6 system-ui,sans-serif}main{max-width:420px;margin:12vh auto;background:white;padding:28px;border:1px solid #dce1e8;border-radius:5px}h1{font:28px/1.3 Georgia,serif;margin:0 0 12px}p{font-size:14px;color:#5c6878}label{display:block;font-size:14px}input,button{width:100%;font:inherit;padding:12px;margin-top:8px;border:1px solid #a8b5c5;border-radius:4px}button{background:#263d59;color:white;cursor:pointer;margin-top:16px}.error{color:#9d322b}</style>
<main><h1>Book Classification</h1><p>Enter the access code from the laptop to open the shared research collection.</p>ERROR
<form action="/__access" method="post"><label for="code">Access code</label><input id="code" name="code" type="password" autocomplete="current-password" required maxlength="128"><button>Open collection</button></form>
<p>The laptop must remain awake and connected. Access lasts eight hours.</p></main></html>'''


def create_gateway(public_origin: str, backend: str, access_code: str, *, transport=None):
    """Build an independently testable proxy; transport is injectable for tests."""
    public_origin = public_origin.rstrip('/')
    backend = backend.rstrip('/')
    public, local = urlsplit(public_origin), urlsplit(backend)
    if (public.scheme != 'https' or not public.hostname or public.path or public.query
            or public.fragment or public.username or '*' in public_origin):
        raise ValueError('The public origin must be an exact HTTPS origin')
    if (local.scheme != 'http' or local.hostname not in {'127.0.0.1', 'localhost'}
            or local.path or local.query or local.fragment or local.username):
        raise ValueError('The backend must be an HTTP loopback origin')
    if len(access_code) < 16:
        raise ValueError('Use an access code of at least 16 characters')
    sessions = {}
    attempts = deque()

    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(transport=transport, timeout=125, follow_redirects=False,
                                     trust_env=False) as client:
            app.state.client = client
            yield

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    def logged_in(request):
        token = request.cookies.get(COOKIE, '')
        digest = hashlib.sha256(token.encode()).hexdigest()
        return sessions.get(digest, 0) > time.monotonic()

    @app.middleware('http')
    async def gate(request: Request, call_next):
        if request.headers.get('host', '').lower() != public.netloc.lower():
            response = JSONResponse({'detail': 'Unrecognized host'}, 400)
        elif (request.method not in {'GET', 'HEAD', 'OPTIONS'}
              and request.headers.get('origin') != public_origin):
            response = JSONResponse({'detail': 'Open the shared HTTPS page to submit requests'}, 403)
        elif request.url.path == '/__access':
            response = await call_next(request)
        elif not logged_in(request):
            response = (JSONResponse({'detail': 'Access expired. Sign in again; pending uploads remain on this device.'}, 401)
                        if request.url.path.startswith('/api/') else RedirectResponse('/__access', 303))
        else:
            response = await call_next(request)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'same-origin', 'X-Frame-Options': 'DENY',
                                 'Permissions-Policy': 'camera=(self), microphone=()'})
        return response

    @app.get('/__access')
    async def login_page():
        return HTMLResponse(LOGIN_PAGE.replace('ERROR', ''))

    @app.post('/__access')
    async def login(request: Request):
        now = time.monotonic()
        while attempts and attempts[0] < now - 60:
            attempts.popleft()
        if len(attempts) >= 10:
            return HTMLResponse(LOGIN_PAGE.replace('ERROR', '<p class="error">Too many attempts. Wait a minute and try again.</p>'), 429,
                                headers={'Retry-After': '60'})
        attempts.append(now)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024:
                return JSONResponse({'detail': 'Access form too large'}, 413)
        code = parse_qs(raw.decode('utf-8', errors='replace')).get('code', [''])[0]
        if not hmac.compare_digest(code.encode(), access_code.encode()):
            return HTMLResponse(LOGIN_PAGE.replace('ERROR', '<p class="error">Incorrect access code.</p>'), 401)
        for key, expiry in list(sessions.items()):
            if expiry <= now:
                del sessions[key]
        if len(sessions) >= 100:
            return JSONResponse({'detail': 'Too many active devices. Restart sharing to reset access.'}, 429)
        token = secrets.token_urlsafe(32)
        sessions[hashlib.sha256(token.encode()).hexdigest()] = now + SESSION_SECONDS
        response = RedirectResponse('/', 303)
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, secure=True, httponly=True, samesite='strict', path='/')
        return response

    @app.api_route('/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
    async def proxy(request: Request, path: str):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                return JSONResponse({'detail': 'Request exceeds the image upload limit'}, 413)
        # Explicit header allowlist: never pass the gateway cookie or forwarded host.
        headers = {key: request.headers[key] for key in ('content-type', 'idempotency-key', 'x-book-revision')
                   if key in request.headers}
        if 'origin' in request.headers:
            headers['origin'] = backend
        url = httpx.URL(backend).copy_with(path=request.url.path, query=request.url.query.encode() or None)
        try:
            upstream = await app.state.client.request(request.method, url, content=bytes(body), headers=headers)
        except httpx.TimeoutException:
            return JSONResponse({'detail': 'The laptop is still processing. Retry the pending upload to recover its result.'}, 504)
        except httpx.RequestError:
            return JSONResponse({'detail': 'The laptop server is unavailable. Keep this page open and reconnect.'}, 503)
        outgoing = {key: upstream.headers[key] for key in ('content-type', 'content-disposition') if key in upstream.headers}
        return Response(upstream.content, status_code=upstream.status_code, headers=outgoing)

    return app
