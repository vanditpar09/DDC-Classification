"""Prepare a separate assistant-labelled experiment; never promote gold data.

Run with the bundled document Python after acquisition and OCR repair. Source
snapshots stay untouched. The ML trainer consumes only this explicit silver set.
"""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import argparse
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.research.intake_cleaning import prepare_text, script_profile
from repair_native_book_samples import recover

CORPUS = Path('data/research/multilingual-pilot-v1')
OUT = CORPUS / 'silver-pilot-v1'
HOLD = {
    'pm-work-55': 'Prosody/grammar boundary unresolved',
    'pm-work-145': 'Rhetoric/grammar boundary unresolved',
    'pm-work-263': 'Prosody/grammar boundary unresolved',
    'pm-work-410': 'Poetics boundary and unreadable source passages',
    'pm-work-695': 'Prosody/grammar boundary unresolved',
    'pm-work-295': '494 versus 894 numeric conflict',
    'pm-work-301': '494 versus 894 numeric conflict',
    'pm-work-718': 'Source begins at chapter 17; edition extent unresolved',
    'hindisamay-v2-1232': 'Missing publisher part 3',
    'esahity-phakiraa': 'Anthology membership unresolved',
    'esahity-saichi_vahi': 'Unreadable stylized OCR',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample(work, raw, provenance, number):
    headers = [work['title'], work['author'], work['title'] + ' ' + work['author']]
    clean, audit = prepare_text(raw, excluded_lines=headers, pdf=True)
    if len(clean) < 350 or (script_profile(clean, work['language'])['expected_script_fraction'] or 0) < .5:
        return None
    path = OUT / 'texts' / work['work_id'] / f'passage-{number}.txt'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean)
    return dict(text_file=str(path), text_sha256=sha(path), provenance=provenance,
                text_origin=provenance['method'], cleaning_audit=audit,
                human_checked=False, reference_is_ground_truth=False)


def run(destination=OUT, followup=False):
    global OUT
    OUT=Path(destination)
    OUT.mkdir(parents=True, exist_ok=False)
    reviewed = list(map(json.loads, (CORPUS/'review-v3/reviewed-books.jsonl').read_text().splitlines()))
    repaired = list(map(json.loads, (CORPUS/'text-repair-v1/repaired-pages.jsonl').read_text().splitlines()))
    bywork = defaultdict(list)
    for row in repaired:
        bywork[row['work_id']].append(row)
    books, exclusions, jobs = [], [], []
    for b in reviewed:
        wid=b['work_id']
        if wid in HOLD or b.get('prior_catalog_candidate_hits'):
            exclusions.append(dict(work_id=wid, reason=HOLD.get(wid,'Possible previous catalog overlap')))
            continue
        samples=[]
        if wid in bywork:
            for r in bywork[wid]:
                if not r['diagnostic_usable']:
                    continue
                raw=Path(r['text_file']).read_text()
                if sha(Path(r['text_file'])) != r['text_sha256']:
                    raise ValueError('Changed OCR')
                p=sample(b,raw,dict(method='machine_ocr_240dpi', **r),len(samples)+1)
                if p:samples.append(p)
        else:
            for w in b['raw_text_sample_candidates']:
                path=CORPUS/'review-v3'/w['file']
                if sha(path)!=w['sha256']:raise ValueError('Changed source window')
                p=sample(b,path.read_text(),dict(method='publisher_native_text', source_file=str(path), source_sha256=w['sha256'],
                         original_text_file=b['source_text_file'], original_text_sha256=b['source_text_sha256'],
                         start_char=w['start_char'],end_char=w['end_char']),len(samples)+1)
                if p:samples.append(p)
        if not samples:
            exclusions.append(dict(work_id=wid, reason='No passage passed text diagnostics'));continue
        books.append(dict(work_id=wid,group_id=b['group_id'],title=b['title'],author=b['author'],language=b['language'],
                          silver_section=b['assistant_reviewed_section'],label_evidence=b['label_evidence'],
                          label_status=b['label_status'],samples=samples, source_extent='Body passages from saved digital edition',
                          verified_section=None,human_checked=False,verified_benchmark_eligible=False,
                          experimental_eligible=True,reviewer='assistant', rights_status='Source-use status remains unestablished'))
    root=CORPUS/'acquisition-v3'
    ncert=json.loads((root/'selected-works.json').read_text())
    if followup:
        extra=CORPUS/'acquisition-v4'
        for b in json.loads((extra/'selected-works.json').read_text()):
            for f in b['files']:f['file']=str(Path('../acquisition-v4')/f['file'])
            ncert.append(b)
    for b in ncert:
        if b.get('label_hold'):
            exclusions.append(dict(work_id=b['work_id'],reason='Physical geography crosses 550/910; hold pending adjudication'));continue
        if any(not (root/f['file']).exists() for f in b['files']):
            exclusions.append(dict(work_id=b['work_id'],reason='Missing selected NCERT source file'));continue
        for f in b['files']:
            path=root/f['file'];receipt=json.loads(path.with_suffix('.pdf.receipt.json').read_text())
            if sha(path)!=receipt['sha256']:raise ValueError('Changed NCERT source')
            if f['chapter']==0:continue
            reader=PdfReader(path)
            page=max(1,round(len(reader.pages)*.5))
            jobs.append((b,dict(page=page,source_pdf=str(path)),f['chapter']))
    def ocr(job):
        b,c,chapter=job
        # Distinct chapter directories prevent collisions between page numbers.
        work=dict(b,work_id=b['work_id']+f'-chapter-{chapter}')
        row=recover((work,c))
        return b, row
    recovered=defaultdict(list)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for b,row in pool.map(ocr,jobs):
            recovered[b['work_id']].append(row)
            print(json.dumps(dict(work_id=b['work_id'],page=row['page'],native=row['native_characters'])),flush=True)
    (OUT/'ncert-ocr-pages.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for rows in recovered.values() for r in rows))
    for b in ncert:
        if b['work_id'] not in recovered:continue
        samples=[]
        for row in recovered[b['work_id']]:
            if row['native_characters']<100 or row['median_word_confidence']<65:continue
            p=sample(b,Path(row['text_file']).read_text(),dict(method='machine_ocr_240dpi',**row),len(samples)+1)
            if p:samples.append(p)
        if not samples:
            exclusions.append(dict(work_id=b['work_id'],reason='NCERT passages failed diagnostics'));continue
        books.append(dict(work_id=b['work_id'],group_id=b['group_id'],title=b['title'],author=b['author'],language=b['language'],
                          silver_section=b['candidate_ddc_section'],label_evidence=[dict(url=b['catalog_url'],subject=b['subject'],scope=b['label_basis'])],
                          label_status='Assistant subject mapping; no exact numeric catalog match',samples=samples,source_extent=b['coverage_status'],
                          verified_section=None,human_checked=False,verified_benchmark_eligible=False,experimental_eligible=True,reviewer='assistant',
                          rights_status=b['training_rights_status']))
    # Hold whole work groups together, including different-language textbooks.
    groups=defaultdict(list)
    for b in books:groups[b['group_id']].append(b)
    strata=defaultdict(list)
    for gid,rows in groups.items():
        labels={r['silver_section'] for r in rows}
        if len(labels)!=1:raise ValueError('Conflicting labels in original-work group')
        strata[next(iter(labels))].append(gid)
    assignment={}
    for section,gids in sorted(strata.items()):
        gids=sorted(gids,key=lambda g:hashlib.sha256(('silver-pilot-v1:'+g).encode()).hexdigest())
        # Preserve the existing five-work support rule. Tiny classes have no
        # independent fine evaluation; the report explicitly identifies them.
        if section in {'891','894','494'}:
            test=1 if len(gids)>=8 else 0
            dev=max(1,int(len(gids)*.2)) if len(gids)>=6 else 0
            dev=min(dev,max(0,len(gids)-5-test))
        else:
            # Other sections also receive support from the original catalog.
            test=1 if len(gids)>=3 else 0
            dev=1 if len(gids)>=3 else 0
        for i,gid in enumerate(gids):
            assignment[gid]='test' if i<test else 'development' if i<test+dev else 'train'
    for b in books:b['assigned_partition']=assignment[b['group_id']]
    if followup:
        previous=list(map(json.loads,(CORPUS/'silver-pilot-v1/books.jsonl').read_text().splitlines()))
        protected={b['group_id']:b['assigned_partition'] for b in previous if b['assigned_partition']!='train'}
        # Preserve every earlier development and locked-test group. Address
        # deficient language coverage by moving train groups OUT of fitting.
        for b in books:
            if b['group_id'] in protected:b['assigned_partition']=protected[b['group_id']]
        marathi=sorted({b['group_id'] for b in books if b['language']=='mar' and b['silver_section']=='891' and b['assigned_partition']=='train'})[:3]
        for b in books:
            if b['group_id'] in marathi:b['assigned_partition']='development'
            if b['work_id'] in {'ncert-ihmh1','ncert-jhmh1'}:b['assigned_partition']='train'
        # The new split is for continued development, not a fresh final test.
        assignment={b['group_id']:b['assigned_partition'] for b in books}
    (OUT/'books.jsonl').write_text(''.join(json.dumps(b,ensure_ascii=False)+'\n' for b in books))
    (OUT/'excluded-books.json').write_text(json.dumps(exclusions,ensure_ascii=False,indent=2)+'\n')
    summary=dict(edition_samples=len(books),provisional_work_groups=len(groups),passages=sum(len(b['samples']) for b in books),
                 by_language=dict(Counter(b['language'] for b in books)),by_section=dict(Counter(b['silver_section'] for b in books)),
                 group_partitions=dict(Counter(assignment.values())),exclusions=exclusions,
                 support_policy='At least five native training work groups where feasible; sparse sections use existing catalog support or fall back',
                 gold_labels=0,checked_transcriptions=0,final_test_evaluated=False,
                 warning='Silver-label clean-body experiment. Source confidence is not accuracy. Provisional grouping cannot prove independence. No camera accuracy or patent finding.')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    manifest={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,default=OUT);p.add_argument('--followup',action='store_true')
    a=p.parse_args();run(a.output_dir,a.followup)
