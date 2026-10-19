"""Fit local division/section heads without inventing labels or reusing test data."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import f1_score

from src.ddc_data.load_data import load_data
from src.ocr_pipeline.hierarchy import HierarchicalDDC, OTHER, clean_text, fine_label, head_probabilities, parent_of
from src.ocr_pipeline.train_improved import ROOT, cover_text, make_splits


def calibrate(model, records, indices):
    rng = np.random.RandomState(42)
    texts = [clean_text(records[i]["raw_text"] if rng.rand() < .5 else cover_text(records[i])) for i in indices]
    matrix = model.features.transform(texts).astype(np.float64)
    report = {}
    for level in (2, 3):
        batches = []
        for parent, head in model.heads[level].items():
            rows, targets = [], []
            for j, i in enumerate(indices):
                label = fine_label(records[i], level)
                if label is None or parent_of(label, level) != parent:
                    continue
                target = label if label in head.classes_ else OTHER
                if target not in head.classes_:
                    continue
                rows.append(j)
                targets.append(list(head.classes_).index(target))
            if rows:
                batches.append((head, matrix[rows], np.asarray(targets)))
        def loss(t):
            values = [-np.log(np.maximum(head_probabilities(h, x, t)[np.arange(len(y)), y], 1e-12)) for h, x, y in batches]
            return float(np.concatenate(values).mean())
        count = sum(len(y) for _, _, y in batches)
        t = float(minimize_scalar(loss, bounds=(.25, 4.), method="bounded").x) if count >= 30 else 1.
        model.temperatures[level] = t
        report[str(level)] = {"books": count, "temperature": t, "conditional_nll_before": loss(1.) if count else None,
                              "conditional_nll_after": loss(t) if count else None,
                              "note": "One shared temperature per level, true-parent calibration; not a validated acceptance policy."}
    return report


def evaluate(model, records, indices, view):
    texts = [clean_text(records[i]["raw_text"] if view == "metadata" else cover_text(records[i])) for i in indices]
    predictions = model.predict_hierarchy(texts)
    result = {}
    for level in (1, 2, 3):
        y, pred, ready_y, ready_pred = [], [], [], []
        supported = set(model.classes_) if level == 1 else {
            str(c) for h in model.heads[level].values() for c in h.classes_ if c != OTHER}
        seen = 0
        for i, output in zip(indices, predictions):
            truth = records[i]["label_level_1"] if level == 1 else fine_label(records[i], level)
            if truth is None:
                continue
            row = next((p for p in output["path"] if p["level"] == level), {})
            prediction = row.get("label") or "ABSTAIN"
            y.append(truth); pred.append(prediction)
            if truth in supported:
                seen += 1
            if row.get("review_ready"):
                ready_y.append(truth); ready_pred.append(prediction)
        labels = sorted(set(y))
        result[str(level)] = {"books": len(y), "excluded_ambiguous": len(indices) - len(y),
                             "accuracy": float(np.mean(np.asarray(y) == pred)),
                             "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
                             "supported_truth_books": seen,
                             "suggestion_coverage": float(np.mean(np.asarray(pred) != "ABSTAIN")),
                             "review_ready_books": len(ready_y),
                             "review_ready_accuracy": float(np.mean(np.asarray(ready_y) == ready_pred)) if ready_y else None,
                             "per_label": {label: {"books": y.count(label), "correct": sum(a == b == label for a, b in zip(y, pred))} for label in labels}}
    return result, [{"document_id": records[i]["document_id"], "view": view, **p} for i, p in zip(indices, predictions)]


def train(output):
    output.mkdir(parents=True, exist_ok=False)
    records = load_data()["records"]
    splits = make_splits(records)
    model = HierarchicalDDC(joblib.load(ROOT / "models/improved_v1/classifier.joblib"))
    audit = {}
    for name, indices in splits.items():
        audit[name] = {}
        for level in (2, 3):
            counts = Counter(fine_label(records[i], level) for i in indices)
            invalid = counts.pop(None, 0)
            audit[name][str(level)] = {"unambiguous": sum(counts.values()), "excluded": invalid,
                                      "classes": len(counts), "label_counts": dict(sorted(counts.items()))}
    (output / "label_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    texts, books, weights = [], [], []
    for i in splits["train"]:
        views = list(dict.fromkeys([clean_text(records[i]["raw_text"]), cover_text(records[i])]))
        texts.extend(views); books.extend([int(i)] * len(views)); weights.extend([1 / len(views)] * len(views))
    print(f"Encoding {len(texts)} training views locally...", flush=True)
    matrix = model.features.transform(texts)
    print("Fitting conditional heads (fixed C=10, minimum five book groups)...", flush=True)
    model.fit_heads(records, splits["train"], texts, matrix, books, weights)
    print("Calibrating shared temperatures on held-out calibration books...", flush=True)
    calibration = calibrate(model, records, splits["calibration"])
    model.ddc_metadata_ = {"family": "multilingual_e5_conditional_hierarchy", "calibration": "sigmoid L1; shared temperature per fine level",
                           "fine_label_source": "Unanimous DDC prefixes consistent with corrected L1",
                           "experimental": True, "min_training_groups": model.min_groups}
    joblib.dump(model, output / "classifier.joblib")
    report = {"dataset_sha256": hashlib.sha256((ROOT / "data/books.jsonl").read_bytes()).hexdigest(),
              "splits": {k: len(v) for k, v in splits.items()}, "fixed_C": model.C, "minimum_training_groups": model.min_groups,
              "head_counts": {str(k): len(v) for k, v in model.heads.items()},
              "predictable_labels": {str(k): len({c for h in heads.values() for c in h.classes_ if c != OTHER}) for k, heads in model.heads.items()},
              "calibration": calibration, "evaluation": {},
              "limitations": ["Catalog prefixes are weak labels, not newly verified librarian labels.",
                              "Previously inspected test set: development benchmark, not fresh validation.",
                              "Only supported classes can be suggested; unsupported/rare outcomes fall back.",
                              "C=10 and five-group minimum fixed before this benchmark; no fine-level model search.",
                              "Conditional heads propagate parent errors; scores and routing thresholds need independent validation.",
                              "Metadata removes catalog-number subject entries; cover is clean text, not OCR.",
                              "No measured Indian-language book accuracy, decimal-code assignment or patentability finding."]}
    predictions = []
    for view in ("metadata", "cover"):
        print(f"Evaluating {view} (all unambiguous test labels, including unsupported classes)...", flush=True)
        scores, rows = evaluate(model, records, splits["test"], view)
        report["evaluation"][view] = scores
        predictions.extend(rows)
        print(json.dumps({k: {m: v for m, v in s.items() if m != "per_label"} for k, s in scores.items()}), flush=True)
    (output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "test_predictions.json").write_text(json.dumps(predictions, indent=2) + "\n")
    assignment = [{"document_id": records[i]["document_id"], "split_group_id": records[i]["split_group_id"], "split": name}
                  for name, indices in splits.items() for i in indices]
    (output / "split_assignments.json").write_text(json.dumps(assignment, indent=2) + "\n")
    print("Saved", output, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models/hierarchy_v1")
    args = parser.parse_args()
    train(args.output_dir)
