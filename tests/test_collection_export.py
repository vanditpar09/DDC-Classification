import csv
import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from prototype.collection_export import collection_rows, csv_text, html_table, model_fields
from prototype.engine import Engine
from prototype.storage import SQLiteStore


def prediction(text):
    return {'label':'000','score':.4,'margin':.02,'top3':[],'truncated':False,
            'hierarchy':{'review_level':0,'target_level':3,'path':[
                {'level':1,'label':'000','supported':True},
                {'level':2,'label':'000','supported':True},
                {'level':3,'label':'005','supported':True}]}}


def make_engine(tmp_path,recognizer=None):
    return Engine(predictor=prediction,recognizer=recognizer,store=SQLiteStore(tmp_path/'books.sqlite3'))


def photo():
    buffer=io.BytesIO();Image.new('RGB',(10,12),'white').save(buffer,'PNG');return buffer.getvalue()


def test_saved_photo_text_and_three_levels_automatically_export(tmp_path):
    def read(*args,**kwargs):
        return {'text':'Computer science','words':[],'usable':True,'quality':{},
                'work':{'ocr_passes':1,'pixels':120,'seconds':.01}}
    engine=make_engine(tmp_path,read);sid=engine.new_session()['id']
    state=engine.add_image(sid,'cover',photo(),'eng')
    root=engine.store.export_root
    row=json.loads((root/'classifications.json').read_text())[0]
    assert [row[c] for c in ('Book','L1','L2','L3')]==['Computer science','000','000','005']
    assert row['Source']=='Model suggestion'
    saved=Image.open(root/'photos'/sid/(state['pages'][0]['id']+'.png'))
    assert saved.size==(10,12)
    assert json.loads((root/'records'/f'{sid}.json').read_text())==state
    assert 'Computer science' in (root/'classifications.html').read_text()
    csv_row=next(csv.DictReader(io.StringIO((root/'classifications.csv').read_text())))
    assert csv_row['L3']=='005'


def test_rejected_ocr_is_saved_with_no_guessed_code(tmp_path):
    def rejected(*args,**kwargs):
        return {'text':'Partial Hindi','words':[],'usable':False,'quality':{'word_count':0},
                'work':{'ocr_passes':1,'pixels':120,'seconds':.01}}
    engine=make_engine(tmp_path,rejected);sid=engine.new_session()['id']
    state=engine.add_image(sid,'cover',photo(),'eng+hin')
    row=collection_rows(engine.store)[0]
    assert [row[k] for k in ('L1','L2','L3')]==['','','']
    assert row['Status']=='Capture a clearer image'
    assert (engine.store.export_root/'photos'/sid/(state['pages'][0]['id']+'.png')).exists()


def test_review_stays_separate_from_predicted_path(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    before=engine.add_text(sid,'cover','भारत का इतिहास','eng+hin')
    state=engine.add_review(sid,'954','Team reviewer','Catalog evidence','')
    row=collection_rows(engine.store)[0]
    assert row['L3']=='005' and row['Reviewed L3']=='954'
    assert row['Review evidence revision']==before['revision']
    assert json.loads((engine.store.export_root/'records'/f'{sid}.json').read_text())==state


def test_restart_rebuilds_derived_files_without_reclassification(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    state=engine.add_text(sid,'cover','गणित','eng+hin')
    root=engine.store.export_root
    (root/'classifications.csv').unlink()
    restored=SQLiteStore(tmp_path/'books.sqlite3')
    assert restored.get(sid)==state
    assert (root/'classifications.csv').exists()
    assert collection_rows(restored)[0]['Book']=='गणित'


def test_deletion_removes_summary_row_record_and_photo_copy(tmp_path):
    def read(*args,**kwargs):
        return {'text':'A book','words':[],'usable':True,'quality':{},'work':{'ocr_passes':1,'pixels':120,'seconds':.01}}
    engine=make_engine(tmp_path,read);sid=engine.new_session()['id']
    engine.add_image(sid,'cover',photo(),'eng');root=engine.store.export_root
    engine.delete(sid)
    assert json.loads((root/'classifications.json').read_text())==[]
    assert not (root/'photos'/sid).exists()
    assert not (root/'records'/f'{sid}.json').exists()


def test_export_failure_does_not_lose_saved_capture(tmp_path,monkeypatch):
    from prototype import collection_export
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    def denied(*args,**kwargs):raise PermissionError('fixture disk failure')
    monkeypatch.setattr(collection_export,'atomic_write',denied)
    state=engine.add_text(sid,'cover','A saved book','eng')
    assert engine.store.get(sid)==state
    assert 'fixture disk failure' in engine.store.export_error


def test_collection_api_and_html_escape_untrusted_titles(tmp_path,monkeypatch):
    import prototype.app as module
    engine=make_engine(tmp_path);monkeypatch.setattr(module,'engine',engine)
    client=TestClient(module.app);sid=client.post('/api/sessions').json()['id']
    title='<script>alert(1)</script>'
    client.post(f'/api/sessions/{sid}/text',json={'kind':'cover','text':title,'language':'eng'})
    response=client.get('/api/collection')
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert '<script>' not in response.text and '&lt;script&gt;' in response.text
    assert client.get('/api/collection/export?format=json').json()[0]['Book']==title
    assert '005' in client.get('/api/collection/export?format=csv').text
    assert client.get('/api/collection/export?format=invalid').status_code==400
    assert 'Results table' in client.get('/').text


def test_csv_does_not_execute_source_titles_as_formulas(tmp_path):
    engine=make_engine(tmp_path);sid=engine.new_session()['id']
    engine.add_text(sid,'cover','=UNTRUSTED()','eng')
    csv_row=next(csv.DictReader(io.StringIO(csv_text(collection_rows(engine.store)))))
    assert csv_row['Book']=="'=UNTRUSTED()"
    assert collection_rows(engine.store)[0]['Book']=='=UNTRUSTED()'


def test_new_image_bytes_update_same_page_export(tmp_path):
    store=SQLiteStore(tmp_path/'books.sqlite3')
    session={'id':'book','updated':1,'revision':1,'combined_text':'Book','prediction':None,
             'pages':[{'id':'page','kind':'cover','language':'eng','source':'ocr'}]}
    store.save(session,('page',b'first'))
    store.save(session,('page',b'second'))
    assert (store.export_root/'photos/book/page.png').read_bytes()==b'second'


def test_low_score_candidates_export_without_becoming_qualified_codes(tmp_path):
    from src.ocr_pipeline.catalog import suppress_uncertain_path
    raw=prediction('')
    for item,score in zip(raw['hierarchy']['path'],(.4,.35,.8)):
        item.update(score=score,margin=.02,review_ready=False)
    engine=make_engine(tmp_path)
    engine.predictor=lambda text:suppress_uncertain_path(raw)
    sid=engine.new_session()['id'];engine.add_text(sid,'cover','A low-score book','eng')
    row=collection_rows(engine.store)[0]
    assert [row[f'L{i}'] for i in (1,2,3)]==['','','']
    assert [row[f'Suggested L{i}'] for i in (1,2,3)]==['000','000','005']
    assert row['L1 model score (%)']==40 and row['L3 conditional score (%)']==80
    assert 'Provisional model / scores' in html_table([row])
    assert 'L3: 005 (80.0%)' in html_table([row])


def test_catalog_codes_never_become_fabricated_model_scores():
    assert all(value=='' for value in model_fields({'label':'800','result_source':'local_catalog'}).values())


def test_missing_branch_and_nonfinite_score_remain_unavailable():
    fields=model_fields({'hierarchy':{'path':[
        {'level':1,'label':'000','supported':True,'score':0},
        {'level':2,'label':None,'supported':False,'score':.9},
        {'level':3,'label':'005','supported':True,'score':float('nan')}]}})
    assert fields['L1 model score (%)']==0
    assert fields['Suggested L2']=='' and fields['L2 conditional score (%)']==''
    assert fields['L3 conditional score (%)']==''
