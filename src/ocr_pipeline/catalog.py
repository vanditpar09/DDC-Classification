"""Offline bibliographic matching; catalog codes are not model probabilities."""
import json
import re
import statistics
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/'data/catalog/index.json'
QUALIFIERS=re.compile(r'\b(study\s*guide|critical\s*study|critical\s*analysis|commentary|criticism|notes\s*on|guide\s*to)\b',re.I)


def normalized(value):
    value=unicodedata.normalize('NFKC',value).casefold()
    return ' '.join(''.join(c if c.isalnum() or unicodedata.category(c).startswith('M') else ' ' for c in value).split())


def section_from_codes(codes):
    parsed=[]
    for code in codes:
        if not re.fullmatch(r'\d{3}(?:/?\.\d+)?',str(code),flags=re.ASCII):return None
        parsed.append(str(code)[:3])
    return parsed[0] if parsed and len(set(parsed))==1 else None


@lru_cache(maxsize=1)
def load_index():
    if not INDEX.is_file():return []
    rows=json.loads(INDEX.read_text(encoding='utf-8'))['entries']
    for row in rows:
        row['_title']=normalized(row['title'])
        row['_authors']=[normalized(a) for a in row['authors']]
    return rows


def phrase_present(phrase,text):
    return bool(phrase and (' '+phrase+' ') in (' '+text+' '))


def identity_phrase_present(phrase,text):
    """Allow omitted OCR spaces, never changed letters or substring identities."""
    tokens=phrase.split()
    if not tokens:return False
    pattern=r'(?<!\w)'+r'\s*'.join(re.escape(token) for token in tokens)+r'(?!\w)'
    return bool(re.search(pattern,text))


def title_height(words,title):
    # A recognizer can merge adjacent title words (THEOLD or TheOldMan).
    # Match the complete letter sequence across contiguous word boxes instead.
    target=''.join(title.split());text_tokens=[normalized(w['text']).replace(' ','') for w in words]
    sizes=[]
    for start in range(len(words)):
        joined=''
        for end in range(start,min(len(words),start+len(title.split())+1)):
            if not text_tokens[end]:break
            joined+=text_tokens[end]
            if not target.startswith(joined):break
            if joined==target:
                sizes.append(statistics.median(float(w.get('height',0)) for w in words[start:end+1]));break
    return max(sizes,default=0.)


def match_catalog(pages,entries=None):
    """Require title AND author on a front/back cover.

    Multiple identities abstain unless one cover title is substantially more
    prominent geometrically. Work-level title matches always require edition
    review. No fuzzy semantic match, network access or guessed DDC code occurs.
    """
    entries=load_index() if entries is None else entries
    candidates=[]
    for page in pages:
        if not page.get('usable') or page.get('duplicate'):continue
        text=normalized(page['text']);words=page.get('words') or []
        heights=[float(w.get('height',0)) for w in words if w.get('height',0)>0]
        median=statistics.median(heights) if heights else 0
        for raw in entries:
            title=raw.get('_title') or normalized(raw['title'])
            authors=raw.get('_authors') or [normalized(a) for a in raw['authors']]
            if len(title.split())<2 or not identity_phrase_present(title,text):continue
            if not any(len(a.split())>=2 and identity_phrase_present(a,text) for a in authors):continue
            if page['kind'] not in {'cover','back_cover'} or QUALIFIERS.search(page['text']):continue
            prominent=title_height(words,title)
            first=next((normalized(line) for line in page['text'].splitlines() if line.strip()),'')
            compact=first.replace(' ','')
            first_is_title=(compact==title.replace(' ','') or any(
                compact==(title+' by '+a).replace(' ','') or compact==(title+' '+a).replace(' ','') for a in authors))
            if words:
                if not median or prominent<median*1.5:continue
            elif not first_is_title:
                continue
            # Keep only serializable source fields, never cached normalization.
            candidates.append({'record':{k:v for k,v in raw.items() if not k.startswith('_')},
                'basis':'title and author; prominent cover text' if words else 'title and author transcription',
                'title_height':prominent,'page_id':page.get('id')})
    groups={}
    for candidate in candidates:
        row=candidate['record'];key=(normalized(row['title']),tuple(sorted(normalized(a) for a in row['authors'])))
        groups.setdefault(key,[]).append(candidate)
    if not groups:return {'status':'no_match'}
    options=[]
    for values in groups.values():
        sections={value['record'].get('section') for value in values if value['record'].get('section')}
        best=max(values,key=lambda value:(bool(value['record'].get('section')),value['record'].get('curated',False),value['title_height']))
        if len(sections)>1:
            return {'status':'ambiguous','reason':'Catalog sources disagree on the section'}
        options.append(best)
    options.sort(key=lambda item:item['title_height'],reverse=True)
    if len(options)>1:
        # The same author may advertise another title on the front cover.
        # Geometry can distinguish this; a text-only match cannot.
        if not options[0]['title_height'] or options[0]['title_height']<max(1,options[1]['title_height'])*1.8:
            return {'status':'ambiguous','reason':'Multiple book identities match the evidence'}
    result=options[0]
    if not result['record'].get('section'):
        return {'status':'code_unavailable',**result}
    return {'status':'matched','edition_review_required':True,**result}


def apply_catalog(prediction,match):
    """Replace the displayed code with identified catalog evidence, retaining ML."""
    if match['status']!='matched':return prediction
    row=match['record'];section=row['section']
    prediction['model_suggestion']={k:prediction[k] for k in ('label','score','margin','entropy','top3','hierarchy') if k in prediction}
    prediction.update(label=section[0]+'00',score=None,margin=None,entropy=None,
        result_source='local_catalog',catalog_match=match)
    prediction['hierarchy']={'path':[{'level':level,'label':section[:level].ljust(3,'0'),
        'parent':section[:level-1].ljust(3,'0') if level>1 else None,
        'supported':True,'review_ready':False,'score':None,'top3':[],
        'source':'local_catalog','reason':'Source-reported catalog code; confirm edition'} for level in (1,2,3)],
        'review_level':0,'target_level':3,'needs_finer_evidence':False,
        'score_note':'Matched catalog code, not a learned probability. Confirm the edition.'}
    return prediction


def suppress_uncertain_path(prediction,min_score=.62,min_margin=.18):
    """Stop propagating an uncertain parent into a precise-looking fine code."""
    if prediction.get('catalog_match',{}).get('status')=='matched':return prediction
    path=prediction.get('hierarchy',{}).get('path',[])
    if not path:return prediction
    prediction['model_suggestion']={k:prediction[k] for k in ('label','score','margin','entropy','top3','hierarchy') if k in prediction}
    kept=[];blocked=False
    for row in path:
        row=dict(row)
        passing=(row.get('supported') and (row.get('score') or 0)>=min_score and (row.get('margin') or 0)>=min_margin)
        blocked=blocked or not passing
        if blocked:
            row.update(label=None,supported=False,review_ready=False,score_abstention=True,
                reason='More subject evidence is needed; the model scores do not support this code')
        kept.append(row)
    while len(kept)<3:
        kept.append({'level':len(kept)+1,'label':None,'supported':False,'review_ready':False,'top3':[],
                     'reason':'A finer code cannot be resolved before its parent'})
    prediction['hierarchy']={**prediction['hierarchy'],'path':kept,
        'review_level':min(prediction['hierarchy'].get('review_level',0),sum(bool(row.get('label')) for row in kept)),
        'needs_finer_evidence':any(not row.get('label') for row in kept)}
    if kept[0]['label'] is None:prediction['label']=None
    prediction['result_source']='model_candidate'
    return prediction
