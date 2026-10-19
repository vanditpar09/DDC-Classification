"""Candidate sourcing stays transparent and never labels an edition as verified."""
import json

from src.research.acquire_candidates import acquire, parse_docs, script_evidence, weak_labels


def work(i, language, code, title=None):
    if language in {'hin','mar'}: default='मराठी ग्रंथ' if language=='mar' else 'हिन्दी पुस्तक'
    elif language=='tam':default='தமிழ் நூல்'
    else:default='History and culture'
    return {'key':f'/works/OL{i}W','title':f'Work {i}','ddc':[code], 'author_name':['Author'],
      'editions':{'docs':[{'key':f'/books/OL{i}M','title':title or default,
         'language':[language],'isbn':[f'9780000000{i:03}']} ]}}


def snapshot(language, docs):return {'language':language,'url':'https://openlibrary.org/search.json',
 'retrieved_at':'2026-10-03T00:00:00Z','payload_sha256':'test','response':{'docs':docs}}


def test_native_script_counts_detect_language_script_and_leave_english_as_roman():
    assert script_evidence('मराठी', 'mar')['native_script_present']
    assert script_evidence('हिन्दी', 'hin')['native_letters']>0
    assert script_evidence('தமிழ்','tam')['native_letters']>0
    assert script_evidence('Tamil language','tam')['native_script_present'] is False
    assert script_evidence('A story','eng')['native_script_present']


def test_weak_labels_keep_only_unanimous_standard_codes():
    assert weak_labels(['005.1','005.9'])=={'1':'000','2':'000','3':'005'}
    assert weak_labels(['005','006'])=={'1':'000','2':'000','3':None}
    assert weak_labels(['005','library code'])=={'1':None,'2':None,'3':None}
    assert weak_labels([''])=={'1':None,'2':None,'3':None}


def test_parse_requires_matching_language_edition_and_records_weak_provenance():
    index={'OL1W':{'test'}}
    docs=[work(1,'mar','005.1'),work(2,'tam','820.3'),work(3,'mar','510','Math book')]
    docs[2]['editions']['docs'][0]['language']=['/languages/eng']
    candidates,rejected=parse_docs(snapshot('mar',docs),index)
    assert len(candidates)==1 and candidates[0]['language']=='mar'
    row=candidates[0]
    assert row['review_status']=='pending' and row['verified_section'] is None
    assert row['prior_catalog_memberships']==['test']
    assert row['weak_labels']=={'1':'000','2':'000','3':'005'}
    assert row['capture_permission'] is False and row['native_scan_ready'] is False
    assert row['title_script']['native_script_present']
    assert rejected=={'no_explicit_matching_edition_language':2}


def test_cached_shortlist_balances_known_classes_and_keeps_forms_blank(tmp_path,monkeypatch):
    import src.research.acquire_candidates as module
    from src.research.collection import LANGUAGES
    monkeypatch.setattr(module,'known_catalog',lambda:([],{}))
    output=tmp_path/'candidates';source=output/'sources';source.mkdir(parents=True)
    for lang in LANGUAGES:
        docs=[work(1000+class_id*3+slot,lang,f'{class_id}05.1')
              for class_id in range(10) for slot in range(3)]
        for sort in ('relevance','random'):
            name=f'openlibrary-{lang}.json' if sort=='relevance' else f'openlibrary-{lang}-random.json'
            (source/name).write_text(json.dumps(snapshot(lang,docs),ensure_ascii=False))
        if lang in {'mar','tam'}:
            (source/f'openlibrary-{lang}-offset100.json').write_text(json.dumps(snapshot(lang,[])))
    manifest=acquire(output,target=20,fetch=False)
    assert manifest['selected_books']==80
    assert all(row['selected']==20 for row in manifest['by_language'].values())
    assert all(len(row['weak_class_counts'])==10 for row in manifest['by_language'].values())
    forms=[json.loads(line) for line in (output/'candidate-review-forms.jsonl').read_text().splitlines()]
    assert len(forms)==80
    assert all(row['review_status']=='pending' and row['section']=='' and not row['capture_permission'] for row in forms)
    assert all(row['pages']==[] for row in forms)
    assert all(row['candidate_source_url'].startswith('https://openlibrary.org/books/') for row in forms)
    assert json.loads((output/'candidate-manifest.json').read_text())['source_files_sha256']
