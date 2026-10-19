"""Exercise the HTTPS sharing gateway on loopback only; never starts a tunnel.

Requires the normal server on 8012, Node + Playwright, and openssl. TLS verification
is disabled only for this disposable self-signed test origin, never real sharing.
"""
import multiprocessing
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://127.0.0.1:8015'


def serve(code, cert, key):
    import uvicorn
    from prototype.gateway import create_gateway
    uvicorn.run(create_gateway(ORIGIN, 'http://127.0.0.1:8012', code), host='127.0.0.1',
                port=8015, ssl_certfile=cert, ssl_keyfile=key,
                access_log=False, proxy_headers=False, log_level='warning')


def main():
    httpx.get('http://127.0.0.1:8012/api/status', trust_env=False).raise_for_status()
    with socket.socket() as check:
        check.bind(('127.0.0.1', 8015))
    with tempfile.TemporaryDirectory(prefix='ddc-https-test-') as directory:
        directory = Path(directory)
        cert, key, code_file = (directory / name for name in ('cert.pem', 'key.pem', 'code.txt'))
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
                        '-out',str(cert),'-days','1','-subj','/CN=127.0.0.1',
                        '-addext','subjectAltName=IP:127.0.0.1'],check=True,capture_output=True)
        code = secrets.token_urlsafe(18)
        code_file.write_text(code)
        code_file.chmod(0o600)
        process = multiprocessing.get_context('spawn').Process(target=serve, args=(code,str(cert),str(key)))
        process.start()
        try:
            for _ in range(100):
                try:
                    response = httpx.get(ORIGIN+'/__access', verify=False, trust_env=False, timeout=1)
                    if response.status_code == 200:
                        break
                except httpx.RequestError:
                    pass
                if not process.is_alive():
                    raise RuntimeError('Local HTTPS test gateway stopped')
                time.sleep(.1)
            else:
                raise RuntimeError('Local HTTPS test gateway did not start')
            env = dict(os.environ, FIELDNOTE_TEST_URL=ORIGIN, FIELDNOTE_TEST_CODE_FILE=str(code_file),
                       FIELDNOTE_TEST_SELF_SIGNED='1', FIELDNOTE_BROWSER_OUTPUT='../output/sharing-tests')
            subprocess.run([shutil.which('node') or 'node',str(ROOT/'prototype/browser_checks.cjs')],
                           cwd=ROOT, env=env, check=True)
        finally:
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join()


if __name__ == '__main__':
    main()
