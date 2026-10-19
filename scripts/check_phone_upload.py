"""Check the active phone gateway locally without logging access credentials."""
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def run():
    info = json.loads((ROOT / 'output/fieldnote/phone-session.json').read_text())
    origin = info['url']
    local = f"http://127.0.0.1:{info['gateway_port']}"
    headers = {'Host': httpx.URL(origin).host, 'Origin': origin}
    with httpx.Client(base_url=local, headers=headers, trust_env=False, timeout=125) as client:
        login = client.post('/__access', data={
            'code': (ROOT / 'output/fieldnote/phone-access.txt').read_text().strip()})
        assert login.status_code == 303, f'Gateway login failed ({login.status_code})'
        # The gateway's secure cookie is intentionally sent explicitly for this
        # loopback-only diagnostic. No public HTTP connection is made.
        client.headers['Cookie'] = '__Host-ddc_access=' + login.cookies['__Host-ddc_access']
        response = client.post('/api/sessions')
        response.raise_for_status()
        sid = response.json()['id']
        try:
            image = ROOT / 'prototype/samples/small_text.png'
            with image.open('rb') as handle:
                response = client.post(f'/api/sessions/{sid}/image',
                                       files={'image': (image.name, handle, 'image/png')},
                                       data={'kind': 'cover', 'language': 'eng'})
            result = {'gateway_upload_status': response.status_code}
            if response.is_success:
                state = response.json()
                result['pages_saved'] = len(state['pages'])
                result['ocr_passes'] = state['work']['ocr_passes']
            else:
                result['error'] = response.json()
            print(json.dumps(result, ensure_ascii=False))
            response.raise_for_status()
        finally:
            client.delete(f'/api/sessions/{sid}').raise_for_status()


if __name__ == '__main__':
    run()
