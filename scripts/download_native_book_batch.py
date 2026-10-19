"""Download only the explicit file list in a saved book collection manifest."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from fetch_native_book_source import fetch


def run(root):
    root = Path(root)
    works = json.loads((root / 'selected-works.json').read_text())
    jobs = [entry for work in works for entry in work['files']]
    def download(entry):
        try:
            return {'file': entry['file'], 'status': 'downloaded',
                    'receipt': fetch(entry['source_url'], root / entry['file'])}
        except Exception as exc:
            return {'file': entry['file'], 'source_url': entry['source_url'],
                    'status': 'failed', 'error': str(exc)}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(download, jobs))
    (root / 'download-results.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'downloaded': sum(r['status'] == 'downloaded' for r in results),
                      'failed': [r for r in results if r['status'] != 'downloaded']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    run(parser.parse_args().root)
