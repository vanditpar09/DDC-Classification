"""Stage 6: Classification (§2.6).

Loads a trained model as a frozen artifact — no retraining or fine-tuning
inline. Includes a HARD REQUIREMENT feature leakage guard: asserts at
inference time that only raw_text reaches the model.

Calibration metadata is reported from the loaded estimator, rather than
assuming every artifact uses the same features or calibration method.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import joblib
from sklearn.calibration import CalibratedClassifierCV

from .config import PipelineConfig
from .exceptions import FeatureLeakageError, ModelNotFoundError
from .schemas import ClassificationResult


def _check_feature_leakage(input_data: dict, config: PipelineConfig) -> None:
    """Hard requirement: assert no forbidden field reaches the model.

    Raises FeatureLeakageError if any key in input_data matches the
    forbidden_model_features list from pipeline_config.yaml.
    """
    forbidden = set(config.forbidden_model_features)
    found = [k for k in input_data if k in forbidden]
    if found:
        raise FeatureLeakageError(found)


def load_model(config: PipelineConfig) -> Any:
    """Load the frozen model artifact.

    Returns the deserialized sklearn Pipeline (or any object with
    predict() and predict_proba() methods).
    """
    model_path = config.model_artifact_path
    if not model_path.exists():
        raise ModelNotFoundError(str(model_path))
    return joblib.load(model_path)


def classify_text(
    raw_text: str,
    config: PipelineConfig,
    model: Optional[Any] = None,
    input_metadata: Optional[dict] = None,
) -> ClassificationResult:
    """Classify raw_text into one of ten DDC broad classes.

    Parameters
    ----------
    raw_text : the assembled raw_text string (from §2.5)
    config : pipeline configuration
    model : pre-loaded model (optional — loaded from disk if not provided)
    input_metadata : optional dict of extra fields to check for leakage.
        If provided, the leakage guard checks BOTH raw_text AND these
        fields. The model itself only ever sees raw_text.

    Returns
    -------
    ClassificationResult with predicted label and confidence

    Raises
    ------
    FeatureLeakageError
        If any forbidden field is present in input_metadata.
    ModelNotFoundError
        If the model artifact cannot be found.
    """
    # Feature leakage guard — HARD REQUIREMENT
    if input_metadata:
        _check_feature_leakage(input_metadata, config)

    # Load model if not provided
    if model is None:
        model = load_model(config)

    # Run inference — only raw_text reaches the model
    proba = model.predict_proba([raw_text])[0]
    classes = list(model.classes_)

    # Build probabilities dict
    all_probs: Dict[str, float] = {
        str(cls): round(float(p), 6) for cls, p in zip(classes, proba)
    }

    # Find the best prediction
    best_idx = proba.argmax()
    predicted_label = str(classes[best_idx])
    confidence = float(proba[best_idx])

    calibrated = isinstance(model, CalibratedClassifierCV)
    method = getattr(model, "method", "unknown")
    metadata = getattr(model, "ddc_metadata_", {})
    note = (
        f"Probabilities calibrated using {method}; this does not establish "
        "reliability on new languages or OCR inputs."
        if calibrated else "Uncalibrated model scores; not validated as correctness probabilities."
    )
    if metadata.get("family"):
        note += f" Model family: {metadata['family']}."

    return ClassificationResult(
        predicted_label=predicted_label,
        confidence=round(confidence, 6),
        all_probabilities=all_probs,
        calibrated=calibrated,
        calibration_note=note,
    )
