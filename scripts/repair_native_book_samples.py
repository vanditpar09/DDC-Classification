"""Recover aligned OCR passages; preserve originals and honest reference status."""
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess

CORPUS = Path('data/research/multilingual-pilot-v1')
REVIEW = CORPUS / 'review-v3'
OUT = CORPUS / 'text-repair-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover(job):
    work, check = job
    folder = OUT / work['work_id']
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"page-{check['page']}"
    image = folder / (stem + '.png')
    text = folder / (stem + '.ocr.txt')
    tsv = folder / (stem + '.tsv')
    if not image.exists():
        subprocess.run(['pdftoppm', '-f', str(check['page']), '-l', str(check['page']),
                        '-r', '240', '-singlefile', '-png', check['source_pdf'], str(folder / stem)],
                       check=True, capture_output=True, timeout=120)
    if not text.exists() or not tsv.exists():
        subprocess.run(['tesseract', str(image), str(folder / stem), '--tessdata-dir',
                        'models/ocr_tessdata', '-l', work['language'], '--psm', '3',
                        '-c', 'tessedit_create_txt=1', '-c', 'tessedit_create_tsv=1'],
                       check=True, capture_output=True, timeout=120, env=dict(os.environ, OMP_THREAD_LIMIT='1'))
        # Tesseract names text output .txt; retain explicit machine provenance.
        (folder / (stem + '.txt')).rename(text)
    words = [r for r in csv.DictReader(io.StringIO(tsv.read_text()), delimiter='\t')
             if r.get('text', '').strip() and float(r['conf']) >= 0]
    scores = [float(r['conf']) for r in words]
    raw = text.read_text()
    lower, upper = ('\u0b80', '\u0bff') if work['language']=='tam' else ('\u0900', '\u097f')
    native = sum(lower <= c <= upper for c in raw)
    return dict(work_id=work['work_id'], page=check['page'], source_pdf=check['source_pdf'],
                source_pdf_sha256=digest(Path(check['source_pdf'])), image_file=str(image), image_sha256=digest(image),
                text_file=str(text), text_sha256=digest(text), tsv_file=str(tsv), tsv_sha256=digest(tsv),
                ocr_language=work['language'], dpi=240, psm=3, native_characters=native,
                median_word_confidence=statistics.median(scores) if scores else 0,
                human_checked=False, reference_is_ground_truth=False,
                diagnostic_usable=native >= 250 and bool(scores) and statistics.median(scores) >= 65,
                note='Machine OCR confidence screens output only; it does not establish transcription accuracy.')


def run():
    OUT.mkdir(exist_ok=True)
    books = list(map(json.loads, (REVIEW / 'reviewed-books.jsonl').read_text().splitlines()))
    selected = [b for b in books if (b['language']=='mar' or b['text_status'].startswith(('needs source', 'extraction unusable')))
                and b['work_id'] not in {'esahity-phakiraa', 'esahity-saichi_vahi'}]
    jobs = [(b, c) for b in selected for c in b['source_page_checks']]
    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(recover, jobs):
            rows.append(row)
            print(json.dumps({k:row[k] for k in ('work_id','page','diagnostic_usable','median_word_confidence')}), flush=True)
    (OUT / 'repaired-pages.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    summary = dict(pages=len(rows), works=len(selected), diagnostic_usable_pages=sum(r['diagnostic_usable'] for r in rows),
                   checked_transcriptions=0, method='240 dpi native-language Tesseract PSM 3; original source and 130 dpi OCR preserved')
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    run()
