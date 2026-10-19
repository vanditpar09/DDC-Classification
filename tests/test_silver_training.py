"""The experimental trainer must never leak groups or claim gold references."""
import hashlib
import numpy as np
import pytest
import pickle

import src.research.train_silver as module
from tests.test_hierarchy import Broad, Features, Head


def book(root, name='one', group='g', partition='train'):
    path=root/(name+'.txt');path.write_text('தமிழ் ஒரு நூல்')
    return dict(work_id=name,group_id=group,assigned_partition=partition,silver_section='894',
                experimental_eligible=True,verified_section=None,human_checked=False,
                samples=[dict(text_file=path.name,text_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              human_checked=False,reference_is_ground_truth=False)])


def test_translations_cannot_cross_partitions(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    a=book(tmp_path);b=book(tmp_path,'translation',partition='development')
    with pytest.raises(ValueError,match='leaks'):module.validate_books([a,b])


def test_changed_text_and_false_reference_claims_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    b=book(tmp_path);b['samples'][0]['reference_is_ground_truth']=True
    with pytest.raises(ValueError,match='False gold'):module.validate_books([b])
    b['samples'][0]['reference_is_ground_truth']=False
    (tmp_path/'one.txt').write_text('changed')
    with pytest.raises(ValueError,match='Modified'):module.validate_books([b])


def test_identical_passage_requires_shared_group(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    a=book(tmp_path);b=book(tmp_path,'two',group='other')
    with pytest.raises(ValueError,match='Repeated passage'):module.validate_books([a,b])
    b['group_id']='g';module.validate_books([a,b])


def test_silver_scores_never_approve_a_book():
    m=module.SilverHierarchicalDDC(Broad());m.features=Features()
    m.heads={2:{'000':Head(['000','020'],-3)},3:{'000':Head(['005','006'],-3)}}
    output=m.predict_hierarchy(['text'])[0]
    assert [r['label'] for r in output['path']]==['000','000','005']
    assert output['review_level']==0
    assert all(not r['review_ready'] for r in output['path'])
    restored=pickle.loads(pickle.dumps(m))
    assert restored.predict_hierarchy(['text'])==m.predict_hierarchy(['text'])


def test_multilingual_editions_receive_one_work_weight():
    def row(gid,truth,pred):
        return dict(group_id=gid,section=truth,hierarchy={'path':[dict(level=l,label=pred[:l].ljust(3,'0')) for l in (1,2,3)]})
    rows=[row('translated','510','510')]*3+[row('single','891','894')]
    result=module.metrics(rows)
    assert result['work_groups']==2
    assert result['levels']['3']['accuracy']==pytest.approx(.5)
    assert result['levels']['1']['accuracy']==1
