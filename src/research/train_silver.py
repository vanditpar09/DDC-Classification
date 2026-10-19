"""Offline, work-group-safe hierarchical training on explicitly silver labels.

This is a clean-body/OCR development experiment, not a verified camera benchmark.
Original catalog holdouts and native locked tests never enter fitting. No encoder
fine-tuning, automatic approval, or replacement of the existing artifact occurs.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from src.ddc_data.load_data import load_data
from src.ocr_pipeline.hierarchy import HierarchicalDDC, OTHER, clean_text
from src.ocr_pipeline.multilingual import MultilingualEmbeddings, ENCODER_ID, ENCODER_REVISION, get_encoder, ENCODER_PATH
from src.ocr_pipeline.train_improved import make_splits, cover_text
from src.research.page_windows import page_chunks, predict_pages

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_training(texts, features):
    """Bounded progress and immutable, content-addressed local fitting cache."""
    hashes=np.array([hashlib.sha256(t.encode()).hexdigest() for t in texts])
    identity=hashlib.sha256(('\n'.join(hashes.tolist())+sha(ROOT/ENCODER_PATH/'model.safetensors')+ENCODER_REVISION).encode()).hexdigest()
    folder=ROOT/'models/native_training_cache';folder.mkdir(exist_ok=True)
    path=folder/(identity+'.npz')
    if path.exists():
        saved=np.load(path,allow_pickle=False)
        if not np.array_equal(saved['text_sha256'],hashes):raise ValueError('Invalid fitting cache')
        matrix=saved['matrix']
        if matrix.shape!=(len(texts),384) or not np.isfinite(matrix).all():raise ValueError('Invalid cached features')
        # This cache contains frozen features only, never fitted model scores.
        from collections import OrderedDict
        features._cache=OrderedDict(zip(texts,matrix))
        return matrix
    parts=[]
    for i in range(0,len(texts),64):
        parts.append(features.transform(texts[i:i+64]))
        print(f'Encoded {min(i+64,len(texts))}/{len(texts)} fitting texts',flush=True)
    matrix=np.concatenate(parts)
    np.savez_compressed(path,matrix=matrix,text_sha256=hashes)
    return matrix


def precompute_catalog():
    records=load_data()['records'];indices=make_splits(records)['train'];texts=[]
    for i in indices:texts.extend(dict.fromkeys([clean_text(records[i]['raw_text']),cover_text(records[i])]))
    encode_training(texts,MultilingualEmbeddings(cache_size=12000,batch_size=16))


class SilverHierarchicalDDC(HierarchicalDDC):
    """Compatible predictions with manual review enforced for uncalibrated heads."""
    def predict_hierarchy(self, *args, **kwargs):
        rows=super().predict_hierarchy(*args, **kwargs)
        for row in rows:
            row['review_level']=0
            row['needs_finer_evidence']=True
            row['score_note']='Uncalibrated silver-label experiment; all suggestions require review.'
            for level in row['path']:level['review_ready']=False
        return rows


def validate_books(books):
    seen=set();groups=defaultdict(set)
    texts={}
    for b in books:
        if b['work_id'] in seen:raise ValueError('Duplicate edition')
        seen.add(b['work_id'])
        if not b.get('experimental_eligible') or b.get('verified_section') is not None or b.get('human_checked'):
            raise ValueError('This trainer accepts only explicitly assistant-labelled silver records')
        if b['assigned_partition'] not in {'train','development','test'}:raise ValueError('Unknown partition')
        if len(b['silver_section'])!=3 or not b['silver_section'].isascii() or not b['silver_section'].isdigit():
            raise ValueError('Invalid section')
        if not b['samples']:raise ValueError('Empty book')
        groups[b['group_id']].add((b['assigned_partition'],b['silver_section']))
        for s in b['samples']:
            path=ROOT/s['text_file']
            if sha(path)!=s['text_sha256']:raise ValueError('Modified prepared passage')
            if s.get('human_checked') or s.get('reference_is_ground_truth'):raise ValueError('False gold reference claim')
            if s['text_sha256'] in texts and texts[s['text_sha256']]!=b['group_id']:
                raise ValueError('Repeated passage across different work groups')
            texts[s['text_sha256']]=b['group_id']
    if any(len(v)!=1 for v in groups.values()):raise ValueError('Work group leaks across partitions or labels')


def native_views(book, tokenizer):
    texts=[];weights=[];audits=[]
    for s in book['samples']:
        raw=(ROOT/s['text_file']).read_text()
        chunks,audit=page_chunks([dict(kind='contents',text=raw)],tokenizer,max_chunks_per_page=4)
        texts.extend(c['text'] for c in chunks)
        weights.extend(c['weight']/len(book['samples']) for c in chunks)
        audits.extend(audit)
    return texts,weights,audits


def metrics(rows):
    if not rows:return dict(books=0,work_groups=0,levels={})
    group_sizes=Counter(r['group_id'] for r in rows)
    weights=np.array([1/group_sizes[r['group_id']] for r in rows])
    levels={}
    for level in (1,2,3):
        truth=[r['section'][:level].ljust(3,'0') for r in rows]
        pred=[next((p.get('label') for p in r['hierarchy']['path'] if p['level']==level),None) or 'ABSTAIN' for r in rows]
        levels[str(level)]=dict(accuracy=float(np.average(np.array(truth)==pred,weights=weights)),
            macro_f1=float(f1_score(truth,pred,labels=sorted(set(truth)),average='macro',sample_weight=weights,zero_division=0)),
            suggestion_coverage=float(np.average(np.array(pred)!='ABSTAIN',weights=weights)),
            per_section={k:dict(books=truth.count(k),correct=sum(a==b==k for a,b in zip(truth,pred))) for k in sorted(set(truth))})
    return dict(books=len(rows),work_groups=len(group_sizes),levels=levels)


def evaluate_native(model, books):
    rows=[]
    for b in books:
        # Body passages occupy three equal-weight evidence slots internally;
        # these are NOT cover/back/contents captures. Report only body evidence.
        pages=[dict(kind=k,text=(ROOT/s['text_file']).read_text()) for k,s in zip(('cover','back_cover','contents'),b['samples'][:3])]
        result=predict_pages(model,pages)
        rows.append(dict(work_id=b['work_id'],group_id=b['group_id'],language=b['language'],section=b['silver_section'],
                         hierarchy=result['hierarchy'],omitted_text=result['omitted_text'],evidence='sampled body passages; not camera captures'))
    return rows


def train(dataset,output,report):
    started=time.perf_counter()
    dataset=ROOT/dataset;output=ROOT/output;report=ROOT/report
    books=list(map(json.loads,(dataset/'books.jsonl').read_text().splitlines()));validate_books(books)
    report.mkdir(parents=True,exist_ok=False);output.mkdir(parents=True,exist_ok=False)
    baseline_path=ROOT/'models/hierarchy_v1/classifier.joblib';original_sha=sha(baseline_path)
    original=load_data()['records'];splits=make_splits(original)
    train_books=[b for b in books if b['assigned_partition']=='train']
    dev_books=[b for b in books if b['assigned_partition']=='development']
    assignments=[dict(document_id=original[i]['document_id'],group_id=original[i]['split_group_id'],partition=k,source='original_catalog')
                 for k,indices in splits.items() for i in indices]
    assignments += [dict(document_id=b['work_id'],group_id=b['group_id'],partition=b['assigned_partition'],source='native_silver') for b in books]
    (report/'split-assignments.json').write_text(json.dumps(assignments,ensure_ascii=False,indent=2)+'\n')
    protocol=dict(C=10.,min_groups=5,native_group_weight=10.,encoder=ENCODER_ID,encoder_revision=ENCODER_REVISION,
                  selection='Single predeclared configuration; no search on development or locked test',
                  calibration='None; manual review always required',native_test_locked=True,
                  dataset_sha256=sha(dataset/'books.jsonl'),baseline_sha256=original_sha,
                  original_catalog_train=len(splits['train']),native_train_editions=len(train_books),native_development_editions=len(dev_books))
    (report/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    records=list(original);texts=[];book_indices=[];weights=[];audits=[]
    for i in splits['train']:
        views=list(dict.fromkeys([clean_text(original[i]['raw_text']),cover_text(original[i])]))
        texts.extend(views);book_indices.extend([int(i)]*len(views));weights.extend([1/len(views)]*len(views))
    tokenizer=get_encoder(ENCODER_PATH).tokenizer
    editions_per_group=Counter(b['group_id'] for b in train_books)
    train_indices=list(map(int,splits['train']))
    for b in train_books:
        i=len(records);train_indices.append(i)
        records.append(dict(document_id=b['work_id'],split_group_id='native:'+b['group_id'],
                            label_level_1=b['silver_section'][0]+'00',ddc_raw=[b['silver_section']]))
        views,w,a=native_views(b,tokenizer)
        texts.extend(views);book_indices.extend([i]*len(views));weights.extend(10.*v/editions_per_group[b['group_id']] for v in w)
        audits.append(dict(work_id=b['work_id'],chunk_audits=a,training_weight=sum(weights[-len(w):])))
    (report/'native-training-windows.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n')
    labels=np.array([records[i]['label_level_1'] for i in book_indices])
    features=MultilingualEmbeddings(cache_size=12000,batch_size=16)
    print(f'Encoding {len(texts)} training windows on CPU, offline...',flush=True)
    # Cache is retained locally with a text hash; it contains ONLY fitting views.
    # The original fitting block can be prepared while book OCR runs. Neither
    # cache reads calibration/development/test features or labels.
    native_start=sum(len(list(dict.fromkeys([clean_text(original[i]['raw_text']),cover_text(original[i])]))) for i in splits['train'])
    old_matrix=encode_training(texts[:native_start],features)
    native_matrix=encode_training(texts[native_start:],features)
    matrix=np.concatenate([old_matrix,native_matrix])
    np.savez_compressed(output/'training-embeddings.npz',matrix=matrix, text_sha256=np.array([hashlib.sha256(t.encode()).hexdigest() for t in texts]))
    print('Fitting broad classifier and parent-constrained fine heads...',flush=True)
    clf=LogisticRegression(C=10.,max_iter=2000,random_state=42)
    clf.fit(matrix.astype(np.float64),labels,sample_weight=np.array(weights))
    level1=Pipeline([('features',features),('clf',clf)])
    model=SilverHierarchicalDDC(level1)
    model.features=features
    model.fit_heads(records,train_indices,texts,matrix,book_indices,weights)
    for head in [clf]+[h for heads in model.heads.values() for h in heads.values()]:
        if not np.isfinite(head.coef_).all() or not np.isfinite(head.intercept_).all():
            raise ValueError('Non-finite fitted classifier parameters')
    model.ddc_metadata_=dict(family='native_silver_e5_hierarchy_v1',experimental=True,calibration='none',
                             label_source='Original weak catalog + assistant-reviewed native silver proposals',automatic_acceptance=False)
    joblib.dump(model,output/'classifier.joblib')
    print('Comparing held-out development works against unchanged baseline...',flush=True)
    baseline=joblib.load(baseline_path)
    # Share immutable frozen embeddings only; there is no transfer of fitted heads.
    baseline.features=features
    baseline.level1.estimator.estimator.named_steps['features']=features
    results={};predictions=[]
    for name,m in (('baseline',baseline),('silver_candidate',model)):
        rows=evaluate_native(m,dev_books)
        results[name]=dict(overall=metrics(rows),by_language={lang:metrics([r for r in rows if r['language']==lang]) for lang in ('hin','mar','tam')})
        predictions.extend(dict(model=name,**r) for r in rows)
    # Predeclared 20 old test records per broad class; this test was exposed in
    # previous project work, so it is explicitly a legacy development check.
    legacy=[]
    for label in sorted(set(clf.classes_)):
        pool=[int(i) for i in splits['test'] if original[i]['label_level_1']==label]
        legacy.extend(sorted(pool,key=lambda i:original[i]['document_id'])[:20])
    legacy_text=[clean_text(original[i]['raw_text']) for i in legacy]
    y=np.array([original[i]['label_level_1'] for i in legacy])
    legacy_results={}
    for name,m in (('baseline',baseline),('silver_candidate',model)):
        pred=m.predict(legacy_text)
        legacy_results[name]=dict(books=len(legacy),accuracy=float(np.mean(pred==y)),macro_f1=float(f1_score(y,pred,average='macro')),
                                  note='Previously exposed catalog test subset; development regression check, NOT fresh validation')
    summary=dict(protocol=protocol,development=results,legacy_catalog_development=legacy_results,
                 train_work_groups=len(editions_per_group),head_counts={str(k):len(v) for k,v in model.heads.items()},
                 new_section_support={k:model.support[3].get(k,0) for k in ('891','894','494')},
                 active_new_sections=[k for k in ('891','894','494') if any(k in h.classes_ for h in model.heads[3].values())],
                 model_sha256=sha(output/'classifier.joblib'),baseline_unchanged=sha(baseline_path)==original_sha,
                 seconds=round(time.perf_counter()-started,2),locked_test_evaluated=False,
                 limitations=['Silver labels and OCR are not gold references.','Small development set with provisional work grouping.',
                              'Shared authors/publishers and textbook-family overlap can inflate results.',
                              'Body text differs from phone cover/contents captures; no camera accuracy claim.',
                              'Sparse native classes lack development/test coverage.','Encoder pretraining overlap is unknown.',
                              'No probability calibration or automatic acceptance.','This does not establish patentability.'])
    (report/'development-predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in predictions))
    (report/'metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (output/'metadata.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=Path('data/research/multilingual-pilot-v1/silver-pilot-v1'))
    p.add_argument('--output-dir',type=Path,default=Path('models/native_silver_v1'))
    p.add_argument('--report-dir',type=Path,default=Path('data/research/multilingual-pilot-v1/experiment-v1'))
    p.add_argument('--precompute-catalog',action='store_true')
    a=p.parse_args()
    # Import the canonical module for stable joblib class names under python -m.
    from src.research.train_silver import train as train_run, precompute_catalog as precompute_run
    if a.precompute_catalog:precompute_run()
    else:train_run(a.dataset,a.output_dir,a.report_dir)
