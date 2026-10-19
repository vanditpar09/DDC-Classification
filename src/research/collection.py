"""Prepare reviewed native-language books without silently inventing labels.

JSONL is one edition per row. Work IDs group editions and translations together.
The collection lives under ignored output/; templates contain no ground truth.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from src.ddc_data.load_data import load_data
from src.ocr_pipeline.hierarchy import fine_label
from src.ocr_pipeline.train_improved import make_splits

ROOT = Path(__file__).resolve().parents[2]
LANGUAGES = ('eng', 'hin', 'mar', 'tam')
KINDS = ('cover', 'back_cover', 'contents')
PARTITIONS = ('train', 'development', 'calibration', 'test')


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def catalog_alias(value):
    value=value.strip()
    work=re.fullmatch(r'(?:https?://openlibrary\.org/(?:works|books)/)?(OL[0-9]+[WM])/?',value,re.I)
    if work:return work[1].upper()
    isbn=re.sub(r'[ -]','',value).upper()
    if re.fullmatch(r'(?:[0-9]{9}[0-9X]|[0-9]{13})',isbn):return isbn
    return value


def known_catalog():
    records = load_data()['records']
    splits = make_splits(records)
    index = {}
    for split, indices in splits.items():
        for i in indices:
            row = records[i]
            identifiers = [row['document_id'], row['split_group_id'], *row.get('source_work_ids', []), *row.get('edition_ids', []), *row.get('isbns', [])]
            for identifier in identifiers:
                index.setdefault(catalog_alias(identifier), set()).add(split)
    return records, index


def audit_catalog():
    rows, _ = known_catalog()
    return {
        'dataset_sha256': hashlib.sha256((ROOT/'data/books.jsonl').read_bytes()).hexdigest(),
        'books': len(rows), 'explicit_language_rows': sum(bool(r.get('language') or r.get('languages')) for r in rows),
        'native_script_title_counts': {
            'devanagari': sum(any('\u0900' <= c <= '\u097f' for c in r['title']) for r in rows),
            'tamil': sum(any('\u0b80' <= c <= '\u0bff' for c in r['title']) for r in rows)},
        'review_status': dict(Counter(r.get('review_status', 'missing') for r in rows)),
        'label_eligibility': {str(level): sum(fine_label(r,level) is not None for r in rows) for level in (2,3)},
        'note': 'Script counts are diagnostics, not language identification. Native-language DDC accuracy is unmeasured.'}


def init_collection(output):
    output.mkdir(parents=True, exist_ok=False)
    (output/'images').mkdir()
    template = []
    for language in LANGUAGES:
        for broad in range(10):
            for slot in range(2):
                template.append({'collection_slot': f'{language}-{broad}00-{slot+1}',
                    'desired_class': f'{broad}00', 'book_id':'', 'work_id':'', 'catalog_ids':[],
                    'language':language, 'title':'', 'review_status':'pending', 'section':'',
                    'reviewer':'', 'label_source':'', 'capture_permission':False, 'pages':[
                        {'kind':kind, 'origin':'native_scan', 'image_path':'', 'reference_text':'', 'ocr_text':''}
                        for kind in KINDS]})
    (output/'collection-template.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in template),encoding='utf-8')
    write_json(output/'catalog-audit.json', audit_catalog())
    (output/'README.md').write_text('''# Private multilingual collection

Start with 20 distinct works per language (80 total), two requested books in each
broad class. Desired class is a collection target; it is never the verified label.
This is a feasibility pilot, too small for precise per-section accuracy claims.
If a subject is unavailable, record the gap rather than forcing a class.

Copy completed rows to `reviewed.jsonl`; leave incomplete template rows out.
Use stable edition/accession/ISBN as book_id and ONE work_id for all editions,
photos and translations of the same work. Resolve related works using source and catalog evidence
before partitioning. List known Open Library work/edition IDs or ISBNs in catalog_ids.
Use the language of this edition, not the language named in its subject.

For each page save its permitted photo under images/ and use a relative path.
Record a faithful, manually checked native-script reference_text and raw OCR text
separately. Do not fix raw OCR silently. Human transcription without a photo uses
origin=human_transcription and an empty image_path; it cannot measure camera/OCR.
Machine translations and authored examples cannot enter the native-book benchmark.

A reviewer must set review_status=verified, section to the actual three-digit
DDC code, reviewer, and label_source (catalog entry/accession/source used to verify
that label). Record the actual reviewer; a librarian is helpful but not required.
Assistant proposals and machine OCR must not be described as human-checked
ground truth. Keep leading zeros. Mark capture_permission=true only once confirmed.
Broad/division targets are derived from that reviewed section. Do not copy model
predictions into these fields. Reviewers should label without seeing predictions.

Run prepare on reviewed.jsonl to freeze work-level train/development/calibration/
test assignments. Keep the frozen prepared dataset unchanged for comparison.
The existing catalog's previously seen books cannot become an independent test.
All crops, OCR variants, translations and editions remain in their work partition.

The pilot identifies errors. Expand priority sections to at least 20-30 distinct
training works per language/section, plus separate development/calibration works.
Collect a new real-scan test cohort before claiming language accuracy.
''',encoding='utf-8')
    return {'output':str(output),'collection_slots':len(template),'languages':list(LANGUAGES)}


def validate_records(rows, root):
    if not rows:
        raise ValueError('No reviewed books supplied')
    seen_books, images, content_groups = set(), {}, {}
    aliases = {}
    for row in rows:
        for field in ('book_id','work_id','title','reviewer','label_source'):
            if not isinstance(row.get(field),str) or not row[field].strip():
                raise ValueError(f'Missing {field} in a reviewed book')
        book, group = row['book_id'], row['work_id']
        if book!=book.strip() or group!=group.strip():
            raise ValueError('Book/work IDs must not have surrounding whitespace')
        if catalog_alias(book) in seen_books:
            raise ValueError(f'Duplicate edition/book ID: {book}')
        seen_books.add(catalog_alias(book))
        if row.get('language') not in LANGUAGES or row.get('review_status') != 'verified':
            raise ValueError(f'{book}: supported language and verified review required')
        if not isinstance(row.get('section'),str) or not re.fullmatch(r'[0-9]{3}',row['section']):
            raise ValueError(f'{book}: section must be a three-digit string')
        if row.get('capture_permission') is not True:
            raise ValueError(f'{book}: capture permission must be confirmed')
        ids = row.get('catalog_ids',[])
        if not isinstance(ids,list) or any(not isinstance(i,str) or not i.strip() for i in ids):
            raise ValueError(f'{book}: catalog_ids must be an array of identifiers')
        # A shared known identifier cannot be hidden behind two claimed work IDs.
        for identifier in [book,*ids]:
            identifier=catalog_alias(identifier)
            if identifier in aliases and aliases[identifier] != group:
                raise ValueError(f'{book}: related catalog identifiers have conflicting work IDs')
            aliases[identifier] = group
        pages = row.get('pages')
        if not isinstance(pages,list) or not pages or len(pages)>3:
            raise ValueError(f'{book}: supply one to three current pages')
        kinds = set()
        for page in pages:
            kind = page.get('kind')
            if kind not in KINDS or kind in kinds:
                raise ValueError(f'{book}: invalid or repeated page type')
            kinds.add(kind)
            if page.get('origin') not in {'native_scan','human_transcription'}:
                raise ValueError(f'{book}: only native scans/transcriptions qualify')
            reference, ocr = page.get('reference_text'),page.get('ocr_text')
            if not isinstance(reference,str) or not isinstance(ocr,str) or not reference.strip():
                raise ValueError(f'{book}: each page needs checked reference_text and a string ocr_text')
            if len(reference)>50000 or len(ocr)>50000:
                raise ValueError(f'{book}: page text exceeds collection limit')
            fingerprint = hashlib.sha256(reference.strip().encode()).hexdigest()
            if len(reference.strip()) >= 80:
                if fingerprint in content_groups and content_groups[fingerprint] != group:
                    raise ValueError(f'{book}: identical page text in different work groups; resolve duplicates')
                content_groups[fingerprint]=group
            image = page.get('image_path','')
            if page['origin']=='native_scan' and not image:
                raise ValueError(f'{book}: a native scan needs an image file')
            if not isinstance(image,str):
                raise ValueError(f'{book}: image_path must be a relative path string')
            if image:
                if Path(image).is_absolute():
                    raise ValueError(f'{book}: image must be an existing file within the collection')
                target = (root/image).resolve()
                if not target.is_relative_to(root.resolve()) or not target.is_file():
                    raise ValueError(f'{book}: image must be an existing file within the collection')
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                if digest in images and images[digest] != group:
                    raise ValueError(f'{book}: same image occurs in different work groups')
                images[digest]=group
                page['image_sha256']=digest
    return rows


def assign_partition(group):
    bucket = int(hashlib.sha256(('ddc-native-v1:'+group).encode()).hexdigest()[:8],16)%100
    return 'train' if bucket<60 else 'development' if bucket<80 else 'calibration' if bucket<90 else 'test'


def prepare(source, output):
    _, index = known_catalog()
    rows = validate_records(read_jsonl(source), source.parent)
    groups = defaultdict(list)
    for row in rows:
        groups[row['work_id']].append(row)
    partitions = {}
    for group, members in groups.items():
        known = {split for r in members for identifier in [r['book_id'],r['work_id'],*r.get('catalog_ids',[])] for split in index.get(catalog_alias(identifier),set())}
        # Known held-out books can be inspected on development only; no fitting.
        partition = 'development' if known else assign_partition(group)
        partitions[group]=partition
        for row in members:
            row['partition']=partition
            row['prior_catalog_memberships']=sorted(known)
    output.mkdir(parents=True, exist_ok=False)
    destination=output/'books.jsonl'
    destination.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    report={'schema_version':1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'prepared_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
        'image_root':str(source.parent.resolve()), 'work_assignments':partitions,
        'books':len(rows),'work_groups':len(groups),
        'by_partition':dict(Counter(r['partition'] for r in rows)),
        'by_language_partition':dict(Counter(r['language']+':'+r['partition'] for r in rows)),
        'note':'Hash partitions are work-grouped, not stratified. Known catalog works go only to development; inspect coverage before training. Human deduplication must also link translations with different catalog IDs.'}
    write_json(output/'manifest.json',report)
    # Training schema excludes evaluation groups and never inserts OCR/label metadata into input prose.
    training=[]
    for row in rows:
        if row['partition'] not in {'train','calibration'}:
            continue
        training.append({'document_id':row['book_id'],'split_group_id':row['work_id'],
            'language':row['language'],'label_level_1':row['section'][0]+'00','ddc_raw':[row['section']],
            'title':row['title'],'subtitle':'','raw_text':'\n'.join(p['reference_text'] for p in row['pages']),
            'assigned_partition':row['partition'],'review_status':'verified',
            'note':'Use assigned_partition in a reviewed-data trainer; the legacy make_splits must not repartition this file.'})
    (output/'training-input.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in training),encoding='utf-8')
    write_json(output/'training-readiness.json',{'distinct_training_works_per_language_section':dict(sorted(Counter(
        f"{lang}:{section}" for lang,section,group in {(r['language'],r['section'],r['work_id']) for r in rows if r['partition']=='train'}).items())),
        'minimum_current_head_support':5,'note':'Counts identify data gaps; more views of one work do not increase support. New heads and calibration still require a separate training experiment.'})
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--output-dir',type=Path,required=True)
    audit=sub.add_parser('audit');audit.add_argument('--output',type=Path,required=True)
    prep=sub.add_parser('prepare');prep.add_argument('source',type=Path);prep.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='init':
        result=init_collection(args.output_dir)
    elif args.command=='prepare':
        result=prepare(args.source,args.output_dir)
    else:
        result=audit_catalog();args.output.parent.mkdir(parents=True,exist_ok=True);write_json(args.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
