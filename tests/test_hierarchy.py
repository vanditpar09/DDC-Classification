"""Labels, sparse-branch abstention and hierarchical routing invariants."""
import numpy as np
import pytest

from prototype.controller import decide
from src.ocr_pipeline.hierarchy import HierarchicalDDC, OTHER, clean_text, fine_label, head_probabilities


@pytest.mark.parametrize("raw,level,expected", [
    (["005.1", "005.8"], 3, "005"),
    (["005.1", "006.3"], 2, "000"),
    (["005.1", "006.3"], 3, None),
    (["005", "510"], 2, None),
    (["05"], 3, None), ([], 2, None), (["005x"], 3, None),
])
def test_consensus_not_first_catalog_number(raw, level, expected):
    assert fine_label({"ddc_raw": raw, "label_level_1": "000"}, level) == expected


def test_corrected_l1_never_inherits_conflicting_fine_code():
    assert fine_label({"label_level_1": "800", "ddc_raw": ["917.82"]}, 2) is None


def test_catalog_targets_removed_without_damaging_indic_text_or_prose_numbers():
    assert clean_text("भारत 2024\nSubjects: 813/.54; Ps3503.r167 f3 2012; उपन्यास; Grade 10") == "भारत 2024\nSubjects: उपन्यास; Grade 10"


class Broad:
    classes_ = np.array(["000", "100"])
    def predict_proba(self, texts):
        return np.tile([.9, .1], (len(texts), 1))


class Features:
    def transform(self, texts):
        return np.zeros((len(texts), 2))


class Head:
    def __init__(self, classes, logit):
        self.classes_ = np.array(classes)
        self.logit = logit
    def decision_function(self, X):
        return np.full(len(X), self.logit)


def model():
    m = HierarchicalDDC(Broad())
    m.features = Features()
    m.heads = {2: {"000": Head(["000", "020"], -3.)},
               3: {"000": Head(["005", "006"], -3.)}}
    m.support = {2: {"000": 10, "020": 6}, 3: {"005": 7, "006": 9}}
    return m


def test_path_consistency_and_nonincreasing_joint_scores():
    output = model().predict_hierarchy(["programming"])[0]
    assert [x["label"] for x in output["path"]] == ["000", "000", "005"]
    assert output["review_level"] == 3
    scores = [x["path_score"] for x in output["path"]]
    assert scores == sorted(scores, reverse=True)


def test_child_cannot_be_review_ready_if_parent_is_uncertain():
    m = model()
    m.heads[2]["000"].logit = -.1
    output = m.predict_hierarchy(["text"])[0]
    assert output["review_level"] == 1
    assert not output["path"][2]["review_ready"]


def test_rare_outcome_abstains_and_does_not_descend():
    m = model()
    m.heads[2]["000"] = Head(["000", OTHER], 3.)
    output = m.predict_hierarchy(["text"])[0]
    assert len(output["path"]) == 2
    assert output["path"][-1]["label"] is None
    assert output["review_level"] == 1


def test_single_class_or_only_rare_branch_never_fits_a_certain_head():
    records = [{"ddc_raw": ["005"], "label_level_1": "000", "split_group_id": f"g{i}"} for i in range(8)]
    m = model()
    m.heads = {2: {}, 3: {}}
    m.fit_heads(records, range(8), ["text"] * 8, np.zeros((8, 2)), list(range(8)), np.ones(8))
    assert m.heads == {2: {}, 3: {}}


def test_distinct_groups_not_augmented_rows_determine_support():
    records = [{"ddc_raw": ["005"], "label_level_1": "000", "split_group_id": "same"} for _ in range(8)]
    m = model(); m.heads = {2: {}, 3: {}}
    m.fit_heads(records, range(8), ["text"] * 16, np.zeros((16, 2)), list(range(8)) * 2, np.ones(16))
    assert m.support[3]["005"] == 1
    assert not m.heads[3]


def test_binary_temperature_probabilities_are_finite_normalized():
    p = head_probabilities(Head(["000", "020"], 3.), np.zeros((2, 2)), 2.)
    np.testing.assert_allclose(p.sum(axis=1), 1.)
    assert p[0, 1] == pytest.approx(1 / (1 + np.exp(-1.5)))


def page():
    return {"kind": "cover", "sequence": 0, "usable": True, "source": "transcription"}


def test_fine_uncertainty_requests_evidence_despite_confident_broad_class():
    m = model(); m.heads[3]["000"].logit = -.1
    p = {"score": .9, "margin": .8, "hierarchy": m.predict_hierarchy(["text"])[0]}
    d = decide([page()], p, 0)
    assert d["action"] == "request_page"
    assert "level 2" in d["reason"]
    assert decide([page()], p, 6)["action"] == "human_review"


def test_missing_branch_stops_for_librarian_not_more_ocr():
    m = model(); m.heads[3] = {}
    p = {"score": .9, "margin": .8, "hierarchy": m.predict_hierarchy(["text"])[0]}
    assert decide([page()], p, 0)["action"] == "human_review"


def test_all_levels_ready_still_only_suggests_human_review():
    p = {"score": .9, "margin": .8, "hierarchy": model().predict_hierarchy(["text"])[0]}
    assert decide([page()], p, 0)["action"] == "ready_for_review"
