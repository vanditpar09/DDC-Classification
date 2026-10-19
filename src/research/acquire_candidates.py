"""Small, cached Open Library shortlist for a human-run multilingual pilot.

Four batch searches, never a bulk corpus download. Source DDC is a weak catalog
label; language-filtered editions can have transliterated titles. These records
are candidates only and cannot enter the verified native-scan evaluator.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import httpx
from src.research.collection import LANGUAGES, catalog_alias, known_catalog, write_json

FIELDS=','.join(['key','title','ddc','author_name','language','edition_key','cover_i','ebook_access','ia',
                 'editions','editions.key','editions.title','editions.language','editions.ddc',
                 'editions.isbn','editions.cover_i','editions.ebook_access'])


def script_evidence(text,language):
    if language in {'hin','mar'}:
        count=sum('\u0900'<=c<='\u097f' and c.isalpha() for c in text)
        return {'script':'Devanagari','native_letters':count,'native_script_present':count>0}
    if language=='tam':
        count=sum('\u0b80'<=c<='\u0bff' and c.isalpha() for c in text)
        return {'script':'Tamil','native_letters':count,'native_script_present':count>0}
    return {'script':'Latin','native_letters':sum(c.isascii() and c.isalpha() for c in text),'native_script_present':True}


def weak_labels(codes):
    valid=[c for c in codes if isinstance(c,str) and re.fullmatch(r'[0-9]{3}(?:\.[0-9]+)?',c)]
    labels={}
    for level in (1,2,3):
        prefixes={code[:level].ljust(3,'0') for code in valid}
        # Non-standard notation stays in raw data; never silently normalize it.
        labels[str(level)]=next(iter(prefixes)) if len(prefixes)==1 and len(valid)==len(codes) else None
    return labels


def parse_docs(snapshot,index):
    language=snapshot['language']; result=[]; rejected=Counter()
    for doc in snapshot['response'].get('docs',[]):
        work=catalog_alias(doc.get('key','').removeprefix('/works/'))
        if not re.fullmatch(r'OL[0-9]+W',work):rejected['missing_work_id']+=1;continue
        matching=doc.get('editions',{}).get('docs',[])
        edition=next((e for e in matching if language in e.get('language',[])),None)
        if not edition:rejected['no_explicit_matching_edition_language']+=1;continue
        book=catalog_alias(edition.get('key','').removeprefix('/books/'))
        if not re.fullmatch(r'OL[0-9]+M',book):rejected['missing_edition_id']+=1;continue
        title=edition.get('title','')
        if not isinstance(title,str) or not title.strip():rejected['missing_edition_title']+=1;continue
        codes=doc.get('ddc',[])
        if not isinstance(codes,list) or not codes:rejected['no_catalog_ddc']+=1;continue
        evidence=script_evidence(title,language)
        aliases=[work,book,*edition.get('isbn',[])]
        prior=sorted({p for alias in aliases for p in index.get(catalog_alias(alias),set())})
        result.append({'candidate_id':f'{language}:{book}','book_id':book,'work_id':work,'language':language,
            'title':title,'work_title':doc.get('title',''),'authors':doc.get('author_name',[]),
            'catalog_ids':aliases,'ddc_raw':codes,'weak_labels':weak_labels(codes),
            'label_scope':'work-level catalog DDC; not independently verified for this edition',
            'title_script':evidence,'review_status':'pending','verified_section':None,
            'native_scan_ready':False,'capture_permission':False,
            'source_url':f'https://openlibrary.org/books/{book}',
            'work_source_url':f'https://openlibrary.org/works/{work}',
            'query_url':snapshot['url'],'retrieved_at':snapshot['retrieved_at'],
            'snapshot_sha256':snapshot['payload_sha256'],'prior_catalog_memberships':prior,
            'cover_id':edition.get('cover_i') or doc.get('cover_i'),
            'ebook_access':edition.get('ebook_access') or doc.get('ebook_access','unknown'),
            'archive_ids':doc.get('ia',[]),
            'image_reuse_status':'Not established; public catalog/availability is not image reuse permission'})
    return result,dict(rejected)


def acquire(output,target=20,fetch=False):
    if not 1<=target<=20:raise ValueError('This pilot shortlist is capped at 20 candidates per language')
    output.mkdir(parents=True,exist_ok=True)
    raw=output/'sources';raw.mkdir(exist_ok=True)
    _,index=known_catalog()
    pool=[];rejections={};hashes={};requests=0
    with httpx.Client(timeout=60,headers={'User-Agent':'DDCClassificationResearchPilot/1.0'},follow_redirects=True) as client:
        for language in LANGUAGES:
            queries=[(0,'relevance')]+([(100,'relevance')] if language in {'mar','tam'} else [])+[(0,'random')]
            combined_rejections=Counter();unique_works={}
            for offset,sort in queries:
                suffix=(f'-{sort}' if sort=='random' else (f'-offset{offset}' if offset else ''))
                path=raw/f'openlibrary-{language}{suffix}.json'
                if not path.exists():
                    if not fetch:raise ValueError(f'Missing cached source {path}; use --fetch to retrieve the small source snapshot')
                    if requests:time.sleep(1.1)
                    response=client.get('https://openlibrary.org/search.json',params={
                        'q':f'language:{language} AND ddc:[000 TO 999]','offset':offset,'limit':100,'fields':FIELDS,**({'sort':'random'} if sort=='random' else {})})
                    response.raise_for_status()
                    snapshot={'language':language,'url':str(response.url),'retrieved_at':datetime.now(timezone.utc).isoformat(),
                        'payload_sha256':hashlib.sha256(response.content).hexdigest(),'response':response.json()}
                    write_json(path,snapshot);requests+=1
                snapshot=json.loads(path.read_text(encoding='utf-8'))
                hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                candidates,rejected=parse_docs(snapshot,index)
                for candidate in candidates:
                    key=candidate['work_id']
                    quality=(candidate['title_script']['native_script_present'],not bool(candidate['prior_catalog_memberships']),
                             candidate['weak_labels']['3'] is not None)
                    if key not in unique_works or quality>unique_works[key][0]:
                        unique_works[key]=(quality,candidate)
                combined_rejections.update(rejected)
            candidates=[item[1] for item in unique_works.values()]
            pool.extend(candidates);rejections[language]=dict(combined_rejections)
    selected=[];counts={};seen=set()
    for language in LANGUAGES:
        choices=[r for r in pool if r['language']==language]
        # Native script, fresh work, unambiguous catalog section first; balance broad labels when possible.
        choices.sort(key=lambda r:(not r['title_script']['native_script_present'],bool(r['prior_catalog_memberships']),
                                   r['weak_labels']['3'] is None,r['work_id']))
        broad_counts=Counter();chosen=[]
        for _ in range(target):
            available=[r for r in choices if (language,r['work_id']) not in seen]
            if not available:break
            labelled=[r for r in available if r['weak_labels']['1'] is not None]
            # Cover each observed broad class once before accepting a large UNKNOWN bucket.
            sample=labelled if labelled else available
            best=min(sample,key=lambda r:(broad_counts[r['weak_labels']['1'] or 'unknown'],
                 not r['title_script']['native_script_present'],bool(r['prior_catalog_memberships']),
                 r['weak_labels']['3'] is None,choices.index(r)))
            seen.add((language,best['work_id']));broad_counts[best['weak_labels']['1'] or 'unknown']+=1
            chosen.append(best)
        selected.extend(chosen)
        counts[language]={'available_matching_works':len({r['work_id'] for r in choices}),'selected':len(chosen),
            'native_script_titles':sum(r['title_script']['native_script_present'] for r in chosen),
            'romanized_or_unconfirmed_titles':sum(not r['title_script']['native_script_present'] for r in chosen),
            'prior_catalog_overlap':sum(bool(r['prior_catalog_memberships']) for r in chosen),
            'unambiguous_weak_sections':sum(r['weak_labels']['3'] is not None for r in chosen),
            'weak_class_counts':dict(broad_counts)}
    def jsonl(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    jsonl(output/'candidate-pool.jsonl',pool)
    jsonl(output/'candidates.jsonl',selected)
    manifest={'schema_version':1,'target_per_language':target,'selected_books':len(selected),'by_language':counts,
        'rejected_source_records':rejections,'source_files_sha256':hashes,'network_batch_requests_this_run':requests,'query_limit_per_snapshot':100,
        'randomized_source_pages':['eng','hin','mar','tam'],
        'extra_relevance_offsets_for_sparse_native_scripts':['mar','tam'],
        'candidates_sha256':hashlib.sha256((output/'candidates.jsonl').read_bytes()).hexdigest(),
        'source_api':'https://openlibrary.org/dev/docs/api/search',
        'source_usage':'https://openlibrary.org/developers/api','source_rights':'https://openlibrary.org/developers/licensing',
        'limitations':['Catalog candidates, not a verified training or camera benchmark.',
            'Source titles may be romanized even when the selected edition has the target language.',
            'Work-level DDC can disagree between editions; verified edition labels remain empty.',
            'No cover/page images were downloaded or assigned reuse permission.',
            'Native-script availability and class balance can be inadequate; do not invent missing data.',
            'Known catalog overlap is recorded, never a fresh independent test.']}
    write_json(output/'candidate-manifest.json',manifest)
    # Prefill source facts only. Reference text, capture permission and verified labels remain blank.
    forms=[]
    for row in selected:
        forms.append({'candidate_id':row['candidate_id'],'book_id':row['book_id'],'work_id':row['work_id'],
            'catalog_ids':row['catalog_ids'],'language':row['language'],'title':row['title'],
            'review_status':'pending','section':'','reviewer':'','label_source':'',
            'candidate_source_url':row['source_url'],'candidate_work_url':row['work_source_url'],
            'capture_permission':False,'suggested_page_types':['cover','back_cover','contents'],
            'pages':[]})
    jsonl(output/'candidate-review-forms.jsonl',forms)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--fetch',action='store_true',help='Fetch only missing snapshots; cached replay needs no network')
    args=parser.parse_args();print(json.dumps(acquire(args.output_dir,fetch=args.fetch),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
