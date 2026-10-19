import pytest
from prototype import engine


@pytest.fixture
def isolated_model(tmp_path,monkeypatch):
    engine.selected_model_path.cache_clear();engine.model_version.cache_clear()
    monkeypatch.setattr(engine,'ROOT',tmp_path)
    yield tmp_path
    engine.selected_model_path.cache_clear();engine.model_version.cache_clear()


def test_explicit_experiment_never_silently_falls_back(isolated_model,monkeypatch):
    monkeypatch.setenv('FIELDNOTE_MODEL','native_silver_v2')
    old=isolated_model/'models/hierarchy_v1/classifier.joblib';old.parent.mkdir(parents=True);old.write_bytes(b'old')
    with pytest.raises(ValueError,match='not been trained'):engine.selected_model_path()


def test_version_identifies_exact_selected_experiment(isolated_model,monkeypatch):
    monkeypatch.setenv('FIELDNOTE_MODEL','native_silver_v2')
    path=isolated_model/'models/native_silver_v2/classifier.joblib';path.parent.mkdir(parents=True);path.write_bytes(b'candidate')
    assert engine.selected_model_path()==path
    assert engine.model_version()['name']=='native_silver_v2'
    assert engine.model_version()['experimental']


def test_external_serialized_models_cannot_be_selected(isolated_model,monkeypatch):
    monkeypatch.setenv('FIELDNOTE_MODEL','../../untrusted')
    with pytest.raises(ValueError,match='saved project'):engine.selected_model_path()
