"""Save a public book/source URL with a bounded download and SHA-256 receipt.

This downloads data only. It does not assign verified labels or training rights.
Existing files are preserved; receipts support an offline collection audit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def fetch(url, destination, limit=50_000_000):
    destination = Path(destination)
    if urlsplit(url).scheme != 'https':
        raise ValueError('Only HTTPS source URLs are accepted')
    if destination.exists():
        receipt = json.loads(destination.with_suffix(destination.suffix + '.receipt.json').read_text())
        if hashlib.sha256(destination.read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Existing source no longer matches its receipt')
        return receipt
    request = Request(url, headers={'User-Agent': 'DDC-research-book-intake/1.0'})
    with urlopen(request, timeout=45) as response:
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError('Source exceeds collection size limit')
        media_type = response.headers.get('Content-Type', '')
        final_url = response.geturl()
    if destination.suffix.lower() == '.pdf' and not content.startswith(b'%PDF-'):
        raise ValueError('Expected PDF; received another format')
    if destination.suffix.lower() == '.epub' and not content.startswith(b'PK'):
        raise ValueError('Expected EPUB; received another format')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    receipt = {'source_url': url, 'final_url': final_url,
               'retrieved_at': datetime.now(timezone.utc).isoformat(),
               'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
               'content_type': media_type, 'file': str(destination)}
    destination.with_suffix(destination.suffix + '.receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('destination')
    args = parser.parse_args()
    print(json.dumps(fetch(args.url, args.destination), ensure_ascii=False))
