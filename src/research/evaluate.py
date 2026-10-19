"""Compare the existing model and page-window experiment on reviewed books.

Defaults to development only. Locked-test use must be deliberate. Reference
transcription and raw OCR are reported separately, using the same books for both
strategies within each view; failed/missing OCR is reported as missing, not fixed.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time
import unicodedata

import joblib
import numpy as np
from sklearn.metrics import f1_score

from src.research.collection import read_jsonl, write_json
from src.research.page_windows import predict_pages
from src.ocr_pipeline.multilingual import get_encoder, ENCODER_PATH, ENCODER_REVISION
from src.ocr_pipeline.hierarchy import clean_text

VIEWS={'cover':{'cover'},'cover_back':{'cover','back_cover'},'all_pages':{'cover','back_cover','contents'}}


def edit_distance(a,b):
    # Trim equal boundaries; keep all Indic marks and avoid a full NxM matrix.
    prefix=0
    while prefix<min(len(a),len(b)) and a[prefix]==b[prefix]:prefix+=1
    a,b=a[prefix:],b[prefix:]
    suffix=0
    while suffix<min(len(a),len(b)) and a[-suffix-1]==b[-suffix-1]:suffix+=1
    if suffix:a,b=a[:-suffix],b[:-suffix]
    if len(a)>len(b):a,b=b,a
    previous=list(range(len(a)+1))
    for i,cb in enumerate(b,1):
        current=[i]
        for j,ca in enumerate(a,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(ca!=cb)))
        previous=current
    return previous[-1]


def ocr_errors(pages):
    totals={'pages':0,'character_edits':0,'reference_characters':0,'word_edits':0,'reference_words':0,'empty_ocr_pages':0}
    for page in pages:
        if page['origin']!='native_scan':continue
        if not page['ocr_text'].strip():totals['empty_ocr_pages']+=1
        ref=' '.join(unicodedata.normalize('NFC',page['reference_text']).split())
        hyp=' '.join(unicodedata.normalize('NFC',page['ocr_text']).split())
        totals['pages']+=1
        totals['character_edits']+=edit_distance(ref,hyp)
        totals['reference_characters']+=len(ref)
        totals['word_edits']+=edit_distance(ref.split(),hyp.split())
        totals['reference_words']+=len(ref.split())
    totals['cer']=totals['character_edits']/totals['reference_characters'] if totals['reference_characters'] else None
    totals['wer']=totals['word_edits']/totals['reference_words'] if totals['reference_words'] else None
    return totals


def summarize(rows):
    if not rows:return {'books':0,'work_groups':0,'levels':{}}
    group_sizes=Counter(r['work_id'] for r in rows)
    weights=np.asarray([1/group_sizes[r['work_id']] for r in rows])
    levels={}
    for level in (1,2,3):
        truth=[r['section'][:level].ljust(3,'0') for r in rows]
        predictions=[next((p.get('label') for p in r['hierarchy']['path'] if p['level']==level),None) or 'ABSTAIN' for r in rows]
        correct=np.asarray(truth)==predictions
        levels[str(level)]={'accuracy':float(np.average(correct,weights=weights)),
            'macro_f1':float(f1_score(truth,predictions,labels=sorted(set(truth)),average='macro',sample_weight=weights,zero_division=0)),
            'abstention_rate':float(np.average(np.asarray(predictions)=='ABSTAIN',weights=weights)),
            'truth_labels':len(set(truth))}
    return {'books':len(rows),'work_groups':len(group_sizes),'levels':levels,
            'mean_seconds_per_book':float(np.mean([r['seconds'] for r in rows])),
            'omitted_text_books':sum(r['omitted_text'] for r in rows)}


def load_prepared(directory):
    path=directory/'books.jsonl'
    manifest=json.loads((directory/'manifest.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['prepared_sha256']:
        raise ValueError('Prepared collection changed; freeze a new version before comparing')
    rows=read_jsonl(path)
    for row in rows:
        if row['partition']!=manifest['work_assignments'][row['work_id']]:
            raise ValueError('Conflicting work partition')
        for page in row['pages']:
            if page.get('image_path'):
                image=Path(manifest['image_root'])/page['image_path']
                if hashlib.sha256(image.read_bytes()).hexdigest()!=page['image_sha256']:
                    raise ValueError('Collection image changed after preparation')
    return rows,manifest


def evaluate(directory,model_path,output,partition='development',allow_locked_test=False):
    if partition=='test' and not allow_locked_test:
        raise ValueError('Locked test requires --allow-locked-test after freezing methods and thresholds')
    all_rows,manifest=load_prepared(directory)
    rows=sorted([r for r in all_rows if r['partition']==partition],key=lambda r:r['book_id'])
    if not rows:raise ValueError(f'No reviewed books in {partition}; do not substitute authored examples')
    if output.exists():raise ValueError('Use a new output directory for every evaluation')
    model=joblib.load(model_path)
    tokenizer=get_encoder(ENCODER_PATH).tokenizer
    predictions=[];summary={};missing={}
    # Warm both feature paths; latency below excludes encoder/model initialization.
    model.predict_hierarchy(['warmup'])
    for mode in ('reference','ocr'):
        for view,kinds in VIEWS.items():
            eligible=[]
            for row in rows:
                selected=[p for p in row['pages'] if p['kind'] in kinds]
                if not kinds.issubset({p['kind'] for p in selected}):continue
                field='reference_text' if mode=='reference' else 'ocr_text'
                if mode=='ocr' and any(p['origin']!='native_scan' for p in selected):continue
                if not all(p[field].strip() for p in selected):continue
                eligible.append((row,[{'kind':p['kind'],'text':p[field]} for p in selected]))
            missing[f'{mode}:{view}']={'eligible_books':len(eligible),'missing_required_pages_or_text':len(rows)-len(eligible)}
            for strategy in ('baseline','page_windows'):
                batch=[]
                for row,pages in eligible:
                    start=time.perf_counter()
                    if strategy=='baseline':
                        text=clean_text('\n'.join(p['text'] for p in sorted(pages,key=lambda p:['cover','back_cover','contents'].index(p['kind']))))
                        result=model.predict_hierarchy([text])[0]
                        omitted=len(tokenizer.encode('query: '+text,add_special_tokens=True))>512
                        chunks=1
                    else:
                        result=predict_pages(model,pages,tokenizer)
                        omitted=result['omitted_text'];chunks=len(result['chunks']);result=result['hierarchy']
                    item={'book_id':row['book_id'],'work_id':row['work_id'],'language':row['language'],
                          'section':row['section'],'mode':mode,'view':view,'strategy':strategy,'hierarchy':result,
                          'omitted_text':omitted,'chunks':chunks,'seconds':time.perf_counter()-start}
                    predictions.append(item);batch.append(item)
                key=f'{mode}:{view}:{strategy}'
                summary[key]={'overall':summarize(batch),'by_language':{
                    lang:summarize([r for r in batch if r['language']==lang]) for lang in ('eng','hin','mar','tam')}}
    output.mkdir(parents=True,exist_ok=False)
    write_json(output/'predictions.json',predictions)
    write_json(output/'metrics.json',{'partition':partition,'collection_sha256':manifest['prepared_sha256'],
        'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'encoder_revision':ENCODER_REVISION,
        'strategies_fixed':['baseline','page_windows'],'page_weighting':'equal pages; character-weighted chunks within each page',
        'max_chunks_per_page':4,'warm_latency':True,'summary':summary,'missing_data':missing,
        'ocr_by_language':{lang:ocr_errors([p for r in rows if r['language']==lang for p in r['pages']]) for lang in ('eng','hin','mar','tam')},
        'limitations':['Pilot metrics do not establish general accuracy; report sample and work counts.',
            'Page-pooled scores require new calibration and never pass automatic review thresholds.',
            'Missing OCR is excluded from paired text-classification metrics and counted explicitly; empty OCR counts as complete error in CER/WER. These are not end-to-end scan success rates.',
            'Latency is order/cache dependent and descriptive; not an efficiency claim.',
            'CER/WER uses NFC + whitespace normalization, case/punctuation preserved, words split by whitespace.',
            'Existing catalog overlap and cross-language work IDs still require human review.']})
    return {'output':str(output),'partition':partition,'books':len(rows),'comparisons':len(summary)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collection',type=Path)
    parser.add_argument('--model',type=Path,default=Path('models/hierarchy_v1/classifier.joblib'))
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--partition',choices=['development','test'],default='development')
    parser.add_argument('--allow-locked-test',action='store_true')
    args=parser.parse_args()
    print(json.dumps(evaluate(args.collection,args.model,args.output_dir,args.partition,args.allow_locked_test),indent=2))


if __name__=='__main__':main()
