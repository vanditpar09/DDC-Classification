"""Data leakage, Unicode windows, rare fallback and book-weighted reporting."""
import hashlib
import json

import numpy as np
import pytest

from src.research.collection import assign_partition, prepare, validate_records
from src.research.evaluate import edit_distance, load_prepared, ocr_errors, summarize
from src.research.page_windows import page_chunks, predict_pages
from tests.test_hierarchy import model, OTHER, Head


def book(book_id='BOOK1',work_id='WORK1'):
    return {'book_id':book_id,'work_id':work_id,'catalog_ids':[],'language':'hin','title':'कंप्यूटर',
            'review_status':'verified','section':'005','reviewer':'Librarian','label_source':'Catalog accession 1',
            'capture_permission':True,'pages':[{'kind':'cover','origin':'human_transcription',
              'image_path':'','reference_text':'कंप्यूटर प्रोग्रामिंग','ocr_text':''}]}


@pytest.mark.parametrize('field,value',[('review_status','pending'),('section',5),('section','05'),
    ('reviewer',''),('work_id',''),('label_source',''),('capture_permission',False),('language','unknown')])
def test_only_reviewed_identified_native_books_enter_collection(tmp_path,field,value):
    row=book();row[field]=value
    with pytest.raises(ValueError):validate_records([row],tmp_path)


def test_synthetic_translation_and_unconfirmed_photos_rejected(tmp_path):
    for origin in ('synthetic','machine_translation','native_scan'):
        row=book();row['pages'][0]['origin']=origin
        with pytest.raises(ValueError):validate_records([row],tmp_path)


def test_image_hash_duplicates_and_paths_cannot_escape_collection(tmp_path):
    (tmp_path/'image.png').write_bytes(b'fixture')
    a=book();a['pages'][0].update(origin='native_scan',image_path='image.png')
    b=book('BOOK2','WORK2');b['pages'][0].update(origin='native_scan',image_path='image.png')
    assert validate_records([a],tmp_path)[0]['pages'][0]['image_sha256']==hashlib.sha256(b'fixture').hexdigest()
    with pytest.raises(ValueError,match='same image'):validate_records([a,b],tmp_path)
    a['pages'][0]['image_path']='../outside.png'
    with pytest.raises(ValueError,match='within'):validate_records([a],tmp_path)


def test_related_editions_translations_and_known_holdout_never_cross_partitions(tmp_path,monkeypatch):
    import src.research.collection as module
    monkeypatch.setattr(module,'known_catalog',lambda:([],{'KNOWN':{'test'}}))
    rows=[book('A','SAME'),book('B','SAME'),book('C','OLD')]
    rows[1]['language']='mar';rows[2]['catalog_ids']=['KNOWN']
    source=tmp_path/'reviewed.jsonl';source.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    out=tmp_path/'prepared';report=prepare(source,out)
    saved=[json.loads(l) for l in (out/'books.jsonl').read_text().splitlines()]
    assert saved[0]['partition']==saved[1]['partition']==assign_partition('SAME')
    assert saved[2]['partition']=='development'
    training=[json.loads(l) for l in (out/'training-input.jsonl').read_text().splitlines()]
    assert all(r['document_id']!='C' for r in training)
    assert report['work_groups']==2
    assert load_prepared(out)[0]==saved
    with pytest.raises(FileExistsError):prepare(source,out)
    (out/'books.jsonl').write_text('{}\n')
    with pytest.raises(ValueError,match='changed'):load_prepared(out)


def test_shared_catalog_aliases_and_duplicate_pages_require_work_resolution(tmp_path):
    a,b=book('A','X'),book('B','Y')
    a['catalog_ids']=b['catalog_ids']=['SAME-WORK']
    with pytest.raises(ValueError,match='conflicting work'):validate_records([a,b],tmp_path)
    a,b=book('A','X'),book('B','Y')
    a['pages'][0]['reference_text']=b['pages'][0]['reference_text']='एक समान लंबा विवरण '*10
    with pytest.raises(ValueError,match='identical page'):validate_records([a,b],tmp_path)


class CharacterTokenizer:
    def encode(self,text,**kwargs):return [0]* (len(text)+2)
    def __call__(self,text,**kwargs):return {'offset_mapping':[(i,i+1) for i in range(len(text))]}


def test_page_windows_keep_late_pages_and_combining_marks_with_bounded_cost():
    pages=[{'kind':'cover','text':'कंप्यूटर '+ 'A'*800},
           {'kind':'contents','text':'தமிழ் algorithms data structures'}]
    chunks,audit=page_chunks(pages,CharacterTokenizer(),max_tokens=96,max_chunks_per_page=2)
    assert len(chunks)==3
    assert set(c['kind'] for c in chunks)=={'cover','contents'}
    assert all(c['tokens']<=96 for c in chunks)
    assert sum(c['weight'] for c in chunks)==pytest.approx(1)
    assert sum(c['weight'] for c in chunks if c['kind']=='cover')==pytest.approx(.5)
    assert chunks[-1]['text']=='தமிழ் algorithms data structures'
    assert audit[0]['omitted_tail'] and not audit[1]['omitted_tail']


def test_short_page_output_exactly_matches_saved_baseline():
    m=model();page={'kind':'cover','text':'कंप्यूटर'}
    result=predict_pages(m,[page],CharacterTokenizer())
    assert result['hierarchy']==m.predict_hierarchy([page['text']])[0]
    assert not result['experimental_pooling']


def test_joint_pooling_is_parent_consistent_and_never_claims_calibrated_review():
    m=model()
    result=predict_pages(m,[{'kind':'cover','text':'programming'},
        {'kind':'contents','text':'algorithms'}],CharacterTokenizer())
    path=result['hierarchy']['path']
    assert [p['label'] for p in path]==['000','000','005']
    assert all(not p['review_ready'] for p in path)
    assert result['hierarchy']['review_level']==0
    assert [p['path_score'] for p in path]==sorted([p['path_score'] for p in path],reverse=True)
    assert sum(c['score'] for c in path[1]['top3'])==pytest.approx(1)
    m.heads[2]['000']=Head(['000',OTHER],3.)
    path=predict_pages(m,[{'kind':'cover','text':'A'},{'kind':'contents','text':'B'}],CharacterTokenizer())['hierarchy']['path']
    assert len(path)==2 and path[-1]['label'] is None


def test_parent_mass_weighting_prevents_children_of_unlikely_parent_dominating():
    m=model()
    m.level1.predict_proba=lambda texts:np.array([[.99,.01],[.01,.99]])
    class VariableHead:
        classes_=np.array(['000','020'])
        def decision_function(self,X):return np.array([-5.,5.])
    m.heads[2]['000']=VariableHead()
    # Break the pooled L1 tie toward 000 by making its aggregate slightly larger.
    m.level1.predict_proba=lambda texts:np.array([[.99,.01],[.02,.98]])
    path=predict_pages(m,[{'kind':'cover','text':'A'},{'kind':'contents','text':'B'}],CharacterTokenizer())['hierarchy']['path']
    assert path[1]['label']=='000'
    assert path[1]['score']>.95  # Uniform conditional averaging would be 0.5.


def test_book_groups_not_duplicate_editions_control_reported_accuracy():
    good={'section':'005','work_id':'same','hierarchy':{'path':[{'level':1,'label':'000'}]},'seconds':0,'omitted_text':False}
    bad={**good,'work_id':'other','hierarchy':{'path':[{'level':1,'label':'900'}]}}
    report=summarize([good,good,bad])
    assert report['work_groups']==2
    assert report['levels']['1']['accuracy']==.5
    assert report['levels']['3']['abstention_rate']==1


def test_unicode_cer_wer_and_empty_ocr_count_as_failure():
    assert edit_distance('kitten','sitting')==3
    assert edit_distance('', 'भारत')==4
    page={'origin':'native_scan','reference_text':'भारत इतिहास','ocr_text':'भारत इतिहास'}
    assert ocr_errors([page])['cer']==0
    page['ocr_text']=''
    assert ocr_errors([page])['cer']==1
    assert ocr_errors([page])['wer']==1


def test_ocr_collection_keeps_references_and_records_failures(tmp_path,monkeypatch):
    import src.research.collect_ocr as module
    a,b=book('A','ONE'),book('B','TWO')
    (tmp_path/'a.png').write_bytes(b'A');(tmp_path/'b.png').write_bytes(b'B')
    for row,name in ((a,'a.png'),(b,'b.png')):row['pages'][0].update(origin='native_scan',image_path=name)
    source=tmp_path/'reviewed.jsonl';source.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in (a,b)))
    monkeypatch.setattr(module,'image_from_bytes',lambda b:b)
    def recognize(image,language,*args,**kwargs):
        assert language=='eng+hin' and kwargs['allow_osd'] is False
        if image==b'B':raise ValueError('OCR timeout')
        return {'text':'कंप्यूटर','quality':{},'work':{'ocr_passes':1}}
    monkeypatch.setattr(module,'recognize',recognize)
    output=tmp_path/'raw-ocr.jsonl';report=module.collect(source,output)
    saved=[json.loads(l) for l in output.read_text().splitlines()]
    assert report['empty_or_failed_pages']==1
    assert saved[0]['pages'][0]['reference_text']==a['pages'][0]['reference_text']
    assert saved[1]['pages'][0]['ocr_text']==''
    assert saved[1]['pages'][0]['ocr_run']['error']=='OCR timeout'
    assert source.read_text().count('OCR timeout')==0
    with pytest.raises(ValueError,match='new output'):module.collect(source,output)


def test_alias_matching_prevents_old_test_work_entering_training(tmp_path,monkeypatch):
    import src.research.collection as module
    monkeypatch.setattr(module,'known_catalog',lambda:([],{'OL123W':{'test'},'9781234567890':{'test'}}))
    a,b=book('A','ONE'),book('B','TWO')
    a['catalog_ids']=['https://openlibrary.org/works/OL123W'];b['catalog_ids']=['978-1-234-56789-0']
    source=tmp_path/'reviewed.jsonl';source.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in (a,b)))
    report=prepare(source,tmp_path/'prepared')
    assert report['by_partition']=={'development':2}


def test_complete_evaluator_pairs_views_and_keeps_locked_test_deliberate(tmp_path,monkeypatch):
    import src.research.collection as collection
    import src.research.evaluate as evaluation
    monkeypatch.setattr(collection,'known_catalog',lambda:([],{'KNOWN':{'test'}}))
    row=book();row['catalog_ids']=['KNOWN']
    row['pages'] += [{**row['pages'][0],'kind':'back_cover','reference_text':'Algorithms'},
                      {**row['pages'][0],'kind':'contents','reference_text':'Databases'}]
    source=tmp_path/'reviewed.jsonl';source.write_text(json.dumps(row,ensure_ascii=False)+'\n')
    prepared=tmp_path/'prepared';prepare(source,prepared)
    artifact=tmp_path/'model.joblib';artifact.write_bytes(b'test model')
    monkeypatch.setattr(evaluation.joblib,'load',lambda path:model())
    class Encoder:tokenizer=CharacterTokenizer()
    monkeypatch.setattr(evaluation,'get_encoder',lambda path:Encoder())
    out=tmp_path/'evaluation';result=evaluation.evaluate(prepared,artifact,out)
    assert result['comparisons']==12
    metrics=json.loads((out/'metrics.json').read_text())
    assert metrics['summary']['reference:all_pages:page_windows']['overall']['levels']['3']['accuracy']==1
    assert metrics['summary']['ocr:all_pages:baseline']['overall']['books']==0
    assert metrics['missing_data']['ocr:all_pages']['missing_required_pages_or_text']==1
    assert metrics['summary']['reference:cover:baseline']['by_language']['tam']['books']==0
    with pytest.raises(ValueError,match='Locked test'):evaluation.evaluate(prepared,artifact,tmp_path/'locked','test')
