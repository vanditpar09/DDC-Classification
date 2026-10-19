"""Real Tesseract + real classifier checks on explicitly synthetic fixtures."""
from pathlib import Path
import json

from prototype.engine import Engine
from prototype.make_samples import create

HERE = Path(__file__).resolve().parent


def main():
    create()
    engine = Engine()
    results = []

    def save(name, state, expected):
        actual = state["decision"]["action"]
        result = {"scenario": name, "expected": expected, "actual": actual, "passed": expected == actual,
                  "prediction": state["prediction"], "work": dict(state["work"]),
                  "quality": state["pages"][-1].get("quality"), "reason": state["decision"]["reason"]}
        results.append(result)
        print(name, actual, "PASS" if result["passed"] else "FAIL", flush=True)

    sid = engine.new_session()["id"]
    state = engine.add_image(sid, "cover", (HERE / "samples/ambiguous_cover.png").read_bytes(), "eng")
    save("Readable ambiguous cover", state, "request_page")
    cover_entropy = state["prediction"]["entropy"]
    state = engine.add_image(sid, "back_cover", (HERE / "samples/informative_back.png").read_bytes(), "eng")
    # Actual frozen-model result: this description helps, but does not clear
    # the unchanged review thresholds. It must not force a confident outcome.
    save("Extra description remains ambiguous; request contents", state, "request_page")
    results.append({"scenario": "Additional evidence improves ranking without forcing acceptance",
                    "passed": state["prediction"]["label"] == "000" and
                              state["prediction"]["entropy"] < cover_entropy and
                              state["decision"].get("requested_page") == "contents" and
                              state["work"]["classifier_calls"] == 2})
    before = dict(state["work"])
    state = engine.add_image(sid, "contents", (HERE / "samples/informative_back.png").read_bytes(), "eng")
    results.append({"scenario": "Duplicate photo avoids processing", "passed": state["work"]["ocr_passes"] == before["ocr_passes"] and state["work"]["classifier_calls"] == before["classifier_calls"]})

    for filename, expected in [("blurred_page.png", "recapture_region"), ("blank.png", "recapture_region"), ("small_text.png", "reprocess_region")]:
        sid = engine.new_session()["id"]
        state = engine.add_image(sid, "cover", (HERE / "samples" / filename).read_bytes(), "eng")
        save(filename, state, expected)
        if filename == "small_text.png" and state["decision"]["action"] == "reprocess_region":
            state = engine.repair(sid, state["pages"][0]["id"])
            # With fine heads, the broad class/division pass but the section is
            # ambiguous (005 versus 006). OCR repair must not force acceptance.
            fine = state["prediction"].get("hierarchy")
            save("Small print after repair", state, "request_page" if fine else "ready_for_review")
            if fine:
                results.append({"scenario": "Readable broad result still requests finer subject evidence",
                                "passed": fine["review_level"] == 2 and
                                          [p["label"] for p in fine["path"]] == ["000", "000", "005"] and
                                          not fine["path"][-1]["review_ready"]})

    for language, text in [("eng+hin", "कंप्यूटर प्रोग्रामिंग का परिचय"), ("eng+mar", "संगणक प्रोग्रामिंगची ओळख"), ("eng+tam", "தமிழ் இலக்கியம்")]:
        sid = engine.new_session()["id"]
        state = engine.add_text(sid, "cover", text, language)
        results.append({"scenario": "Unicode transcription: " + language, "passed": bool(state["prediction"]) and state["work"]["ocr_passes"] == 0,
                        "prediction": state["prediction"], "action": state["decision"]["action"]})
    output = {"fixtures": "Synthetic English typography images and hand-written Unicode phrases; not a real-book accuracy benchmark.",
              "results": results, "passed": sum(r["passed"] for r in results), "total": len(results)}
    (HERE / "smoke_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"{output['passed']}/{output['total']} smoke checks passed", flush=True)
    if output["passed"] != output["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
