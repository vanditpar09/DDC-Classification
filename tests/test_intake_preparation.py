import hashlib
import json

import pytest

from scripts.prepare_book_intake import run


def fixture(tmp_path):
    source = tmp_path / 'books'
    intake = tmp_path / 'intake'
    source.mkdir()
    intake.mkdir()
    (source / 'test.epub').write_bytes(b'epub fixture; reader is mocked')
    (intake / 'text.txt').write_text('original extraction')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inventory = {'source_directory': str(source), 'books': [{
        'file': 'test.epub', 'format': 'epub', 'expected_language': 'eng',
        'source_sha256': digest(source / 'test.epub'), 'extracted_text': 'text.txt',
        'extracted_text_sha256': digest(intake / 'text.txt')}]}
    (intake / 'inventory.json').write_text(json.dumps(inventory))
    plan = {'dpi': 200, 'books': [{'file': 'test.epub', 'work_id': 'same-original-work',
        'language': 'eng', 'diagnostic_spine_ordinals': [2],
        'section': '823', 'review_status': 'verified'}]}
    plan_path = intake / 'plan.json'
    plan_path.write_text(json.dumps(plan))
    return source, intake, plan_path


def test_preparation_does_not_promote_plan_labels_or_spine_chunks(tmp_path, monkeypatch):
    _, intake, plan = fixture(tmp_path)
    import scripts.audit_multilingual_intake as reader
    monkeypatch.setattr(reader, 'epub', lambda p: ({}, [
        ('license.xhtml', 'THE FULL PROJECT GUTENBERG™ LICENSE\nTerms', None),
        ('chapter.xhtml', 'Chapter\nBody text.', None)]))
    output = tmp_path / 'prepared'
    run(intake, plan, output, False)
    report = json.loads((output / 'preparation.json').read_text())
    assert report['complete']
    assert report['summary']['books'] == 1
    book = report['books'][0]
    assert book['work_id'] == 'same-original-work'
    assert book['partition'] == 'development'
    assert book['verified_section'] is None and not book['training_eligible']
    assert not book['samples'][0]['use_as_development_text']
    assert (output / book['samples'][0]['clean_text']).read_text() == ''
    assert book['samples'][1]['use_as_development_text']
    assert all(s['reference_text'] is None for s in book['samples'])
    assert not (output / 'training-input.jsonl').exists()
    with pytest.raises(FileExistsError):
        run(intake, plan, output, False)


@pytest.mark.parametrize('changed', ['source', 'extraction'])
def test_source_changes_are_rejected_before_output_is_created(tmp_path, changed):
    source, intake, plan = fixture(tmp_path)
    target = source / 'test.epub' if changed == 'source' else intake / 'text.txt'
    target.write_text('changed')
    output = tmp_path / 'prepared'
    with pytest.raises(ValueError, match='changed'):
        run(intake, plan, output, False)
    assert not output.exists()


def test_relocated_sources_require_the_same_hashes(tmp_path, monkeypatch):
    source, intake, plan = fixture(tmp_path)
    moved = tmp_path / 'relocated-books'
    source.rename(moved)
    import scripts.audit_multilingual_intake as reader
    monkeypatch.setattr(reader, 'epub', lambda p: ({}, [('chapter.xhtml', 'Body', None)]))
    output = tmp_path / 'prepared'
    run(intake, plan, output, False, moved)
    assert json.loads((output / 'preparation.json').read_text())['complete']
