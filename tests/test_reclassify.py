import copy
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from prototype.engine import Engine
from prototype.storage import SQLiteStore


def old_prediction(text):
    return {'label':'800','score':.49,'margin':.1,'top3':[],'truncated':False,
            'hierarchy':{'review_level':0,'target_level':3,'path':[
                {'level':i,'label':code,'supported':True} for i,code in enumerate(('800','820','823'),1)]}}


def corrected_prediction(text):
    from src.ocr_pipeline.catalog import apply_catalog
    return apply_catalog(old_prediction(text),{'status':'matched','edition_review_required':True,
        'record':{'title':'Test Book','authors':['Test Author'],'section':'813','ddc_raw':['813.52']}})


def make_engine(tmp_path):
    def read(*args,**kwargs):
        return {'text':'Test Book by Test Author','usable':True,'words':[],'quality':{},
                'work':{'ocr_passes':1,'pixels':100,'seconds':.01}}
    return Engine(predictor=old_prediction,recognizer=read,store=SQLiteStore(tmp_path/'books.sqlite3'))


def test_update_preserves_images_ocr_reviews_and_prior_prediction(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    image=io.BytesIO();Image.new('RGB',(10,10),'white').save(image,'PNG')
    engine.add_image(sid,'cover',image.getvalue(),'eng')
    engine.add_review(sid,'813','Reviewer','Source-backed review','')
    before=copy.deepcopy(engine.get(sid));pid=before['pages'][0]['id'];photo=engine.store.image(sid,pid)
    engine.predictor=corrected_prediction
    after=engine.reclassify(sid)
    assert [r['label'] for r in after['prediction']['hierarchy']['path']]==['800','810','813']
    assert after['prediction_history'][-1]['prediction']==before['prediction']
    assert after['pages']==before['pages'] and after['reviews']==before['reviews']
    assert after['combined_text']==before['combined_text']
    assert after['work']['ocr_passes']==before['work']['ocr_passes']
    assert engine.store.image(sid,pid)==photo
    assert after['work']['classifier_calls']==before['work']['classifier_calls']+1
    assert SQLiteStore(tmp_path/'books.sqlite3').get(sid)==after


def test_failed_update_retains_previous_result_and_evidence(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    before=copy.deepcopy(engine.add_text(sid,'cover','Test book','eng'))
    def fail(text):raise RuntimeError('Fixture inference failure')
    engine.predictor=fail
    with pytest.raises(RuntimeError):engine.reclassify(sid)
    saved=engine.store.get(sid)
    assert saved['prediction']==before['prediction'] and saved['pages']==before['pages']
    assert saved['events'][-1]['status']=='failed'


def test_empty_book_cannot_consume_a_classifier_call(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    before=copy.deepcopy(engine.get(sid))
    with pytest.raises(ValueError,match='readable evidence'):engine.reclassify(sid)
    assert engine.get(sid)==before


def test_api_update_is_revision_checked_and_replay_safe(tmp_path,monkeypatch):
    import prototype.app as module
    engine=make_engine(tmp_path);monkeypatch.setattr(module,'engine',engine)
    client=TestClient(module.app);sid=client.post('/api/sessions').json()['id']
    state=client.post(f'/api/sessions/{sid}/text',json={'kind':'cover','text':'Test book','language':'eng'}).json()
    engine.predictor=corrected_prediction
    headers={'Idempotency-Key':'reclassify-fixture','X-Book-Revision':str(state['revision'])}
    response=client.post(f'/api/sessions/{sid}/reclassify',headers=headers)
    assert response.status_code==200
    after=response.json()
    assert client.post(f'/api/sessions/{sid}/reclassify',headers=headers).json()==after
    assert after['work']['classifier_calls']==2
    assert client.post(f'/api/sessions/{sid}/reclassify',headers={'X-Book-Revision':str(state['revision'])}).status_code==409
    assert 'Update prediction' in client.get('/').text
