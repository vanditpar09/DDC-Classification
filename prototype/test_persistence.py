"""Recovery/duplicate/concurrency checks, using tiny deterministic OCR fixtures."""
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from prototype.engine import Engine, Conflict
from prototype.storage import SQLiteStore


def prediction(text):
    return {'label':'000','score':.4,'margin':.02,'top3':[], 'truncated':False}


def recognize(*args, **kwargs):
    return {'text':'Book evidence','usable':True,'words':[], 'quality':{},
            'work':{'ocr_passes':1,'pixels':100,'seconds':.1}}


def photo():
    data=io.BytesIO()
    Image.new('RGB',(10,10),'white').save(data,'PNG')
    return data.getvalue()


def make_engine(path, predictor=prediction, recognizer=recognize):
    return Engine(predictor=predictor, recognizer=recognizer, store=SQLiteStore(path))


def test_image_and_books_survive_restart_and_do_not_expire(tmp_path):
    path=tmp_path/'books.sqlite3'
    engine=make_engine(path)
    sid=engine.new_session()['id']
    state=engine.add_image(sid,'cover',photo(),'eng')
    state['updated']=0
    engine.store.save(state)
    recovered=make_engine(path)
    recovered.new_session()
    assert len(recovered.list_sessions())==2
    assert recovered.get(sid)['combined_text']=='Book evidence'
    assert recovered.get_image(sid,state['pages'][0]['id']).size==(10,10)
    state=recovered.repair(sid,state['pages'][0]['id'])
    assert state['pages'][0]['repairs']==1
    assert state['work']['ocr_passes']==2


def test_replacement_keeps_history_and_removes_old_image(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    first=engine.add_image(sid,'cover',photo(),'eng')
    pid=first['pages'][0]['id']
    state=engine.add_text(sid,'cover','Corrected Hindi: भारत','eng+hin')
    assert state['page_history'][0]['page']['text']=='Book evidence'
    assert engine.store.image(sid,pid) is None
    assert 'भारत' in state['combined_text']


def test_lost_response_replay_after_restart_does_not_repeat_work(tmp_path):
    path=tmp_path/'books.db'
    engine=make_engine(path)
    sid=engine.new_session()['id']
    first=engine.execute(sid,'upload-123','image-hash',0,lambda:engine.add_image(sid,'cover',photo(),'eng'))
    recovered=make_engine(path)
    state=recovered.execute(sid,'upload-123','image-hash',0,lambda:pytest.fail('Repeated OCR'))
    assert state==first
    with pytest.raises(Conflict,match='different evidence'):
        recovered.execute(sid,'upload-123','different',0,lambda:None)


def test_stale_revision_conflicts_without_overwriting_newer_page(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    engine.execute(sid,'operation-one','one',0,lambda:engine.add_text(sid,'cover','New title','eng'))
    with pytest.raises(Conflict,match='changed'):
        engine.execute(sid,'operation-two','two',0,lambda:engine.add_text(sid,'cover','Old title','eng'))
    assert engine.get(sid)['combined_text']=='New title'


def test_replaying_an_old_success_does_not_silently_rebase_pending_edits(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    engine.execute(sid,'operation-first','one',0,lambda:engine.add_text(sid,'cover','Original','eng'))
    engine.add_text(sid,'cover','Newer edit on another device','eng')
    with pytest.raises(Conflict,match='was saved'):
        engine.execute(sid,'operation-first','one',0,lambda:pytest.fail('Repeated work'))


def test_two_concurrent_edits_cannot_share_one_revision(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    def submit(n):
        try:
            engine.execute(sid,f'operation-{n}',str(n),0,lambda:engine.add_text(sid,'cover',f'Title {n}','eng'))
            return 'saved'
        except Conflict:
            return 'conflict'
    with ThreadPoolExecutor(2) as workers:
        assert sorted(workers.map(submit,[1,2]))==['conflict','saved']
    assert engine.get(sid)['work']['classifier_calls']==1


def test_failed_classifier_retains_ocr_evidence_cost_and_image(tmp_path):
    def broken(text):
        raise RuntimeError('Classifier offline')
    path=tmp_path/'books.db'
    engine=make_engine(path,predictor=broken)
    sid=engine.new_session()['id']
    with pytest.raises(RuntimeError):
        engine.execute(sid,'upload-fail','hash',0,lambda:engine.add_image(sid,'cover',photo(),'eng'))
    recovered=make_engine(path)
    state=recovered.get(sid)
    assert state['work']['ocr_passes']==1
    assert state['work']['classifier_calls']==1
    assert state['prediction'] is None
    assert state['combined_text']=='Book evidence'
    assert recovered.get_image(sid,state['pages'][0]['id']).size==(10,10)
    with pytest.raises(Conflict,match='did not complete'):
        recovered.execute(sid,'upload-fail','hash',0,lambda:pytest.fail('Repeated work'))


def test_failed_ocr_reserves_budget_across_restart(tmp_path):
    def broken(*args,**kwargs):
        raise ValueError('OCR timed out')
    path=tmp_path/'books.db'
    engine=make_engine(path,recognizer=broken)
    sid=engine.new_session()['id']
    with pytest.raises(ValueError):
        engine.add_image(sid,'cover',photo(),'eng')
    state=make_engine(path).get(sid)
    assert state['work']['ocr_passes']==2
    assert state['events'][-1]['status']=='failed'
    assert state['decision']['action']=='human_review'


def test_unfinished_receipt_after_restart_is_not_automatically_reexecuted(tmp_path):
    path=tmp_path/'books.db'
    engine=make_engine(path)
    sid=engine.new_session()['id']
    engine.store.record(sid,'upload-pending',{'fingerprint':'hash','status':'pending'})
    with pytest.raises(Conflict):
        make_engine(path).execute(sid,'upload-pending','hash',0,lambda:pytest.fail('Repeated work'))


def test_review_keeps_model_prediction_and_unicode_source(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    before=engine.add_text(sid,'cover','भारत का इतिहास','eng+hin')
    state=engine.add_review(sid,'954','Librarian','स्रोत','ISBN-123')
    review=state['reviews'][0]
    assert (review['class'],review['division'],review['section'])==('900','950','954')
    assert review['evidence_revision']==before['revision']
    assert review['note']=='स्रोत'
    assert state['prediction']==before['prediction']
    assert state['work']==before['work']


def test_delete_removes_images_and_operation_receipts(tmp_path):
    engine=make_engine(tmp_path/'books.db')
    sid=engine.new_session()['id']
    state=engine.execute(sid,'upload-delete','hash',0,lambda:engine.add_image(sid,'cover',photo(),'eng'))
    engine.delete(sid)
    assert engine.store.get(sid) is None
    assert engine.store.receipt(sid,'upload-delete') is None
    assert engine.store.image(sid,state['pages'][0]['id']) is None


def test_api_idempotency_review_and_private_cache_headers(tmp_path,monkeypatch):
    import prototype.app as module
    monkeypatch.setattr(module,'engine',make_engine(tmp_path/'books.db'))
    client=TestClient(module.app)
    sid=client.post('/api/sessions').json()['id']
    headers={'Idempotency-Key':'request-first','X-Book-Revision':'0','Origin':'http://testserver'}
    data={'kind':'cover','text':'Programming','language':'eng'}
    first=client.post(f'/api/sessions/{sid}/text',json=data,headers=headers)
    second=client.post(f'/api/sessions/{sid}/text',json=data,headers=headers)
    assert first.status_code==200 and second.json()==first.json()
    assert client.get('/api/sessions').json()[0]['id']==sid
    assert client.get(f'/api/sessions/{sid}/export').headers['cache-control']=='no-store'
    assert client.post(f'/api/sessions/{sid}/review',json={'section':'005','reviewer':'Librarian'}).status_code==200
    assert client.post(f'/api/sessions/{sid}/review',json={'section':'5','reviewer':'Librarian'}).status_code==422
    assert client.post('/api/sessions',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/status',headers={'Host':'evil.example'}).status_code==400
    assert client.get('/api/sessions/no-such-book').status_code==404


def test_pwa_assets_are_served(monkeypatch):
    import prototype.app as module
    client=TestClient(module.app)
    for asset in ('/manifest.webmanifest','/sw.js','/camera.js','/local-store.js','/icon-192.png','/icon-512.png'):
        assert client.get(asset).status_code==200
    assert client.get('/manifest.webmanifest').json()['display']=='standalone'
