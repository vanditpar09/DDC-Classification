"""Regression checks for partitions, feature isolation and offline inference."""
import pickle

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from src.ddc_data.load_data import load_data
from src.ocr_pipeline.classify import classify_text
from src.ocr_pipeline.leakage_checks import check_historical_holdout
from src.ocr_pipeline.multilingual import MultilingualEmbeddings
from src.ocr_pipeline.train_improved import augmented_inputs, cover_text, make_splits, metrics
import pytest


def test_partitions_preserve_test_and_exclude_historical_holdouts():
    data = load_data()
    records = data["records"]
    splits = make_splits(records)
    _, original_test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42).split(data["X"], data["y"], data["groups"]))
    assert set(splits["test"]) == set(original_test)
    assert sorted(i for indices in splits.values() for i in indices) == list(range(len(records)))
    group_sets = [{records[i]["split_group_id"] for i in indices} for indices in splits.values()]
    for i, a in enumerate(group_sets):
        assert all(a.isdisjoint(b) for b in group_sets[i + 1:])
    for name in ("train", "calibration"):
        assert check_historical_holdout([records[i] for i in splits[name]]) == []
    assert {k: list(v) for k, v in splits.items()} == {k: list(v) for k, v in make_splits(records).items()}


def test_cover_proxy_never_uses_target_or_subjects_and_keeps_unicode():
    record = {"title": "भारत का इतिहास", "subtitle": "संस्कृति और समाज", "raw_text": "catalog text",
              "label_level_1": "900", "ddc_raw": "954", "subject_headings": ["SECRET_SUBJECT"]}
    assert cover_text(record) == "भारत का इतिहास\nसंस्कृति और समाज"
    texts, labels, weights = augmented_inputs([record], [0], True)
    assert len(texts) == 2
    assert weights.sum() == 1
    assert list(labels) == ["900", "900"]


def test_augmentation_does_not_double_weight_or_duplicate_title_only():
    records = [{"title": "A book", "raw_text": "A book", "label_level_1": "000"},
               {"title": "Another", "raw_text": "Another\nSubjects: Science", "label_level_1": "500"}]
    texts, labels, weights = augmented_inputs(records, [0, 1], True)
    assert texts == ["A book", "Another\nSubjects: Science", "Another"]
    assert weights.tolist() == [1., .5, .5]


def test_embeddings_prefix_cache_and_pickle(monkeypatch):
    calls = []
    class Encoder:
        def encode(self, texts, **kwargs):
            calls.extend(texts)
            return np.ones((len(texts), 384), dtype=np.float32)
    monkeypatch.setattr("src.ocr_pipeline.multilingual.get_encoder", lambda path: Encoder())
    feature = MultilingualEmbeddings()
    assert feature.transform(["नमस्ते", "नमस्ते"]).shape == (2, 384)
    feature.transform(["नमस्ते"])
    assert calls == ["query: नमस्ते"]
    restored = pickle.loads(pickle.dumps(feature))
    assert not hasattr(restored, "_cache")


def test_calibration_note_matches_actual_estimator(sample_pipeline_config):
    # This fake classifier checks that unknown predict_proba objects are not
    # represented as calibrated simply because they return probabilities.
    class UnknownModel:
        classes_ = np.array(["000", "500"])
        def predict_proba(self, texts):
            return np.array([[.7, .3]])
    result = classify_text("test", sample_pipeline_config, model=UnknownModel())
    assert result.calibrated is False
    assert "Uncalibrated" in result.calibration_note


def test_invalid_probabilities_fail_instead_of_publishing_metrics():
    with pytest.raises(ValueError, match="Invalid prediction"):
        metrics(["000"], np.array([[float("nan"), 0.]]), ["000", "100"])
