"""Functional localhost OCR/model checks; these do not measure phone accuracy."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request,urlopen
import uuid

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8013'
OUT=ROOT/'data/research/multilingual-pilot-v1/experiment-v2'


def request(path,body=None,content_type='application/json'):
    req=Request(BASE+path,data=body,headers={'Content-Type':content_type,'Origin':BASE},method='POST' if body is not None else 'GET')
    with urlopen(req,timeout=120) as response:return json.load(response)


def run():
    status=request('/api/status')
    assert status['model_version']['name']=='native_silver_v2'
    assert status['model_version']['experimental']
    books=list(map(json.loads,(ROOT/'data/research/multilingual-pilot-v1/silver-pilot-v2/books.jsonl').read_text().splitlines()))
    reviewed={b['work_id']:b for b in map(json.loads,(ROOT/'data/research/multilingual-pilot-v1/review-v3/reviewed-books.jsonl').read_text().splitlines())}
    selected=['ncert-fhgp1','esahity-anand_madhu_shirgaonkar','pm-work-118']
    rows=[]
    for wid in selected:
        b=next(x for x in books if x['work_id']==wid)
        assert b['assigned_partition']=='development'
        sample=b['samples'][0]
        image=sample['provenance'].get('image_file')
        if image:image=ROOT/image
        else:image=ROOT/'data/research/multilingual-pilot-v1/review-v3'/reviewed[wid]['source_page_checks'][0]['image_file']
        sid=request('/api/sessions',b'{}')['id']
        boundary='ddc-local-'+uuid.uuid4().hex
        parts=[]
        for key,value in [('kind','cover'),('language','eng+'+b['language'])]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="page.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+image.read_bytes()+b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        result=request(f'/api/sessions/{sid}/image',b''.join(parts),'multipart/form-data; boundary='+boundary)
        pred=result.get('prediction');assert pred,'OCR did not produce a classifier input'
        assert pred['model_version']==status['model_version']
        hierarchy=pred['hierarchy'];assert hierarchy['review_level']==0
        known=[x for x in hierarchy['path'] if x.get('label')]
        for a,c in zip(known,known[1:]):assert c['label'][:a['level']]==a['label'][:a['level']]
        assert all(not x['review_ready'] for x in hierarchy['path'])
        # One recognition pass plus the prototype's optional script diagnostic.
        assert 1 <= result['work']['ocr_passes'] <= 2
        row=dict(work_id=wid,language=b['language'],session_id=sid,source_image=str(image.relative_to(ROOT)),
                 source_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),expected_silver_section=b['silver_section'],
                 suggested_path=[x.get('label') for x in hierarchy['path']],model_version=pred['model_version'],
                 ocr_passes=result['work']['ocr_passes'],token_count=pred['token_count'],truncated=pred['truncated'],
                 functional_only=True,physical_phone_test=False,reference_is_ground_truth=False)
        rows.append(row)
        (OUT/(wid+'-local-trace.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(row,ensure_ascii=False),flush=True)
    (OUT/'local-server-smoke.json').write_text(json.dumps(dict(status=status,checks=rows,passed=True,
        note='Real OCR on rendered PDF pages. Body pages entered through the capture API; these are not photographed covers or a camera benchmark.'),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':run()
