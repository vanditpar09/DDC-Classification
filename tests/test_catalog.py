import copy
import pytest
from src.ocr_pipeline.catalog import match_catalog, apply_catalog, suppress_uncertain_path, section_from_codes


def entry(title='Test of Geometry',author='Asha Rao',section='510'):
    return {'id':title,'title':title,'authors':[author],'section':section,'ddc_raw':[section] if section else [],'source_urls':['https://openlibrary.org/']}


def page(text,words=None,kind='cover'):
    return {'id':'p','kind':kind,'text':text,'usable':True,'words':words or []}


def test_identity_requires_both_title_and_author_and_cover():
    record=entry()
    for text in ('Test of Geometry','Asha Rao','Test of Geometry\nAnother Author'):
        assert match_catalog([page(text)],[record])['status']=='no_match'
    assert match_catalog([page('Test of Geometry\nAsha Rao',kind='contents')],[record])['status']=='no_match'
    assert match_catalog([page('Test of Geometry\nAsha Rao')],[record])['status']=='matched'


def test_study_guide_does_not_inherit_original_book_code():
    assert match_catalog([page('Test of Geometry\nAsha Rao\nA study guide')],[entry()])['status']=='no_match'


def test_unicode_identity_matching():
    assert match_catalog([page('गणित की कहानी\nआशा राव')],[entry('गणित की कहानी','आशा राव')])['status']=='matched'


def test_missing_and_conflicting_codes_abstain():
    text=page('Test of Geometry\nAsha Rao')
    assert match_catalog([text],[entry(section=None)])['status']=='code_unavailable'
    assert match_catalog([text],[entry(section='510'),entry(section='820')])['status']=='ambiguous'


def test_advertised_book_is_not_the_main_title():
    main=entry('The Main Book');other=entry('Another Advertised Book',section='820')
    text='The Main Book\nAsha Rao\nAnother Advertised Book'
    words=[{'text':token,'height':100 if i<3 else 25} for i,token in enumerate(text.split())]
    assert match_catalog([page(text,words)],[main,other])['record']['section']=='510'
    # First-line evidence still cannot resolve several identities without geometry.
    text='The Main Book by Asha Rao\nAnother Advertised Book by Asha Rao'
    assert match_catalog([page(text),page('Another Advertised Book\nAsha Rao')],[main,other])['status']=='ambiguous'


def test_unknown_or_single_word_titles_are_not_guessed():
    assert match_catalog([page('Unknown text\nAsha Rao')],[entry()])['status']=='no_match'
    assert match_catalog([page('Geometry\nAsha Rao')],[entry('Geometry')])['status']=='no_match'


def test_joined_ocr_words_match_full_title_and_author_with_geometry():
    record=entry('The Old Man and the Sea','Ernest Hemingway','813')
    words=[{'text':text,'height':height} for text,height in
           [('THEOLD',73),('MAN',51),('AND',28),('THE',28),('SEA',96),
            ('Ernest',23),('Hemingway',23)]+[('description',23)]*10]
    capture=page('THEOLD\nMAN\nAND\nTHE\nSEA\nErnest Hemingway',words)
    assert match_catalog([capture],[record])['record']['section']=='813'
    assert match_catalog([dict(capture,kind='back_cover')],[record])['status']=='matched'


def test_ocr_spacing_tolerance_does_not_allow_missing_letters_or_wrong_author():
    record=entry('The Old Man and the Sea','Ernest Hemingway','813')
    for text in ('TheOldMan and the Seashore\nErnest Hemingway',
                 'TheOdMan and the Sea\nErnest Hemingway',
                 'TheOldMan and the Sea\nAnother Hemingway',
                 'TheOldMan and the Sea\nHemingway'):
        assert match_catalog([page(text)],[record])['status']=='no_match'
    assert match_catalog([page('TheOldMan and the Sea\nErnestHemingway')],[record])['status']=='matched'


def test_joined_advertised_title_cannot_override_main_book():
    main=entry('Main Cover Title',section='823')
    other=entry('The Old Man and the Sea',section='813')
    text='Main Cover Title\nAsha Rao\nTheOldMan and the Sea'
    words=[{'text':token,'height':100 if i<3 else 20} for i,token in enumerate(text.split())]
    assert match_catalog([page(text,words)],[main,other])['record']['section']=='823'


def test_guide_back_cover_cannot_inherit_original_novel_code():
    record=entry('The Old Man and the Sea','Ernest Hemingway','813')
    for qualifier in ('Study guide','StudyGuide','CriticalAnalysis'):
        assert match_catalog([page('The Old Man and the Sea\nErnest Hemingway\n'+qualifier,kind='back_cover')],[record])['status']=='no_match'


@pytest.mark.parametrize('codes,expected',[(['813/.6'],'813'),(['823.7'],'823'),(['813.6','813.5'],'813'),(['813','823'],None),([],None),(['bad'],None)])
def test_code_parsing(codes,expected):
    assert section_from_codes(codes)==expected


def prediction():
    return {'label':'900','score':.39,'margin':.1,'entropy':.8,'top3':[],
        'hierarchy':{'review_level':0,'target_level':3,'path':[
            {'level':i,'label':code,'supported':True,'score':.8 if i>1 else .39,'margin':.2,'review_ready':False}
            for i,code in enumerate(['900','910','914'],1)]}}


def test_catalog_code_has_provenance_not_fake_probability():
    result=apply_catalog(prediction(),match_catalog([page('Test of Geometry\nAsha Rao')],[entry(section='813')]))
    assert [r['label'] for r in result['hierarchy']['path']]==['800','810','813']
    assert result['model_suggestion']['label']=='900'
    assert result['score'] is None
    assert result['result_source']=='local_catalog'
    assert result['catalog_match']['edition_review_required']


def test_uncertain_parent_cannot_generate_precise_children():
    raw=prediction();original=copy.deepcopy(raw)
    result=suppress_uncertain_path(raw)
    assert result['label'] is None
    assert [r['label'] for r in result['hierarchy']['path']]==[None,None,None]
    assert result['model_suggestion']['hierarchy']==original['hierarchy']
    assert result['hierarchy']['needs_finer_evidence']


def test_parent_can_remain_when_only_child_is_uncertain():
    raw=prediction();raw['hierarchy']['path'][0].update(score=.8,margin=.3)
    raw['hierarchy']['path'][1]['margin']=.05
    assert [r['label'] for r in suppress_uncertain_path(raw)['hierarchy']['path']]==['900',None,None]


def test_geometry_identity_change_reclassifies_without_extra_ocr(monkeypatch):
    from prototype import engine as engine_module
    import src.ocr_pipeline.catalog as catalog
    rows=[entry('The Main Book'),entry('Another Advertised Book',section='820')]
    monkeypatch.setattr(catalog,'load_index',lambda:rows)
    monkeypatch.setattr(engine_module,'model_version',lambda:{'name':'test-only'})
    def local_predict(text,pages=None):
        match=catalog.match_catalog(pages)
        raw=prediction();raw['catalog_match']=match
        return apply_catalog(raw,match) if match['status']=='matched' else suppress_uncertain_path(raw)
    monkeypatch.setattr(engine_module,'predict',local_predict)
    engine=engine_module.Engine();state=engine.new_session()
    text='The Main Book by Asha Rao\nAnother Advertised Book by Asha Rao'
    words=[{'text':token,'height':30} for token in text.split()]
    evidence={'id':'first','kind':'cover','text':text,'usable':True,'source':'ocr',
              'language':'eng','quality':{},'repairs':0,'words':words}
    state=engine._update(state,copy.deepcopy(evidence),'test')
    assert state['prediction']['catalog_match']['status']=='no_match' or state['prediction']['catalog_match']['status']=='ambiguous'
    revised=copy.deepcopy(evidence);revised['id']='second'
    for w in revised['words'][:3]:w['height']=100
    state=engine._update(state,revised,'test')
    assert state['prediction']['result_source']=='local_catalog'
    assert state['work']['classifier_calls']==2
    state=engine._update(state,copy.deepcopy(revised),'test')
    assert state['work']['classifier_calls']==2
    assert state['work']['ocr_passes']==0
