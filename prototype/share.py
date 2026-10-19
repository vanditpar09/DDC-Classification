"""Share the running laptop server over authenticated HTTPS using installed ngrok."""
import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import subprocess
import threading
import time

import httpx
import uvicorn
from prototype.gateway import create_gateway


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        if hasattr(os, 'fchmod'):
            os.fchmod(handle.fileno(), 0o600)
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-port', type=int, default=8012)
    parser.add_argument('--port', type=int, default=8014, help='Loopback gateway port')
    args = parser.parse_args()
    if args.port == args.backend_port or not all(1024 <= port <= 65535 for port in (args.port, args.backend_port)):
        parser.error('Use two different ports between 1024 and 65535')
    ngrok = shutil.which('ngrok')
    if not ngrok:
        parser.error('Install ngrok and connect your account before sharing. See docs/LAPTOP_SHARING.md.')
    backend = f'http://127.0.0.1:{args.backend_port}'
    try:
        response = httpx.get(backend + '/api/status', timeout=5, trust_env=False)
        response.raise_for_status()
        if response.json().get('api_version') != 2:
            raise ValueError('Unexpected server version')
    except (httpx.HTTPError, ValueError) as exc:
        parser.error(f'Start the laptop server first: python -m prototype.run --port {args.backend_port} ({type(exc).__name__})')
    # Never point the tunnel at an existing, possibly unprotected service.
    try:
        with socket.socket() as check:
            check.bind(('127.0.0.1', args.port))
    except OSError:
        parser.error(f'Gateway port {args.port} is in use; stop that sharing process or choose --port')
    output = Path(__file__).resolve().parents[1] / 'output' / 'fieldnote'
    code = secrets.token_urlsafe(18)
    private_write(output / 'phone-access.txt', code + '\n')
    lines = queue.Queue()
    process = subprocess.Popen([ngrok, 'http', f'http://127.0.0.1:{args.port}', '--inspect=false',
                                '--log=stdout', '--log-format=json'], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    def reader():
        for line in process.stdout:
            try:
                record = json.loads(line)
                if record.get('url', '').startswith('https://'):
                    lines.put(record['url'])
                elif record.get('lvl') in ('error', 'eror', 'crit'):
                    lines.put(RuntimeError(str(record.get('err') or record.get('msg') or 'Tunnel startup failed')))
            except (ValueError, AttributeError):
                pass
        lines.put(RuntimeError('ngrok stopped before opening a tunnel'))
    threading.Thread(target=reader, daemon=True).start()
    server = None
    try:
        print('Opening an HTTPS tunnel…', flush=True)
        try:
            origin = lines.get(timeout=45)
        except queue.Empty:
            raise RuntimeError('ngrok did not open a tunnel within 45 seconds')
        if isinstance(origin, Exception):
            raise origin
        app = create_gateway(origin, backend, code)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=args.port,
                                               access_log=False, proxy_headers=False, log_level='warning'))
        def watch_tunnel():
            process.wait()
            if server:
                server.should_exit = True
        threading.Thread(target=watch_tunnel, daemon=True).start()
        private_write(output / 'phone-session.json', json.dumps({'url': origin, 'gateway_port': args.port,
                      'backend_port': args.backend_port, 'started_at': time.time()}, indent=2))
        print(f'Phone link: {origin}\nAccess code: {output / "phone-access.txt"}\n'
              'Keep the laptop awake and both terminals running. Ctrl-C closes sharing.', flush=True)
        server.run()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        (output / 'phone-session.json').unlink(missing_ok=True)


if __name__ == '__main__':
    main()
