"""Save reproducible source-based checks, never label OCR as human ground truth."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from pypdf import PdfReader


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def native(text, language):
    text = unicodedata.normalize('NFC', text)
    lower, upper = ('\u0b80', '\u0bff') if language == 'tam' else ('\u0900', '\u097f')
    return ''.join(c for c in text if lower <= c <= upper)


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(corpus, destination):
    corpus, destination = Path(corpus), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    sample_root = destination / 'samples'
    sample_root.mkdir(exist_ok=True)
    inventory = [json.loads(line) for line in (corpus / 'corpus-inventory-v2.jsonl').read_text().splitlines()]
    jobs, reviews = [], []
    for book in inventory:
        folder = sample_root / book['work_id']
        folder.mkdir(exist_ok=True)
        batch = Path(book['batch_root'])
        text_path = batch / book['text_file']
        text = text_path.read_text(encoding='utf-8')
        if hash_file(text_path) != book['text_sha256']:
            raise ValueError('Changed source extraction: ' + str(text_path))
        review = dict(work_id=book['work_id'], group_id=book['group_id'], title=book['title'], author=book['author'],
                      language=book['language'], batch_root=str(batch), source_text_file=str(text_path),
                      source_text_sha256=book['text_sha256'], reviewer='assistant', human_checked=False,
                      text_reference_human_checked=False, verified_section=None, training_eligible=False,
                      proposed_section=book['candidate_ddc_section'], numeric_catalog_evidence=[],
                      label_status='pending independent numeric evidence', identity_status='publisher identity retained; edition matching unresolved',
                      source_notes=book.get('quality_notes', []), missing_provider_parts=book.get('missing_provider_parts', []),
                      native_text_available=book['text_available'], raw_text_sample_candidates=[], source_page_checks=[])
        for number, fraction in enumerate((.25, .5, .75), 1):
            pos=int(len(text)*fraction)
            # Body-region windows remain explicit candidates until semantic review.
            end=min(len(text),pos+2200)
            fragment=text[pos:end]
            path=folder/f'body-window-{number}.txt';path.write_text(fragment,encoding='utf-8')
            review['raw_text_sample_candidates'].append(dict(file=str(path.relative_to(destination)),start_char=pos,end_char=end,
                sha256=hash_file(path),native_characters=len(native(fragment,book['language'])),sample_status='candidate; unverified transcription'))
        if not book['text_available']:
            review['text_status']='extraction unusable; sampled OCR will be stored separately'
        elif book.get('missing_provider_parts'):
            review['text_status']='partial native source; complete-work claim rejected'
        else:
            review['text_status']='candidate native text; source-sample concordance pending'
        for entry in book['source_files']:
            if not entry['file'].endswith('.pdf'):
                continue
            source=batch/entry['file'];reader=PdfReader(source);length=len(reader.pages)
            pages=sorted({max(1,min(length,round(length*f))) for f in (.25,.5,.75)})
            # A nearly empty text-layer page may just be a chapter ending.
            # Do not apply this shortcut to scanned pages with no text layer.
            pages=sorted({min(length,page+1) if 0 < len(reader.pages[page-1].extract_text() or '') < 200 else page for page in pages})
            for page in pages:
                jobs.append((review,source,page,folder))
        reviews.append(review)
    def check(job):
        review,source,page,folder=job
        stem=f'{source.stem}-page-{page}'
        prefix=folder/stem;image=prefix.with_suffix('.png');ocr=prefix.with_suffix('.ocr.txt')
        if not image.exists():
            subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r','130','-singlefile','-png',str(source),str(prefix)],
                           check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
        if not ocr.exists():
            env=dict(os.environ,OMP_THREAD_LIMIT='1')
            process=subprocess.run(['tesseract',str(image),'stdout','--tessdata-dir','models/ocr_tessdata','-l',review['language'],'--psm','3'],
                                   check=True,capture_output=True,text=True,env=env,timeout=120)
            ocr.write_text(process.stdout,encoding='utf-8')
        recognized=ocr.read_text(encoding='utf-8');script=native(recognized,review['language'])
        full=native(Path(review['source_text_file']).read_text(encoding='utf-8'),review['language'])
        # This is an agreement screen, not character error rate or a checked reference.
        shingles={script[i:i+12] for i in range(0,max(0,len(script)-11),4)}
        match=sum(s in full for s in shingles)/max(1,len(shingles))
        check=dict(source_pdf=str(source),page=page,image_file=str(image.relative_to(destination)),image_sha256=hash_file(image),
                   ocr_file=str(ocr.relative_to(destination)),ocr_sha256=hash_file(ocr),ocr_native_characters=len(script),
                   native_12gram_agreement=round(match,4),reference_is_ground_truth=False,
                   status=('insufficient native text; additional body sample needed' if len(script)<100 else 'low text/OCR agreement; inspect font decoding or OCR' if match<.8 else 'text/OCR agreement screen passed; not a verified transcription'))
        return review['work_id'],check
    byid={r['work_id']:r for r in reviews};failures=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for wid,check in pool.map(check,jobs):
            byid[wid]['source_page_checks'].append(check)
            print(json.dumps({'work_id':wid,'page':check['page'],'agreement':check['native_12gram_agreement']},ensure_ascii=False),flush=True)
    for r in reviews:
        if r['native_text_available'] and not r['missing_provider_parts'] and r['source_page_checks']:
            bad=[c for c in r['source_page_checks'] if not c['status'].startswith('text/OCR agreement screen passed')]
            r['text_status']='needs source-fidelity investigation' if bad else 'sampled source agreement; unverified full transcription'
    (destination/'source-reviews.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in reviews),encoding='utf-8')
    summary=dict(generated_at=datetime.now(timezone.utc).isoformat(),titles_reviewed=len(reviews),body_windows_saved=sum(len(r['raw_text_sample_candidates']) for r in reviews),
                 source_page_checks=sum(len(r['source_page_checks']) for r in reviews),text_statuses=dict(Counter(r['text_status'] for r in reviews)),
                 human_checked_references=0,verified_training_books=0,model_retrained=False,
                 agreement_screen_threshold=.8, minimum_native_characters_per_page=100, note='OCR concordance is an agreement screen only. Native-script ratios and OCR do not establish exact text fidelity, identity or labels.')
    write_json(destination/'source-review-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('corpus');p.add_argument('destination');args=p.parse_args();run(args.corpus,args.destination)
