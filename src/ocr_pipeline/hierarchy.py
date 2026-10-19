"""Conservative, parent-constrained DDC division and section suggestions.

Fine labels are derived only from unanimous catalog prefixes. Rare training
labels share an OTHER outcome; they are never silently relabeled as a common
section. Scores below a parent are conditional and are not accuracy estimates.
"""
from __future__ import annotations

import re
from collections import defaultdict

import numpy as np
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression

from src.ocr_pipeline.multilingual import MultilingualEmbeddings

OTHER = "__other__"
CODE = re.compile(r"\d{3}(?:\.\d+)?", re.ASCII)


def fine_label(record, level):
    if level not in (2, 3):
        raise ValueError("Fine level must be 2 or 3")
    raw = record.get("ddc_raw", [])
    if not raw or any(not CODE.fullmatch(code) for code in raw):
        return None
    if any(code[0] != record["label_level_1"][0] for code in raw):
        return None
    labels = {code[:level].ljust(3, "0") for code in raw}
    return next(iter(labels)) if len(labels) == 1 else None


def clean_text(text):
    """Remove catalog-number subject entries, keeping ordinary prose/numbers.

    Catalog records sometimes include the target DDC number among subjects.
    Apply this same cleanup at training and inference, not to label fields.
    """
    lines = []
    for line in text.splitlines():
        if line.lower().startswith("subjects: "):
            entries = line[len("Subjects: "):].split("; ")
            entries = [x for x in entries if not re.fullmatch(r"[\d./\s]+", x)
                       and not re.fullmatch(r"[A-Za-z]{1,3}\s*\d.*", x)]
            if entries:
                lines.append("Subjects: " + "; ".join(entries))
        else:
            lines.append(line)
    return "\n".join(lines)


def parent_of(label, level):
    return label[:level - 1].ljust(3, "0")


def head_probabilities(head, X, temperature=1.):
    logits = head.decision_function(X)
    if logits.ndim == 1:
        logits = np.column_stack([np.zeros(len(X)), logits])
    p = softmax(logits / temperature, axis=1)
    if not np.isfinite(p).all():
        raise ValueError("Non-finite hierarchical probabilities")
    return p


class HierarchicalDDC:
    def __init__(self, level1, min_groups=5, C=10.):
        self.level1 = level1
        self.classes_ = level1.classes_
        self.features = MultilingualEmbeddings()
        self.min_groups = min_groups
        self.C = C
        self.heads = {2: {}, 3: {}}
        self.support = {2: {}, 3: {}}
        self.temperatures = {2: 1., 3: 1.}

    def fit_heads(self, records, train_indices, texts, matrix, book_indices, weights):
        for level in (2, 3):
            groups = defaultdict(set)
            labels = {}
            for i in train_indices:
                label = fine_label(records[i], level)
                if label is not None:
                    labels[i] = label
                    groups[label].add(records[i]["split_group_id"])
            self.support[level] = {k: len(v) for k, v in groups.items()}
            eligible = {k for k, v in groups.items() if len(v) >= self.min_groups}
            for parent in sorted({parent_of(label, level) for label in labels.values()}):
                rows = [j for j, i in enumerate(book_indices)
                        if i in labels and parent_of(labels[i], level) == parent]
                y = [labels[book_indices[j]] if labels[book_indices[j]] in eligible else OTHER for j in rows]
                # No one-class softmax masquerading as perfect confidence.
                if len(set(y)) < 2 or not (set(y) - {OTHER}):
                    continue
                head = LogisticRegression(C=self.C, max_iter=2000, random_state=42)
                head.fit(matrix[rows].astype(np.float64), y, sample_weight=np.asarray(weights)[rows])
                self.heads[level][parent] = head
        return self

    def predict_proba(self, texts):
        # sklearn-compatible broad-class interface for existing callers.
        return self.level1.predict_proba([clean_text(text) for text in texts])

    def predict(self, texts):
        return self.classes_[self.predict_proba(texts).argmax(axis=1)]

    def predict_hierarchy(self, texts, min_score=.62, min_margin=.18, broad=None):
        texts = [clean_text(text) for text in texts]
        matrix = self.features.transform(texts).astype(np.float64)
        broad = self.level1.predict_proba(texts) if broad is None else np.asarray(broad)
        if broad.shape != (len(texts), len(self.classes_)) or not np.isfinite(broad).all() or np.any(broad < 0) or not np.allclose(broad.sum(axis=1), 1):
            raise ValueError("Invalid broad-class probabilities")
        result = []
        for x, p in zip(matrix, broad):
            order = np.argsort(p)[::-1]
            parent = str(self.classes_[order[0]])
            broad_ok = p[order[0]] >= min_score and p[order[0]] - p[order[1]] >= min_margin
            path = [{"level": 1, "label": parent, "score": float(p[order[0]]),
                     "margin": float(p[order[0]] - p[order[1]]), "supported": True,
                     "review_ready": bool(broad_ok), "path_score": float(p[order[0]]),
                     "top3": [{"label": str(self.classes_[i]), "score": float(p[i])} for i in order[:3]]}]
            resolved = 1 if broad_ok else 0
            path_score = float(p[order[0]])
            for level in (2, 3):
                head = self.heads[level].get(parent)
                if head is None:
                    path.append({"level": level, "parent": parent, "label": None, "supported": False,
                                 "review_ready": False, "reason": "Insufficient training support for this branch", "top3": []})
                    break
                probs = head_probabilities(head, x[None, :], self.temperatures[level])[0]
                order = np.argsort(probs)[::-1]
                label = str(head.classes_[order[0]])
                score = float(probs[order[0]])
                margin = float(score - probs[order[1]])
                known = label != OTHER
                ready = known and resolved == level - 1 and score >= min_score and margin >= min_margin
                path_score *= score
                row = {"level": level, "parent": parent, "label": label if known else None,
                       "supported": known, "score": score, "margin": margin,
                       "path_score": path_score, "review_ready": bool(ready),
                       "training_groups": self.support[level].get(label, 0),
                       "top3": [{"label": str(head.classes_[i]) if head.classes_[i] != OTHER else None,
                                 "score": float(probs[i])} for i in order[:3]],
                       "reason": "Conditional suggestion; human review required" if known else "Rare or unsupported child class"}
                path.append(row)
                if ready:
                    resolved = level
                if not known:
                    break
                parent = label
            result.append({"path": path, "review_level": resolved, "target_level": 3,
                           "needs_finer_evidence": resolved < 3,
                           "score_note": "L2/L3 scores are conditional on the displayed parent. Thresholds are experimental."})
        return result
