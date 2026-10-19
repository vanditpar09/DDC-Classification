"""Classify Unicode text locally with an explicitly selected model artifact."""
import argparse
import json
from pathlib import Path

import joblib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="Visible book title, subtitle or description")
    root = Path(__file__).resolve().parents[2]
    default_model = root / "models/hierarchy_v1/classifier.joblib"
    if not default_model.exists():
        default_model = root / "models/improved_v1/classifier.joblib"
    parser.add_argument("--model", type=Path, default=default_model)
    args = parser.parse_args()
    if not args.text.strip():
        parser.error("Text must not be empty")
    model = joblib.load(args.model)
    scores = model.predict_proba([args.text])[0]
    order = scores.argsort()[::-1][:3]
    result = {
        "model": str(args.model),
        "top3": [{"label": str(model.classes_[i]), "score": round(float(scores[i]), 4)} for i in order],
        "note": "Indian-language and real-OCR DDC accuracy requires labeled evaluation; scores are not guarantees.",
    }
    if hasattr(model, "predict_hierarchy"):
        result["hierarchy"] = model.predict_hierarchy([args.text])[0]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
