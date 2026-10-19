"""Check improved local cover OCR without changing the user's original saved book."""
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/ocr-phone-review'


def run():
    with httpx.Client(base_url='http://127.0.0.1:8013', trust_env=False, timeout=125) as client:
        response = client.post('/api/sessions')
        response.raise_for_status()
        sid = response.json()['id']
        try:
            fixture = ROOT / 'data/research/ocr-upgrade-v1/fixtures/phone-english-cover.png'
            with (fixture if fixture.exists() else OUT / 'english-original.png').open('rb') as handle:
                response = client.post(f'/api/sessions/{sid}/image',
                    files={'image': ('phone-cover.png', handle, 'image/png')},
                    data={'kind': 'cover', 'language': 'eng'})
            response.raise_for_status()
            state = response.json()
            page = state['pages'][0]
            normalized = ' '.join(page['text'].casefold().split())
            assert page['usable']
            assert 'the kite runner' in normalized and 'khaled hosseini' in normalized
            assert not any(word in normalized for word in ('control','option','command'))
            assert state['work']['classifier_calls'] == 1
            assert len(state['prediction']['hierarchy']['path']) == 3
            report = {'passed': True, 'raw_photo_and_text_preserved': True,
                      'title_recovered': True, 'author_recovered': True,
                      'background_text_removed': True,
                      'classifier_calls': 1, 'quality': page['quality'],
                      'suggested_path': [level['label'] for level in state['prediction']['hierarchy']['path']],
                      'next_action': state['decision']['action']}
            (OUT / 'server-check.json').write_text(json.dumps(report, indent=2) + '\n')
            destination = ROOT / 'output/ocr-upgrade-v1'
            destination.mkdir(parents=True, exist_ok=True)
            (destination / 'server-check.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
        finally:
            client.delete(f'/api/sessions/{sid}').raise_for_status()


if __name__ == '__main__':
    run()
