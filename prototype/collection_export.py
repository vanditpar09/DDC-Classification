"""Readable derived outputs; SQLite remains the authoritative capture record."""
from __future__ import annotations

import csv
import html
import io
import json
import math
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ('Book','L1','L2','L3','Source','Status','Languages','Pages','Session ID',
           'Revision','Updated UTC','Reviewed L1','Reviewed L2','Reviewed L3','Review evidence revision',
           'Suggested L1','L1 model score (%)','Suggested L2','L2 conditional score (%)',
           'Suggested L3','L3 conditional score (%)')

SCORE_COLUMNS = {1:'L1 model score (%)',2:'L2 conditional score (%)',3:'L3 conditional score (%)'}


def safe_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):
        raise ValueError('Invalid identifier for a derived export')
    return value


def code(value):
    return value if isinstance(value,str) and re.fullmatch(r'[0-9]{3}',value) else ''


def model_fields(prediction):
    """Keep uncalibrated learned candidates separate from qualified/catalog codes."""
    result={f'Suggested L{level}':'' for level in (1,2,3)}
    result.update({name:'' for name in SCORE_COLUMNS.values()})
    raw=prediction.get('model_suggestion')
    if raw is None:
        if prediction.get('result_source')=='local_catalog':return result
        raw=prediction
    path=raw.get('hierarchy',{}).get('path',[])
    if not path and not raw.get('hierarchy'):
        path=[{'level':1,'label':raw.get('label'),'score':raw.get('score'),'supported':True}]
    for item in path:
        level=item.get('level');label=code(item.get('label'))
        if level not in SCORE_COLUMNS or not item.get('supported') or not label:continue
        result[f'Suggested L{level}']=label
        score=item.get('score')
        if isinstance(score,(int,float)) and math.isfinite(score) and 0<=score<=1:
            result[SCORE_COLUMNS[level]]=round(score*100,2)
    return result


def collection_rows(store):
    rows=[]
    for session in store.list():
        prediction=session.get('prediction') or {}
        match=prediction.get('catalog_match') or {}
        title=(match.get('record') or {}).get('title') or next(
            (line.strip() for line in session.get('combined_text','').splitlines() if line.strip()),'Untitled book')
        path={p['level']:code(p.get('label')) for p in prediction.get('hierarchy',{}).get('path',[]) if p.get('supported')}
        if not path and not prediction.get('hierarchy'):
            path[1]=code(prediction.get('label'))
        review=(session.get('reviews') or [{}])[-1]
        photos=[{'id':safe_id(p['id']),'kind':p['kind']} for p in session['pages'] if p.get('source')=='ocr']
        rows.append({'Book':title,'L1':path.get(1,''),'L2':path.get(2,''),'L3':path.get(3,''),
            'Source':'Catalog match' if prediction.get('result_source')=='local_catalog' else 'Model suggestion' if prediction else '',
            'Status':(session.get('decision') or {}).get('title','Waiting for evidence'),
            'Languages':', '.join(sorted({p['language'] for p in session['pages']})),
            'Pages':len(session['pages']),'Session ID':safe_id(session['id']),
            'Revision':session.get('revision',0),
            'Updated UTC':datetime.fromtimestamp(session['updated'],timezone.utc).isoformat(),
            'Reviewed L1':code(review.get('class')),'Reviewed L2':code(review.get('division')),
            'Reviewed L3':code(review.get('section')),'Review evidence revision':review.get('evidence_revision',''),
            'photos':photos,**model_fields(prediction)})
    return rows


def csv_text(rows):
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=COLUMNS,extrasaction='ignore');writer.writeheader()
    for row in rows:
        # Prevent source titles from becoming formulas when opened in spreadsheets.
        clean={key:("'"+value if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')) else value)
               for key,value in row.items()}
        writer.writerow(clean)
    return output.getvalue()


def html_table(rows,offline=False):
    esc=lambda value:html.escape(str(value),quote=True)
    csv_url='classifications.csv' if offline else '/api/collection/export?format=csv'
    json_url='classifications.json' if offline else '/api/collection/export?format=json'
    content=[]
    for row in rows:
        sid=row['Session ID'];links=[]
        for photo in row['photos']:
            pid=photo['id']
            url=f'photos/{sid}/{pid}.png' if offline else f'/api/sessions/{sid}/pages/{pid}/image'
            links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(photo["kind"].replace("_"," "))}</a>')
        record=f'records/{sid}.json' if offline else f'/api/sessions/{sid}/export'
        links.append(f'<a href="{esc(record)}">Record / OCR</a>')
        cells=''.join(f'<td>{esc(row[key] or "—")}</td>' for key in ('Book','L1','L2','L3','Source','Status'))
        reviewed=' / '.join(row[key] or '—' for key in ('Reviewed L1','Reviewed L2','Reviewed L3'))
        candidates=[]
        for level in (1,2,3):
            label=row.get(f'Suggested L{level}')
            if not label:continue
            score=row.get(SCORE_COLUMNS[level],'')
            candidates.append(f'L{level}: {esc(label)}'+(f' ({esc(score)}%)' if score!='' else ''))
        content.append('<tr>'+cells+'<td>'+('<br>'.join(candidates) or '—')+'</td><td>'+esc(reviewed)+'</td><td>'+ ' · '.join(links)+'</td></tr>')
    if not content:content=['<tr><td colspan="9">No books saved yet.</td></tr>']
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="10"><title>Book classification results</title>
<style>body{font:16px system-ui,sans-serif;margin:24px;color:#203247;background:#f8fafb}h1{font:28px Georgia,serif}a{color:#244e74}nav{display:flex;gap:20px;margin:20px 0}.table{overflow:auto}table{border-collapse:collapse;width:100%;background:white}th,td{padding:15px;text-align:left;border-bottom:1px solid #dbe1e7;vertical-align:top}th{white-space:nowrap}td:nth-child(2),td:nth-child(3),td:nth-child(4){font-family:monospace;font-size:20px}p{max-width:900px;line-height:1.5}</style></head><body>
<h1>Book classification results</h1><p>Saved on the connected laptop. This view refreshes every 10 seconds. A dash means no supported code is available. Catalog codes, model suggestions and recorded manual reviews are separate; all assignments need confirmation.</p>
<nav>'''+('' if offline else '<a href="/">Return to capture</a>')+f'<a href="{csv_url}">Download CSV</a><a href="{json_url}">Download JSON</a></nav>'+'''
<div class="table"><table><thead><tr><th>Book</th><th>L1</th><th>L2</th><th>L3</th><th>Source</th><th>Status</th><th>Provisional model / scores</th><th>Recorded review</th><th>Evidence</th></tr></thead><tbody>'''+''.join(content)+'''</tbody></table></div>
<p>Provisional model codes can appear below review thresholds and may be wrong. Their scores are uncalibrated; L2/L3 scores are conditional on the predicted parent, not full-path accuracy. The main L1/L2/L3 columns retain threshold-qualified or catalog codes. The CSV includes session IDs, revisions, languages and review evidence revisions. Import DDC columns as text to preserve leading zeros. Records include raw OCR, model alternatives, decisions and review history. Pending uploads remain on the phone until the server saves them.</p></body></html>'''


def atomic_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(data,str):data=data.encode('utf-8')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'-',delete=False) as handle:
            temporary=Path(handle.name);handle.write(data)
        os.replace(str(temporary),str(path))
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def sync_session(store,session,image=None,force_images=False):
    root=store.export_root;sid=safe_id(session['id'])
    atomic_write(root/'records'/f'{sid}.json',json.dumps(session,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    photo_root=root/'photos'/sid
    live=set()
    for page in session['pages']:
        if page.get('source')!='ocr':continue
        pid=safe_id(page['id']);live.add(pid+'.png');path=photo_root/(pid+'.png')
        if image is not None and image[0]==pid:
            atomic_write(path,image[1])
        elif force_images or not path.exists():
            body=store.image(sid,pid)
            if body is not None and (not path.exists() or path.read_bytes()!=body):atomic_write(path,body)
    if photo_root.exists():
        for path in photo_root.glob('*.png'):
            if path.name not in live:path.unlink()


def remove_session(store,sid):
    sid=safe_id(sid)
    (store.export_root/'records'/f'{sid}.json').unlink(missing_ok=True)
    photos=store.export_root/'photos'/sid
    if photos.exists():shutil.rmtree(photos)


def sync_table(store):
    rows=collection_rows(store);root=store.export_root
    atomic_write(root/'classifications.csv',csv_text(rows))
    atomic_write(root/'classifications.json',json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    atomic_write(root/'classifications.html',html_table(rows,offline=True))


def rebuild(store):
    sessions=store.list();live={safe_id(s['id']) for s in sessions}
    for session in sessions:sync_session(store,session,force_images=True)
    if (store.export_root/'records').exists():
        for path in (store.export_root/'records').glob('*.json'):
            if path.stem not in live:remove_session(store,path.stem)
    sync_table(store)
