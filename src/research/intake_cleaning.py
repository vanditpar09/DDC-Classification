"""Conservative, auditable text preparation for unreviewed book intake.

These functions never provide labels, references, or permission decisions.
Cleaning preserves Indic combining marks and joiners. Only explicitly identified
metadata is removed; an ordinary number in prose is not a catalog label.
"""
import re
import unicodedata

VERSION = 'book-intake-cleaning-v1'
START = re.compile(r'\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*?\*{3}', re.I)
END = re.compile(r'\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*?\*{3}', re.I)
FULL_LICENSE = re.compile(r'^\s*THE FULL PROJECT GUTENBERG[™®]? LICENSE', re.I)
CALL_FIELD = re.compile(r'^(?:DDC(?:\s+(?:number|classification|class))?|Dewey(?:\s+decimal)?(?:\s+classification)?(?:\s+number)?|Call\s+(?:number|no\.?))\s*[:#-]', re.I)
NUMBER = re.compile(r'(?<![0-9])[0-9]{3}(?:\.[0-9]+)?(?![0-9])')


def prepare_text(raw, excluded_lines=(), pdf=False, gutenberg=False):
    """Return clean Unicode text and an audit; retain the raw input separately."""
    text = unicodedata.normalize('NFC', raw.replace('\r\n', '\n').replace('\r', '\n'))
    audit = {'version': VERSION, 'raw_characters': len(raw),
             'nfc_changed': text != raw, 'removed_regions': [], 'removed_lines': []}
    if gutenberg:
        # Some EPUBs place the complete license in its own spine document.
        if FULL_LICENSE.match(text):
            audit['removed_regions'].append({'reason': 'gutenberg_license_document', 'text': text})
            text = ''
        else:
            start = START.search(text)
            if start:
                audit['removed_regions'].append({'reason': 'gutenberg_pre_start', 'text': text[:start.end()]})
                text = text[start.end():]
            end = END.search(text)
            if end:
                audit['removed_regions'].append({'reason': 'gutenberg_post_end', 'text': text[end.start():]})
                text = text[:end.start()]
    excluded = {unicodedata.normalize('NFC', ' '.join(line.split())).casefold() for line in excluded_lines}
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        line = ' '.join(line.split())
        reason = None
        if line and line.casefold() in excluded:
            reason = 'configured_header_or_footer'
        elif CALL_FIELD.match(line) and NUMBER.search(line):
            reason = 'explicit_catalog_number_field'
        elif pdf and re.fullmatch(r'\d{1,4}', line):
            reason = 'isolated_pdf_page_number'
        if reason:
            audit['removed_lines'].append({'line': number, 'reason': reason, 'text': line})
        else:
            lines.append(line)
    clean = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    audit['clean_characters'] = len(clean)
    return clean, audit


def script_profile(text, language):
    """Script presence is a diagnostic, never a proof of language or OCR quality."""
    letters = [ch for ch in text if ch.isalpha()]
    if language in ('hin', 'mar'):
        matches = sum('\u0900' <= ch <= '\u097f' for ch in letters)
    elif language == 'tam':
        matches = sum('\u0b80' <= ch <= '\u0bff' for ch in letters)
    elif language == 'eng':
        matches = sum('LATIN' in unicodedata.name(ch, '') for ch in letters)
    else:
        raise ValueError('Unsupported intake language')
    return {'letters': len(letters), 'expected_script_letters': matches,
            'expected_script_fraction': matches / len(letters) if letters else None,
            'has_expected_script': matches > 0}
