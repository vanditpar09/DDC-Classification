"""Check saved source hashes and generated EPUBs without accessing the network."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from audit_multilingual_intake import epub


def validate(root):
    root = Path(root)
    records = [json.loads(line) for line in (root / 'collected-books.jsonl').read_text().splitlines()]
    receipts = list(root.rglob('*.receipt.json'))
    errors = []
    for path in receipts:
        receipt = json.loads(path.read_text())
        source = path.with_name(path.name.removesuffix('.receipt.json'))
        if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['sha256']:
            errors.append(str(source))
    if errors:
        raise ValueError('Source hash mismatches: ' + ', '.join(errors))
    books = [r for r in records if r['acquisition_status'] == 'downloaded']
    checks = []
    for record in books:
        if 'derived_epub' not in record:
            continue
        path = root / record['derived_epub']
        metadata, sections = epub(path)
        with ZipFile(path) as archive:
            if archive.namelist()[0] != 'mimetype' or archive.read('mimetype') != b'application/epub+zip':
                raise ValueError('Invalid EPUB mimetype entry: ' + str(path))
            if archive.testzip() is not None:
                raise ValueError('EPUB ZIP integrity failure: ' + str(path))
            for name in archive.namelist():
                if name.endswith(('.opf', '.xml', '.xhtml')):
                    ET.fromstring(archive.read(name))
        if len(sections) != record['provider_parts_expected'] or record['missing_provider_parts']:
            raise ValueError('EPUB does not contain the complete indexed source sequence')
        checks.append({'book': record['work_id'], 'epub_parts': len(sections),
                       'parsed_title': metadata['title'][0], 'parsed_language': metadata['language'][0]})
    result = {'source_receipts_checked': len(receipts), 'hash_mismatches': errors,
        'downloaded_title_count': len(books), 'languages': dict(Counter(r['language'] for r in books)),
        'epub_checks': checks, 'verified_training_count': sum(bool(r['training_eligible']) for r in records),
        'source_books_bytes': sum((root / f['file']).stat().st_size for r in books for f in r['source_files']),
        'unverified_text_available': sum(r['text_available'] for r in books),
        'provisional_group_count': len({r['group_id'] for r in books}),
        'groups_excluding_quarantined_anthology': len({r['group_id'] for r in books
            if 'anthology membership unresolved' not in r['group_resolution_status']})}
    if result['verified_training_count']:
        raise ValueError('This acquisition batch unexpectedly promotes training labels')
    (root / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    validate(parser.parse_args().root)
