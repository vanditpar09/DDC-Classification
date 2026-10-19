"""Prepare a downloaded batch offline, keeping source text and quality separate.

Requires the document runtime's lxml and pypdf. No verified labels, human
transcription claims, model fitting, or evaluation splits are generated here.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
from lxml import html
from pypdf import PdfReader
from audit_multilingual_intake import PlainText, counts


def plain(fragment):
    parser = PlainText()
    parser.feed(fragment)
    return parser.text()


def html_text(path, language):
    document = html.fromstring(path.read_text(encoding='utf-8-sig'))
    if language == 'hin':
        nodes = document.xpath('//*[@id="ContentPlaceHolder1_lblContentText"]')
        if len(nodes) != 1:
            raise ValueError('Book content element missing or ambiguous')
        raw = plain(html.tostring(nodes[0], encoding='unicode'))
        return raw, raw, 'publisher book-content element'
    bodies = document.xpath('//body')
    raw = plain(html.tostring(bodies[0], encoding='unicode'))
    marker = 'provided this header page is kept intact.'
    match = re.search(re.escape(marker), raw, re.I)
    # Retain unmodified source and extracted source text. This derivative omits
    # the publisher boilerplate; it is not a redistribution of the original.
    content = raw[match.end():].strip() if match else raw
    return raw, content, 'after publisher notice' if match else 'body; header boundary not found'


def make_epub(work, parts, destination):
    """Create a clearly identified derivative of Hindi publisher source parts."""
    uid = 'urn:ddc-intake:' + work['work_id']
    modified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    spine, nav, files = [], [], {}
    for number, text, source in parts:
        name = f'part-{number}.xhtml'
        manifest.append(f'<item id="p{number}" href="{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{number}"/>')
        nav.append(f'<li><a href="{name}">Source part {number}</a></li>')
        paragraphs = '\n'.join(f'<p>{escape(line)}</p>' for line in text.splitlines() if line.strip())
        files[name] = f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="hi"><head><title>Source part {number}</title></head><body>{paragraphs}<p>Source: <a href="{escape(source, quote=True)}">Hindi Samay</a></p></body></html>'
    files['nav.xhtml'] = '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><p>Research derivative from Hindi Samay source pages. Navigation follows publisher web parts, which may each contain several original chapters. It is not a publisher-supplied EPUB.</p><nav epub:type="toc"><ol>' + ''.join(nav) + '</ol></nav></body></html>'
    files['package.opf'] = f'<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{escape(work["title"])}</dc:title><dc:creator>{escape(work["author"])}</dc:creator><dc:language>hi</dc:language><dc:source>{escape(work["catalog_url"])}</dc:source><meta property="dcterms:modified">{modified}</meta></metadata><manifest>{"".join(manifest)}</manifest><spine>{"".join(spine)}</spine></package>'
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, 'w') as archive:
        archive.writestr('mimetype', 'application/epub+zip', compress_type=ZIP_STORED)
        archive.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>', compress_type=ZIP_DEFLATED)
        for name, content in files.items():
            archive.writestr('OEBPS/' + name, content, compress_type=ZIP_DEFLATED)


def prepare(root):
    root = Path(root)
    out = root / 'prepared'
    out.mkdir(exist_ok=True)
    works = json.loads((root / 'selected-works.json').read_text())
    prepared = []
    for work in works:
        item = dict(work)
        item.update({'prepared_at': datetime.now(timezone.utc).isoformat(),
                     'text_reference_human_checked': False,
                     'catalog_overlap_status': 'unresolved; do not use as independent test data',
                     'training_rights_status': 'not established by this download',
                     'distribution_notice_status': 'retain original source notices; review per file',
                     'coverage_status': 'publisher supplied extent; full original-work completeness unverified'})
        existing = [f for f in work['files'] if (root / f['file']).exists()]
        item['source_file_count'] = len(existing)
        item['source_files'] = []
        for f in existing:
            path = root / f['file']
            receipt = json.loads(path.with_suffix(path.suffix + '.receipt.json').read_text())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != receipt['sha256']:
                raise ValueError('Source hash mismatch: ' + str(path))
            item['source_files'].append({**f, 'sha256': digest, 'bytes': path.stat().st_size})
        if not existing:
            item['acquisition_status'] = 'download failed'
            prepared.append(item)
            continue
        item['acquisition_status'] = 'downloaded'
        folder = out / work['work_id']
        folder.mkdir(exist_ok=True)
        html_files = [f for f in existing if f['file'].endswith('.html')]
        text_parts, statuses, candidates = [], [], {}
        for entry in html_files:
            path = root / entry['file']
            raw, text, extraction = html_text(path, work['language'])
            (folder / (path.stem + '.raw.txt')).write_text(raw, encoding='utf-8')
            statuses.append({'file': entry['file'], 'characters': len(text), 'extraction': extraction,
                             'status': 'nonempty' if len(text) >= 500 else 'empty content'})
            number = entry.get('provider_part_number', 1)
            if len(text) >= 500 and (number not in candidates or len(text) > len(candidates[number][0])):
                candidates[number] = (text, entry['source_url'])
        if html_files:
            text_parts = [candidates[n][0] for n in sorted(candidates)]
            item['native_text_source'] = 'publisher HTML; unverified transcription'
            if work['language'] == 'hin':
                expected = set(range(1, work['provider_index_parts'] + 1))
                item['provider_parts_expected'] = len(expected)
                item['provider_parts_nonempty'] = len(candidates)
                item['missing_provider_parts'] = sorted(expected - set(candidates))
                item['coverage_status'] = ('all indexed publisher parts present' if not item['missing_provider_parts'] else 'incomplete source sequence')
                if not item['missing_provider_parts']:
                    epub = root / 'derived-ebooks' / (work['work_id'] + '.epub')
                    make_epub(work, [(n, *candidates[n]) for n in sorted(candidates)], epub)
                    item['derived_epub'] = str(epub.relative_to(root))
        item['html_extraction_status'] = statuses
        pdfs = [f for f in existing if f['file'].endswith('.pdf')]
        item['pdf_diagnostics'] = []
        for entry in pdfs:
            path = root / entry['file']
            reader = PdfReader(path)
            pages, offsets, errors, cursor = [], [], [], 0
            for number, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ''
                except Exception as exc:
                    text = ''
                    errors.append({'page': number, 'error': str(exc)})
                offsets.append({'page': number, 'start': cursor, 'end': cursor + len(text),
                                'characters': len(text), 'scripts': counts(text)})
                pages.append(text)
                cursor += len(text) + 3
            raw = '\n\f\n'.join(pages)
            (folder / (path.stem + '.pdf-extracted.txt')).write_text(raw, encoding='utf-8')
            (folder / (path.stem + '.pages.json')).write_text(json.dumps(offsets, ensure_ascii=False, indent=2) + '\n')
            scripts = counts(raw)
            native = scripts.get('tamil' if work['language'] == 'tam' else 'devanagari', 0)
            ratio = native / max(1, sum(scripts.values()))
            needs_ocr = native < 1000 or ratio < .6 or '/uni0' in raw or '/g8' in raw
            item['pdf_diagnostics'].append({'file': entry['file'], 'pages': len(pages), 'scripts': scripts,
                'native_script_ratio': ratio, 'needs_ocr_or_alternate_text': needs_ocr,
                'extraction_errors': errors, 'reference_human_checked': False})
            if not html_files:
                text_parts.append(raw)
                item['native_text_source'] = 'PDF extraction; OCR required' if needs_ocr else 'PDF extraction; fidelity unverified'
        combined = '\n\f\n'.join(text_parts)
        text_path = folder / 'book-content.txt'
        text_path.write_text(combined, encoding='utf-8')
        item['text_file'] = str(text_path.relative_to(root))
        item['text_characters'] = len(combined)
        item['text_scripts'] = counts(combined)
        item['text_sha256'] = hashlib.sha256(combined.encode()).hexdigest()
        item['text_available'] = bool(candidates) or bool(pdfs and not any(d['needs_ocr_or_alternate_text'] for d in item['pdf_diagnostics']))
        prepared.append(item)
    (root / 'collected-books.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in prepared))
    downloaded = [r for r in prepared if r['acquisition_status'] == 'downloaded']
    summary = {'prepared_at': datetime.now(timezone.utc).isoformat(), 'selected_titles': len(prepared),
        'downloaded_titles': len(downloaded), 'by_language': dict(Counter(r['language'] for r in downloaded)),
        'text_available_unverified': sum(r['text_available'] for r in downloaded),
        'verified_training_books': 0, 'model_retrained': False,
        'derived_hindi_epubs': sum('derived_epub' in r for r in downloaded),
        'failed_titles': [r['work_id'] for r in prepared if r['acquisition_status'] != 'downloaded']}
    (root / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    prepare(parser.parse_args().root)
