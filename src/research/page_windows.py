"""Experimental page-balanced inference for the saved DDC model.

Each page keeps its own token budget. Within a page, chunks share its weight;
long contents cannot erase the cover. All paths obey parent constraints. Pooled
scores need new calibration and always require review. This module does not
replace the prototype's validated baseline or alter saved classifier weights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import unicodedata

import joblib
import numpy as np

from src.ocr_pipeline.hierarchy import OTHER, clean_text, head_probabilities
from src.ocr_pipeline.multilingual import ENCODER_PATH, get_encoder

KINDS = ('cover','back_cover','contents')


def page_chunks(pages, tokenizer, max_tokens=512, max_chunks_per_page=4):
    if max_tokens < 16 or not 1 <= max_chunks_per_page <= 8:
        raise ValueError('Use at least 16 tokens and 1-8 chunks per page')
    chunks=[]; audit=[]; seen=set()
    overhead=len(tokenizer.encode('query: ',add_special_tokens=True))
    budget=max_tokens-overhead-16
    if budget<1:
        raise ValueError('Token limit leaves no text budget')
    for page in sorted(pages,key=lambda p:KINDS.index(p['kind']) if p.get('kind') in KINDS else 99):
        kind=page.get('kind')
        if kind not in KINDS or kind in seen:
            raise ValueError('Use one current page per type: cover, back_cover, contents')
        seen.add(kind)
        text=clean_text(page['text']).strip()
        if not text:
            continue
        count=len(tokenizer.encode('query: '+text,add_special_tokens=True))
        start=0; page_windows=[]
        if count<=max_tokens:
            page_windows=[{'kind':kind,'text':text,'start':0,'end':len(text),'tokens':count}]
            start=len(text)
        else:
            offsets=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
            offsets=[(a,b) for a,b in offsets if b>a]
            position=0
            for _ in range(max_chunks_per_page):
                while position<len(offsets) and offsets[position][1]<=start:
                    position+=1
                if position==len(offsets):
                    break
                end=offsets[min(position+budget-1,len(offsets)-1)][1]
                # Preserve combining-mark sequences when the tokenizer boundary is inside one.
                while end<len(text) and unicodedata.category(text[end]).startswith('M'):
                    end+=1
                while end>start:
                    fragment=text[start:end].strip()
                    tokens=len(tokenizer.encode('query: '+fragment,add_special_tokens=True))
                    if fragment and tokens<=max_tokens:
                        break
                    end-=1
                    while end>start and end<len(text) and unicodedata.category(text[end]).startswith('M'):
                        end-=1
                if end<=start:
                    raise ValueError('Tokenizer could not produce a bounded nonempty window')
                page_windows.append({'kind':kind,'text':fragment,'start':start,'end':end,'tokens':tokens})
                start=end
                if not text[start:].strip():
                    start=len(text);break
        total=sum(c['end']-c['start'] for c in page_windows)
        for chunk in page_windows:
            chunk['weight_within_page']=(chunk['end']-chunk['start'])/total
        chunks.extend(page_windows)
        audit.append({'kind':kind,'original_tokens':count,'chunks':len(page_windows),
                      'covered_characters':start,'total_characters':len(text),'omitted_tail':bool(text[start:].strip())})
    if not chunks:
        raise ValueError('No usable page text')
    for chunk in chunks:
        chunk['weight']=chunk['weight_within_page']/len(audit)
    return chunks,audit


def _probabilities(values):
    if not np.isfinite(values).all() or np.any(values<0) or not np.allclose(values.sum(axis=-1),1):
        raise ValueError('Invalid page-window probabilities')
    return values


def predict_pages(model,pages,tokenizer=None,max_chunks_per_page=4):
    if tokenizer is None:
        tokenizer=get_encoder(ENCODER_PATH).tokenizer
    chunks,audit=page_chunks(pages,tokenizer,max_chunks_per_page=max_chunks_per_page)
    texts=[c['text'] for c in chunks]
    if len(chunks)==1:
        hierarchy=model.predict_hierarchy(texts)[0]
        if any(a['omitted_tail'] for a in audit):
            hierarchy['review_level']=0
            hierarchy['score_note']='Text exceeds the experiment budget; manual review required.'
            for row in hierarchy['path']:row['review_ready']=False
        return {'hierarchy':hierarchy,'strategy':'single_window_baseline','chunks':chunks,'page_coverage':audit,
                'omitted_text':any(a['omitted_tail'] for a in audit),'experimental_pooling':False}
    weights=np.asarray([c['weight'] for c in chunks],dtype=np.float64)
    broad=_probabilities(np.asarray(model.predict_proba(texts),dtype=np.float64))
    matrix=model.features.transform(texts).astype(np.float64)
    pooled=_probabilities(weights@broad)
    order=np.argsort(pooled)[::-1]; parent=str(model.classes_[order[0]])
    mass=broad[:,order[0]]
    path=[{'level':1,'label':parent,'score':float(pooled[order[0]]),'path_score':float(pooled[order[0]]),
           'supported':True,'review_ready':False,'margin':float(pooled[order[0]]-pooled[order[1]]),
           'top3':[{'label':str(model.classes_[i]),'score':float(pooled[i])} for i in order[:3]]}]
    for level in (2,3):
        head=model.heads[level].get(parent)
        if head is None:
            path.append({'level':level,'parent':parent,'label':None,'supported':False,'review_ready':False,
                         'reason':'Insufficient training support for this branch','top3':[]})
            break
        conditional=_probabilities(head_probabilities(head,matrix,model.temperatures[level]))
        denominator=float(weights@mass)
        if denominator<=0:
            raise ValueError('Selected parent has zero probability mass')
        # Average child joint mass first, then condition on the pooled parent.
        child_joint=(weights*mass)@conditional
        scores=_probabilities(child_joint/denominator)
        order=np.argsort(scores)[::-1]; label=str(head.classes_[order[0]])
        known=label!=OTHER
        path.append({'level':level,'parent':parent,'label':label if known else None,'supported':known,
                     'score':float(scores[order[0]]),'margin':float(scores[order[0]]-scores[order[1]]),
                     'path_score':float(child_joint[order[0]]),'review_ready':False,
                     'training_groups':model.support[level].get(label,0),
                     'top3':[{'label':str(head.classes_[i]) if head.classes_[i]!=OTHER else None,
                              'score':float(scores[i])} for i in order[:3]],
                     'reason':'Experimental page pooling; manual review required' if known else 'Rare or unsupported child class'})
        if not known:
            break
        mass=mass*conditional[:,order[0]]
        parent=label
    return {'hierarchy':{'path':path,'review_level':0,'target_level':3,'needs_finer_evidence':True,
                        'score_note':'Page-pooled scores have not been recalibrated; always review.'},
            'strategy':'page_balanced_joint_pooling_v1','chunks':chunks,'page_coverage':audit,
            'omitted_text':any(a['omitted_tail'] for a in audit),'experimental_pooling':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pages',type=Path,help='JSON array of {kind,text} pages')
    parser.add_argument('--model',type=Path,default=Path('models/hierarchy_v1/classifier.joblib'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=predict_pages(joblib.load(args.model),json.loads(args.pages.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='chunks'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
