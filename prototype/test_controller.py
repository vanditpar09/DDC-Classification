import io

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from prototype.controller import decide, combine_evidence, normalized_text
from prototype.engine import Engine, image_from_bytes


def page(kind="cover", text="Connections", usable=True, source="ocr", repairs=0, **quality):
    return {"id": "p1", "kind": kind, "text": text, "usable": usable, "source": source,
            "repairs": repairs, "sequence": 0, "language": "eng", "quality": dict(ocr_confidence=92, word_count=6, sharpness=150, median_character_height=35, **quality)}


def prediction(score=.3, margin=.03):
    return {"label": "000", "score": score, "margin": margin, "top3": [], "truncated": False}


def test_readable_uncertain_cover_requests_new_subject_information():
    result = decide([page()], prediction(), 1)
    assert result["action"] == "request_page"
    assert result["requested_page"] == "back_cover"


def test_bad_image_is_not_mistaken_for_missing_subject_evidence():
    p = page(usable=False)
    p["quality"].update(word_count=0, sharpness=2)
    assert decide([p], None, 1)["action"] == "recapture_region"


def test_small_text_gets_only_one_repair():
    p = page(usable=False)
    p["quality"].update(median_character_height=11)
    assert decide([p], None, 1)["action"] == "reprocess_region"
    p["repairs"] = 1
    assert decide([p], None, 2)["action"] == "recapture_region"


def test_script_mismatch_precedes_capture_request():
    p = page(usable=False, script_mismatch=True, suggested_languages=["eng+hin", "eng+mar"])
    assert decide([p], None, 1)["action"] == "switch_language"
    p["repairs"] = 1
    assert decide([p], None, 3)["action"] == "recapture_region"


def test_good_evidence_still_requires_human_review():
    assert decide([page()], prediction(.8, .5), 1)["action"] == "ready_for_review"


def test_exhausted_evidence_and_budget_stop():
    pages = [page(kind=k) for k in ("cover", "back_cover", "contents")]
    assert decide(pages, prediction(), 3)["action"] == "human_review"
    assert decide([page()], prediction(.9, .8), 6)["action"] == "human_review"


def test_duplicates_and_unreadable_text_do_not_reach_model():
    pages = [page(text="Readable title"), page("back_cover", "Readable title\nUseful description"), page("contents", "Garbage", usable=False)]
    assert combine_evidence(pages) == "Readable title\nUseful description"


def test_normalization_preserves_indic_marks():
    assert normalized_text("कला") != normalized_text("किला")
    assert normalized_text("कंप्यूटर प्रोग्रामिंग") == "कंप्यूटर प्रोग्रामिंग"


def test_manual_text_has_no_fake_ocr_quality():
    engine = Engine(predictor=lambda text: prediction())
    state = engine.new_session()
    result = engine.add_text(state["id"], "cover", "भारत का इतिहास", "eng+hin")
    assert result["pages"][0]["quality"] is None
    assert result["work"]["ocr_passes"] == 0


def test_duplicate_text_does_not_increase_model_calls_or_confidence():
    engine = Engine(predictor=lambda text: prediction())
    sid = engine.new_session()["id"]
    engine.add_text(sid, "cover", "Connections", "eng")
    state = engine.add_text(sid, "back_cover", "Connections", "eng")
    assert state["work"]["classifier_calls"] == 1
    assert state["combined_text"] == "Connections"
    assert state["decision"]["requested_page"] == "back_cover"


def test_replacing_page_removes_stale_evidence():
    engine = Engine(predictor=lambda text: prediction())
    sid = engine.new_session()["id"]
    engine.add_text(sid, "cover", "Old OCR mistake", "eng")
    state = engine.add_text(sid, "cover", "Corrected title", "eng")
    assert state["combined_text"] == "Corrected title"
    assert len(state["pages"]) == 1


def test_replacement_restores_previously_duplicate_evidence():
    engine = Engine(predictor=lambda text: prediction())
    sid = engine.new_session()["id"]
    engine.add_text(sid, "cover", "Connections", "eng")
    engine.add_text(sid, "back_cover", "Connections", "eng")
    state = engine.add_text(sid, "cover", "Computer science", "eng")
    assert state["combined_text"] == "Computer science\nConnections"
    assert not any(p["duplicate"] for p in state["pages"])


def test_truncation_prevents_ready_state():
    engine = Engine(predictor=lambda text: dict(prediction(.9, .8), truncated=True))
    sid = engine.new_session()["id"]
    assert engine.add_text(sid, "cover", "Long text", "eng")["decision"]["action"] == "human_review"


def test_repeated_image_is_not_processed_again():
    calls = []
    def ocr(*args, **kwargs):
        calls.append(1)
        return dict(text="Connections", words=[], usable=True, quality={}, work={"ocr_passes": 1, "pixels": 100, "seconds": .1})
    engine = Engine(predictor=lambda text: prediction(), recognizer=ocr)
    sid = engine.new_session()["id"]
    data = io.BytesIO(); Image.new("RGB", (100, 100), "white").save(data, "PNG")
    engine.add_image(sid, "cover", data.getvalue(), "eng")
    result = engine.add_image(sid, "back_cover", data.getvalue(), "eng")
    assert len(calls) == 1
    assert result["work"]["duplicate_uploads"] == 1
    assert result["work"]["ocr_passes"] == 1


def test_ocr_budget_does_not_run_optional_osd_with_one_pass_left():
    seen = []
    def ocr(*args, **kwargs):
        seen.append(kwargs["allow_osd"])
        return dict(text="Connections", words=[], usable=True, quality={}, work={"ocr_passes": 1, "pixels": 100, "seconds": .1})
    engine = Engine(predictor=lambda text: prediction(), recognizer=ocr)
    session = engine.new_session(); session["work"]["ocr_passes"] = 5
    data = io.BytesIO(); Image.new("RGB", (100, 100), "white").save(data, "PNG")
    result = engine.add_image(session["id"], "cover", data.getvalue(), "eng")
    assert seen == [False]
    assert result["work"]["ocr_passes"] == 6
    assert result["decision"]["action"] == "human_review"


@pytest.mark.parametrize("data", [b"not an image", b"x" * (12 * 1024 * 1024 + 1)])
def test_invalid_images_rejected(data):
    with pytest.raises(ValueError):
        image_from_bytes(data)


def test_api_and_local_origin_guard(monkeypatch):
    import prototype.app as module
    monkeypatch.setattr(module, "engine", Engine(predictor=lambda text: prediction()))
    client = TestClient(module.app)
    sid = client.post("/api/sessions").json()["id"]
    response = client.post(f"/api/sessions/{sid}/text", json={"kind": "cover", "text": "Connections", "language": "eng"})
    assert response.status_code == 200
    assert response.json()["decision"]["action"] == "request_page"
    assert client.get(f"/api/sessions/{sid}/export").status_code == 200
    assert client.post("/api/sessions", headers={"Origin": "https://example.com"}).status_code == 403
    assert client.post(f"/api/sessions/{sid}/text", json={"kind": "bad", "text": "x"}).status_code == 400
    assert client.delete(f"/api/sessions/{sid}").status_code == 200
