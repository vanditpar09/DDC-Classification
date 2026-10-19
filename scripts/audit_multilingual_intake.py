"""Inspect the eight-book pilot locally; keep intake separate from reviewed data.

Requires pypdf and Python 3.10+. EPUB parsing uses only the standard library.
No OCR, labels, permissions, or language correctness are inferred automatically.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import logging
from pathlib import Path, PurePosixPath
import re
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile

EXPECTED = {
    'pg1342-images-3.epub': ('Pride and Prejudice', 'Jane Austen', 'eng'),
    'pg1228-images-3.epub': ('On the Origin of Species', 'Charles Darwin', 'eng'),
    'godan_by_premchand.pdf': ('गोदान', 'प्रेमचंद', 'hin'),
    'gandhi-autobiography-hindi.pdf': ('सत्य के प्रयोग अथवा आत्मकथा', 'महात्मा गांधी', 'hin'),
    'shyamachi_aai.pdf': ('श्यामची आई', 'साने गुरुजी', 'mar'),
    'dasbodh_khand_2.pdf': ('दासबोध, खंड २', 'समर्थ रामदास', 'mar'),
    'ponniyin-selvan.pdf': ('பொன்னியின் செல்வன்', 'கல்கி', 'tam'),
    'tolkappiyar.pdf': ('தொல்காப்பியம்', 'தொல்காப்பியர்', 'tam'),
}


def counts(text):
    result = Counter()
    for ch in text:
        if '\u0900' <= ch <= '\u097f':
            result['devanagari'] += 1
        elif '\u0b80' <= ch <= '\u0bff':
            result['tamil'] += 1
        elif ch.isalpha() and 'LATIN' in unicodedata.name(ch, ''):
            result['latin'] += 1
        elif '\ue000' <= ch <= '\uf8ff':
            result['private_use'] += 1
        elif ch == '\ufffd':
            result['replacement'] += 1
    return dict(result)


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return re.sub(r'\n{3,}', '\n\n', ''.join(self.parts)).strip()


def epub(path):
    with ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 300_000_000:
            raise ValueError('EPUB exceeds the uncompressed intake limit')
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        package_path = next(e.attrib['full-path'] for e in container.iter()
                            if e.tag.rsplit('}', 1)[-1] == 'rootfile')
        package = ET.fromstring(archive.read(package_path))
        metadata = {}
        manifest = {}
        spine = []
        for element in package.iter():
            local = element.tag.rsplit('}', 1)[-1]
            if element.tag.startswith('{http://purl.org/dc/elements/1.1/'):
                metadata.setdefault(local, []).append(''.join(element.itertext()).strip())
            if local == 'item':
                manifest[element.attrib['id']] = element.attrib
            elif local == 'itemref':
                spine.append(element.attrib['idref'])
        sections = []
        for item_id in spine:
            item = manifest[item_id]
            if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
                continue
            from urllib.parse import unquote
            href = str(PurePosixPath(package_path).parent / unquote(item['href'].split('#')[0]))
            parser = PlainText()
            parser.feed(archive.read(href).decode('utf-8-sig'))
            sections.append((href, parser.text(), None))
        return metadata, sections


def pdf(path):
    from pypdf import PdfReader
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    reader = PdfReader(path)
    if reader.is_encrypted and not reader.decrypt(''):
        raise ValueError('Encrypted PDF cannot be read without its password')
    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    sections = []
    for number, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ''
            error = None
        except Exception as exc:
            text = ''
            error = f'{type(exc).__name__}: {exc}'
        sections.append((str(number), text, error))
    return metadata, sections


def run(source, output):
    files = sorted(p for p in source.iterdir() if p.suffix.lower() in ('.pdf', '.epub'))
    if not files:
        raise ValueError('No PDF or EPUB files found')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'text').mkdir()
    records = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        title, author, expected_language = EXPECTED.get(path.name, (path.stem, '', None))
        metadata, sections = (pdf if path.suffix.lower() == '.pdf' else epub)(path)
        stem = path.stem
        offset = 0
        index = []
        texts = []
        for ordinal, (identifier, text, error) in enumerate(sections, 1):
            index.append({'ordinal': ordinal, 'source_id': identifier,
                          'start_char': offset, 'chars': len(text),
                          'script_counts': counts(text), 'error': error})
            texts.append(text)
            offset += len(text) + 3  # Separator is newline, form feed, newline.
        joined = '\n\f\n'.join(texts)
        text_path = output / 'text' / f'{stem}.txt'
        text_path.write_text(joined, encoding='utf-8')
        index_path = output / 'text' / f'{stem}.index.jsonl'
        index_path.write_text(''.join(json.dumps(i, ensure_ascii=False) + '\n' for i in index), encoding='utf-8')
        script = counts(joined)
        target_script = {'eng': 'latin', 'hin': 'devanagari', 'mar': 'devanagari', 'tam': 'tamil'}.get(expected_language)
        status = 'text_extracted_needs_review' if target_script and script.get(target_script, 0) >= 100 else 'needs_visual_check_or_ocr'
        record = {
            'file': path.name, 'format': path.suffix[1:].lower(),
            'source_relative_path': str(path.relative_to(source.parent)),
            'source_sha256': digest, 'bytes': path.stat().st_size,
            'expected_title': title, 'expected_author': author,
            'expected_language': expected_language,
            'expectation_basis': 'User-requested collection titles / filenames, not automatic confirmation',
            'embedded_metadata': metadata,
            'pdf_pages' if path.suffix.lower() == '.pdf' else 'epub_spine_documents': len(sections),
            'extracted_chars': len(joined), 'script_counts': script,
            'empty_sections': sum(not text.strip() for _, text, _ in sections),
            'extraction_errors': sum(error is not None for _, _, error in sections),
            'extraction_status': status,
            'extracted_text': str(text_path.relative_to(output)),
            'extracted_text_sha256': hashlib.sha256(text_path.read_bytes()).hexdigest(),
            'section_index': str(index_path.relative_to(output)),
            'review_status': 'pending', 'verified_ddc_section': None,
            'training_eligible': False,
        }
        records.append(record)
        print(json.dumps({k: record[k] for k in ('file', 'extracted_chars', 'script_counts', 'extraction_status')}, ensure_ascii=False), flush=True)
    report = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
              'source_directory': str(source.resolve()), 'books': records,
              'note': 'Unreviewed intake only. Extraction/script counts do not verify language, rights, DDC labels, or OCR accuracy. No fitting or partitioning performed.'}
    (output / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.source, args.output)
