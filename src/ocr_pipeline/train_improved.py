"""Reproducible, group-safe DDC benchmark and multilingual model training.

Select on grouped cross-validation of training books only. Fit sigmoid
calibration on separate books. Evaluate the selected model once on the original
1,007-book test split. Historical holdout groups never enter fitting/calibration.
The encoder is frozen; its original pretraining corpus is outside our control.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, log_loss
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from src.ddc_data.load_data import load_data
from src.ocr_pipeline.leakage_checks import check_historical_holdout, check_split_group_integrity
from src.ocr_pipeline.multilingual import ENCODER_ID, ENCODER_PATH, ENCODER_REVISION, MultilingualEmbeddings

ROOT = Path(__file__).resolve().parents[2]
LABELS = [f"{i}00" for i in range(10)]


def cover_text(record):
    """A clean-text cover proxy, NOT actual OCR and not a generated summary."""
    title = record["title"].strip()
    subtitle = record.get("subtitle", "").strip()
    return title + ("\n" + subtitle if subtitle and subtitle.casefold() not in title.casefold() else "")


def make_splits(records, seed=42):
    groups = np.array([r["split_group_id"] for r in records])
    labels = np.array([r["label_level_1"] for r in records])
    all_idx = np.arange(len(records))
    # Reproduce the existing test membership; do not recycle exposed test books.
    pool, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(all_idx, labels, groups))
    prior = json.loads((ROOT / "sources/prior_splits.json").read_text())
    protected = {r["split_group_id"] for r in records if
                 r.get("prior_holdout_status", "none") != "none" or
                 any(prior.get(w) in {"test", "validation"} for w in r["source_work_ids"])}
    reserved = np.array([i for i in pool if groups[i] in protected], dtype=int)
    eligible = np.array([i for i in pool if groups[i] not in protected], dtype=int)
    train_local, cal_local = next(GroupShuffleSplit(n_splits=1, test_size=.15, random_state=seed).split(eligible, labels[eligible], groups[eligible]))
    splits = {"train": eligible[train_local], "calibration": eligible[cal_local],
              "test": test, "historical_reserved": reserved}
    violations = check_split_group_integrity({k: [records[i] for i in idx] for k, idx in splits.items()})
    for name in ("train", "calibration"):
        violations += check_historical_holdout([records[i] for i in splits[name]])
        if set(labels[splits[name]]) != set(LABELS):
            violations.append(f"Missing class in {name}")
    if violations:
        raise ValueError("\n".join(violations))
    return splits


def lexical_features():
    # Keep Unicode marks: Indian-language diacritics carry meaning.
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=50000, sublinear_tf=True)),
    ])


def augmented_inputs(records, indices, augment):
    texts, labels, weights = [], [], []
    for i in indices:
        record = records[i]
        views = [record["raw_text"]]
        cover = cover_text(record)
        if augment and cover != views[0]:
            views.append(cover)
        texts.extend(views)
        labels.extend([record["label_level_1"]] * len(views))
        weights.extend([1 / len(views)] * len(views))
    return texts, np.array(labels), np.array(weights)


def metrics(labels, probabilities, classes):
    if not np.isfinite(probabilities).all() or not np.allclose(probabilities.sum(axis=1), 1):
        raise ValueError("Invalid prediction probabilities")
    pred = np.asarray(classes)[probabilities.argmax(axis=1)]
    confidence = probabilities.max(axis=1)
    y = np.asarray(labels)
    one_hot = (y[:, None] == np.asarray(classes)[None, :]).astype(float)
    report = {
        "n": len(y), "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=LABELS, average="macro", zero_division=0)),
        "top3_accuracy": float(np.mean([a in np.asarray(classes)[np.argsort(p)[-3:]] for a, p in zip(y, probabilities)])),
        "log_loss": float(log_loss(y, probabilities, labels=list(classes))),
        "brier_multiclass": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "per_class": classification_report(y, pred, labels=LABELS, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y, pred, labels=LABELS).tolist(),
    }
    report["routing_at_fixed_085"] = {
        "accepted": int(np.sum(confidence >= .85)),
        "coverage": float(np.mean(confidence >= .85)),
        "accuracy": float(np.mean(pred[confidence >= .85] == y[confidence >= .85])) if np.any(confidence >= .85) else None,
        "note": "Descriptive only; not a validated deployment threshold.",
    }
    return report


def paired_accuracy_intervals(predictions, records, resamples=2000):
    """Descriptive paired bootstrap: resample whole book groups, not text views."""
    groups = {r["document_id"]: r["split_group_id"] for r in records}
    intervals = {}
    for view in ("metadata", "cover"):
        selected = {r["document_id"]: r for r in predictions if r["model"] == "selected" and r["view"] == view}
        gids = sorted({groups[i] for i in selected})
        group_index = {g: i for i, g in enumerate(gids)}
        sizes = np.zeros(len(gids))
        for i in selected:
            sizes[group_index[groups[i]]] += 1
        sample = np.random.RandomState(42).randint(0, len(gids), size=(resamples, len(gids)))
        for reference in ("previous_baseline", "matched_tfidf_reference"):
            old = {r["document_id"]: r for r in predictions if r["model"] == reference and r["view"] == view}
            if not old:
                continue
            delta = np.zeros(len(gids))
            for i, row in selected.items():
                delta[group_index[groups[i]]] += int(row["prediction"] == row["label"]) - int(old[i]["prediction"] == old[i]["label"])
            draws = delta[sample].sum(axis=1) / sizes[sample].sum(axis=1)
            intervals[view + "__vs__" + reference] = {
                "delta_accuracy": float(delta.sum() / sizes.sum()),
                "group_bootstrap_95pct": np.quantile(draws, [.025, .975]).tolist(),
                "resamples": resamples, "seed": 42,
            }
    return intervals


def train(output_dir, include_embeddings=True):
    output_dir = Path(output_dir)
    # Keep runs immutable and protect the previously fitted baseline.
    output_dir.mkdir(parents=True, exist_ok=False)
    data = load_data()
    records = data["records"]
    splits = make_splits(records)
    groups = np.asarray(data["groups"])
    y = np.asarray(data["y"])
    tr, cal, te = (splits[k] for k in ("train", "calibration", "test"))
    print("Split sizes:", {k: len(v) for k, v in splits.items()}, flush=True)
    assignment = [{"document_id": r["document_id"], "split_group_id": r["split_group_id"],
                   "split": name} for name, indices in splits.items() for i in indices for r in [records[i]]]
    (output_dir / "split_assignments.json").write_text(json.dumps(assignment, indent=2) + "\n")

    folds = list(StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42).split(tr, y[tr], groups[tr]))
    # Candidate list and objective are fixed before reading any test results.
    candidates = [dict(family=f, C=c, augment=a) for f in ("tfidf_logistic", "tfidf_svm")
                  for c in (1., 10.) for a in (False, True)]
    if include_embeddings:
        candidates += [dict(family="multilingual_e5", C=c, augment=a) for c in (.1, 1., 10., 100.) for a in (False, True)]
    embedder = MultilingualEmbeddings()
    if include_embeddings:
        # Precompute only training text; the encoder is fixed and sees no labels.
        train_views = list(dict.fromkeys([text for i in tr for text in (records[i]["raw_text"], cover_text(records[i]))]))
        print(f"Encoding {len(train_views)} training text views locally...", flush=True)
        embedder.transform(train_views)
    results = []
    for candidate in candidates:
        start = time.time()
        fold_results = []
        for train_local, val_local in folds:
            fit_idx, val_idx = tr[train_local], tr[val_local]
            assert set(groups[fit_idx]).isdisjoint(groups[val_idx])
            X_fit, y_fit, weights = augmented_inputs(records, fit_idx, candidate["augment"])
            features = embedder if candidate["family"] == "multilingual_e5" else lexical_features()
            features.fit(X_fit)
            matrix = features.transform(X_fit)
            clf = LinearSVC(C=candidate["C"], max_iter=10000, random_state=42) if candidate["family"] == "tfidf_svm" else LogisticRegression(C=candidate["C"], max_iter=2000, random_state=42)
            clf.fit(matrix, y_fit, sample_weight=weights)
            scores = {}
            for view in ("metadata", "cover"):
                texts = [records[i]["raw_text"] if view == "metadata" else cover_text(records[i]) for i in val_idx]
                pred = clf.predict(features.transform(texts))
                scores[view] = float(f1_score(y[val_idx], pred, labels=LABELS, average="macro", zero_division=0))
            fold_results.append(scores)
        result = dict(candidate, folds=fold_results,
                      metadata_cv_macro_f1=float(np.mean([f["metadata"] for f in fold_results])),
                      cover_cv_macro_f1=float(np.mean([f["cover"] for f in fold_results])))
        result["selection_score"] = (result["metadata_cv_macro_f1"] + result["cover_cv_macro_f1"]) / 2
        result["seconds"] = round(time.time() - start, 2)
        results.append(result)
        print(json.dumps(result), flush=True)
        (output_dir / "cv_results.json").write_text(json.dumps(results, indent=2) + "\n")

    best = max(results, key=lambda r: r["selection_score"])
    print("Selected on training CV:", best, flush=True)
    def fit_candidate(candidate):
        X_fit, y_fit, weights = augmented_inputs(records, tr, candidate["augment"])
        features = embedder if candidate["family"] == "multilingual_e5" else lexical_features()
        clf = LinearSVC(C=candidate["C"], max_iter=10000, random_state=42) if candidate["family"] == "tfidf_svm" else LogisticRegression(C=candidate["C"], max_iter=2000, random_state=42)
        pipeline = Pipeline([("features", features), ("clf", clf)])
        pipeline.fit(X_fit, y_fit, clf__sample_weight=weights)
        # Exactly one deterministic text view per calibration book; no inflated n.
        rng = np.random.RandomState(42)
        X_cal = [records[i]["raw_text"] if rng.rand() < .5 else cover_text(records[i]) for i in cal]
        calibrated = CalibratedClassifierCV(FrozenEstimator(pipeline), method="sigmoid")
        calibrated.fit(X_cal, y[cal])
        calibrated.ddc_metadata_ = {
            "family": candidate["family"], "calibration": "sigmoid", "calibration_books": len(cal),
            "input": "Unicode text only; metadata and cover proxy", "multilingual_evaluation": "not yet performed on labeled real books",
        }
        return calibrated

    model = fit_candidate(best)
    joblib.dump(model, output_dir / "classifier.joblib")
    # Fixed comparator, same training/calibration books; not selected on test.
    reference = fit_candidate(dict(family="tfidf_logistic", C=1., augment=False))
    models = {"selected": model, "matched_tfidf_reference": reference}
    old_path = ROOT / "models/baseline_classifier.joblib"
    if old_path.exists():
        models["previous_baseline"] = joblib.load(old_path)
    evaluation = {}
    predictions = []
    for name, estimator in models.items():
        evaluation[name] = {}
        for view in ("metadata", "cover"):
            texts = [records[i]["raw_text"] if view == "metadata" else cover_text(records[i]) for i in te]
            proba = estimator.predict_proba(texts)
            evaluation[name][view] = metrics(y[te], proba, estimator.classes_)
            if name == "selected":
                for slice_name, mask in {
                    "with_subjects": np.array([bool(records[i]["subject_headings"]) for i in te]),
                    "without_subjects": np.array([not records[i]["subject_headings"] for i in te]),
                    "title_only": np.array([records[i]["text_availability"] == "title_only" for i in te]),
                }.items():
                    evaluation[name][view][slice_name] = metrics(y[te][mask], proba[mask], estimator.classes_)
            for i, p in zip(te, proba):
                predictions.append({"model": name, "view": view, "document_id": records[i]["document_id"],
                                    "label": records[i]["label_level_1"], "prediction": str(estimator.classes_[p.argmax()]),
                                    "confidence": float(p.max())})
        print(name, {view: {k: v for k, v in report.items() if k in {"accuracy", "macro_f1", "top3_accuracy"}} for view, report in evaluation[name].items()}, flush=True)
    report = {
        "dataset_sha256": hashlib.sha256((ROOT / "data/books.jsonl").read_bytes()).hexdigest(),
        "seed": 42, "splits": {k: len(v) for k, v in splits.items()}, "labels": LABELS,
        "selection_rule": "Mean of metadata and cover-proxy macro-F1 across 3 training-only grouped folds",
        "best_candidate": best, "evaluation": evaluation,
        "paired_accuracy_comparisons": paired_accuracy_intervals(predictions, records),
        "encoder": ENCODER_ID if include_embeddings else None,
        "encoder_revision": ENCODER_REVISION if include_embeddings else None,
        "encoder_path": ENCODER_PATH if include_embeddings else None,
        "python": platform.python_version(),
        "dependencies": {p: version(p) for p in ("scikit-learn", "numpy", "joblib") + (("sentence-transformers", "transformers", "torch") if include_embeddings else ())},
        "limitations": ["No labeled language-specific evaluation; multilingual encoder support is not measured DDC accuracy.",
                        "Cover inputs are clean title/subtitle proxies, not real OCR.",
                        "Historical reserved books are unused, not a fresh test set.",
                        "The original test has previously been inspected; obtain an independent real-scan set before deployment.",
                        "Previous baseline used more training books and isotonic calibration; matched reference controls these differences."]}
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    with (output_dir / "test_predictions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    print("Saved model and benchmark to", output_dir, flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models/improved_v1")
    parser.add_argument("--lexical-only", action="store_true")
    args = parser.parse_args()
    train(args.output_dir, include_embeddings=not args.lexical_only)
