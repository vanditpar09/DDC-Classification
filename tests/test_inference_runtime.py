import numpy as np
import pytest

from src.ocr_pipeline.multilingual import MultilingualEmbeddings
from tests.test_hierarchy import model


def test_reusing_broad_scores_preserves_entire_hierarchical_path():
    m=model()
    expected=m.predict_hierarchy(['text'])
    broad=m.predict_proba(['text'])
    m.level1.predict_proba=lambda texts:pytest.fail('Broad classifier evaluated twice')
    assert m.predict_hierarchy(['text'],broad=broad)==expected


@pytest.mark.parametrize('broad',[[[1,0,0]],[[-.1,1.1]],[[float('nan'),1]]])
def test_reused_scores_are_validated(broad):
    with pytest.raises(ValueError,match='Invalid broad'):
        model().predict_hierarchy(['text'],broad=broad)


def test_bounded_cache_preserves_large_batches_and_repeated_indic_text(monkeypatch):
    import src.ocr_pipeline.multilingual as module
    class Encoder:
        calls=[]
        def encode(self,texts,**kwargs):
            self.calls.append(texts)
            return np.array([[len(t),sum(map(ord,t))] for t in texts],dtype=float)
    encoder=Encoder()
    monkeypatch.setattr(module,'get_encoder',lambda path:encoder)
    features=MultilingualEmbeddings(cache_size=2)
    texts=['कंप्यूटर','தமிழ்','history','कंप्यूटर']
    result=features.transform(texts)
    np.testing.assert_array_equal(result[0],result[3])
    assert len(features._cache)==2
    replay=features.transform(['कंप्यूटर'])
    assert len(encoder.calls)==1
    np.testing.assert_array_equal(replay[0],result[0])
    assert '_cache' not in features.__getstate__()
    # Old serialized feature objects did not have cache_size.
    del features.cache_size
    assert features.transform(['history']).shape==(1,2)
    restored=MultilingualEmbeddings.__new__(MultilingualEmbeddings)
    restored.__setstate__(features.__getstate__())
    assert restored.get_params()['cache_size']==2048
