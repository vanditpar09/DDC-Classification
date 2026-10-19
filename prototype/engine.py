"""Local OCR + multilingual classifier; no cloud services or remote requests."""
from __future__ import annotations

import hashlib
import io
import math
import os
import threading
import time
import uuid
import copy
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from scipy.ndimage import laplace

from prototype.controller import Policy, combine_evidence, decide, normalized_text
from prototype.storage import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
TESSDATA = ROOT / "models/ocr_tessdata"
LANGUAGES = {"eng": "English", "eng+hin": "English + Hindi", "eng+mar": "English + Marathi", "eng+tam": "English + Tamil"}
LABELS = {"000": "Computing & general works", "100": "Philosophy & psychology", "200": "Religion", "300": "Social sciences", "400": "Language", "500": "Science", "600": "Technology", "700": "Arts & recreation", "800": "Literature", "900": "History & geography"}
MAX_BYTES = 12 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


@lru_cache(maxsize=1)
def selected_model_path():
    name = os.environ.get("FIELDNOTE_MODEL", "hierarchy_v1")
    if name not in {"hierarchy_v1", "native_silver_v1", "native_silver_v2"}:
        raise ValueError("FIELDNOTE_MODEL must name a saved project model")
    path = ROOT / "models" / name / "classifier.joblib"
    if name.startswith("native_silver_") and not path.exists():
        raise ValueError("The native silver experiment has not been trained on this machine.")
    if not path.exists():
        path = ROOT / "models/improved_v1/classifier.joblib"
    if not path.exists():
        raise ValueError("Train or restore models/improved_v1/classifier.joblib before using the prototype.")
    return path


@lru_cache(maxsize=1)
def load_classifier():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    return joblib.load(selected_model_path())


def predict(text, pages=None):
    started = time.perf_counter()
    model = load_classifier()
    # The pretrained encoder truncates at 512 tokens. Make the limit visible.
    from src.ocr_pipeline.multilingual import get_encoder, ENCODER_PATH
    tokens = len(get_encoder(ENCODER_PATH).tokenizer.encode("query: " + text, truncation=False))
    p = model.predict_proba([text])[0]
    if not np.isfinite(p).all() or not np.isclose(p.sum(), 1):
        raise ValueError("Classifier produced invalid scores")
    order = np.argsort(p)[::-1]
    result = {
        "label": str(model.classes_[order[0]]), "score": float(p[order[0]]),
        "margin": float(p[order[0]] - p[order[1]]),
        "entropy": float(-np.sum(p * np.log(np.maximum(p, 1e-12))) / math.log(len(p))),
        "top3": [{"label": str(model.classes_[i]), "name": LABELS[str(model.classes_[i])], "score": float(p[i])} for i in order[:3]],
        "token_count": tokens, "truncated": tokens > 512,
    }
    if hasattr(model, "predict_hierarchy"):
        policy = Policy()
        result["hierarchy"] = model.predict_hierarchy([text], policy.min_model_score, policy.min_margin, broad=p[None, :])[0]
    result["inference_seconds"] = time.perf_counter() - started
    result["model_version"] = model_version()
    result["classification_policy"] = "catalog-assisted-v1"
    from src.ocr_pipeline.catalog import match_catalog, apply_catalog, suppress_uncertain_path
    evidence = pages or [{'kind':'cover','text':text,'usable':True,'source':'transcription'}]
    match = match_catalog(evidence)
    result['catalog_match'] = match
    if match['status'] == 'matched':
        result = apply_catalog(result, match)
    else:
        result = suppress_uncertain_path(result)
    return result


@lru_cache(maxsize=1)
def model_version():
    path = selected_model_path()
    return {"name": path.parent.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "experimental": path.parent.name.startswith("native_silver_")}


class Conflict(ValueError):
    """A stale edit or an uncertain previous operation needs user review."""


class MissingSession(ValueError):
    pass


def image_from_bytes(content):
    if len(content) > MAX_BYTES:
        raise ValueError("Image exceeds the 12 MB limit")
    try:
        image = Image.open(io.BytesIO(content))
        if image.width * image.height > 20_000_000:
            raise ValueError("Image exceeds the 20-megapixel limit")
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Upload a valid JPEG, PNG, WebP or other supported raster image") from exc


def recognize_tesseract(image, language, policy, repair=False, allow_osd=True):
    if language not in LANGUAGES:
        raise ValueError("Unsupported OCR language selection")
    for pack in language.split("+"):
        if not (TESSDATA / (pack + ".traineddata")).exists():
            raise ValueError(f"Missing local OCR pack: {pack}")
    from prototype.runtime import find_tesseract
    executable = find_tesseract()
    if not executable:
        raise ValueError('Tesseract is not installed. Install it or set TESSERACT_CMD to its executable path.')
    pytesseract.pytesseract.tesseract_cmd = executable
    start = time.perf_counter()
    original_size = image.size
    working = ImageOps.grayscale(image)
    if repair:
        working = ImageOps.autocontrast(working)
        # Bounded resampling; do not double already large photographs.
        if max(working.size) <= 1800:
            working = working.resize((working.width * 2, working.height * 2), Image.Resampling.LANCZOS)
    sx, sy = original_size[0] / working.width, original_size[1] / working.height
    config = f'--tessdata-dir "{TESSDATA}" --oem 1 --psm 6'
    try:
        data = pytesseract.image_to_data(working, lang=language, config=config, output_type=pytesseract.Output.DICT, timeout=25)
    except (pytesseract.TesseractError, RuntimeError) as exc:
        raise ValueError("Local OCR failed or timed out: " + str(exc)) from exc
    words, lines = [], {}
    for i, text in enumerate(data["text"]):
        if not text.strip() or float(data["conf"][i]) < 0:
            continue
        word = {"text": text.strip(), "confidence": float(data["conf"][i]),
                "left": int(data["left"][i] * sx), "top": int(data["top"][i] * sy),
                "width": max(1, int(data["width"][i] * sx)), "height": max(1, int(data["height"][i] * sy))}
        words.append(word)
        line = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(line, []).append(word["text"])
    text = "\n".join(" ".join(line) for line in lines.values())
    heights = [w["height"] for w in words]
    mean = float(np.mean([w["confidence"] for w in words])) if words else 0
    # Compute sharpness on text bounds, so large blank margins do not dominate.
    if words:
        left = max(0, min(w["left"] for w in words) - 20)
        top = max(0, min(w["top"] for w in words) - 20)
        right = min(image.width, max(w["left"] + w["width"] for w in words) + 20)
        bottom = min(image.height, max(w["top"] + w["height"] for w in words) + 20)
    else:
        left, top, right, bottom = 0, 0, image.width, image.height
    gray = np.asarray(ImageOps.grayscale(image.crop((left, top, right, bottom))), dtype=float)
    sharpness = float(laplace(gray).var())
    bad = [w for w in words if w["confidence"] < policy.min_ocr_confidence]
    low_confidence_fraction = len(bad) / max(1, len(words))
    if bad:
        left = max(0, min(w["left"] for w in bad) - 15)
        top = max(0, min(w["top"] for w in bad) - 15)
        right = min(image.width, max(w["left"] + w["width"] for w in bad) + 15)
        bottom = min(image.height, max(w["top"] + w["height"] for w in bad) + 15)
    script = None
    mismatch = False
    suggested = []
    # OSD is diagnostic only and is included in reported OCR pass/pixel costs.
    osd_passes = 0
    # Save the second reserved pass for a scene-text fallback when recognition
    # is already unreliable. OSD itself cannot repair those missing words.
    preliminarily_usable = mean >= policy.min_ocr_confidence and low_confidence_fraction <= policy.max_low_confidence_fraction
    if allow_osd and len(words) >= 6 and preliminarily_usable:
        osd_passes = 1
        try:
            osd = pytesseract.image_to_osd(working, config=f'--tessdata-dir "{TESSDATA}"', output_type=pytesseract.Output.DICT, timeout=10)
            script = osd.get("script")
            confident = float(osd.get("script_conf", 0)) >= 5
            if confident and script == "Devanagari" and not any(l in language for l in ("hin", "mar")):
                mismatch, suggested = True, ["eng+hin", "eng+mar"]
            if confident and script == "Tamil" and "tam" not in language:
                mismatch, suggested = True, ["eng+tam"]
        except (pytesseract.TesseractError, RuntimeError):
            pass
    median = float(np.median(heights)) if heights else 0
    usable = (bool(text.strip()) and mean >= policy.min_ocr_confidence
              and low_confidence_fraction <= policy.max_low_confidence_fraction
              and sharpness >= policy.min_sharpness and not mismatch)
    # Small text deserves a bounded repair even when its first OCR score is high.
    if not repair and 0 < median < policy.min_character_height:
        usable = False
    return {
        "text": text, "words": words, "usable": usable,
        "quality": {"ocr_confidence": mean, "word_count": len(words), "median_character_height": median,
                    "low_confidence_fraction": low_confidence_fraction,
                    "engine": "tesseract", "confidence_source": "word recognizer; uncalibrated",
                    "sharpness": sharpness, "script": script, "script_mismatch": mismatch, "suggested_languages": suggested,
                    "region": {"left": left, "top": top, "width": right - left, "height": bottom - top,
                               "image_width": image.width, "image_height": image.height}},
        "work": {"ocr_passes": 1 + osd_passes, "pixels": working.width * working.height * (1 + osd_passes),
                 "seconds": time.perf_counter() - start},
    }


def recognize(image, language, policy, repair=False, allow_osd=True):
    """Prefer local scene OCR for English; repair unreliable native-script OCR.

    A scene fallback occupies the second reserved OCR pass. No model downloads
    occur while serving, and selected Indian scripts never use English Vision.
    """
    if language not in LANGUAGES:
        raise ValueError("Unsupported OCR language selection")
    from prototype.scene_ocr import vision_ready, easy_ready, rapid_ready, recognize_scene
    started = time.perf_counter()
    mode = os.environ.get('FIELDNOTE_OCR', 'auto')
    if mode not in {'auto','portable','tesseract'}:
        raise ValueError('FIELDNOTE_OCR must be auto, portable or tesseract')
    backend = None
    if mode in {'auto', 'portable'}:
        if mode == 'portable' and language == 'eng' and not rapid_ready(language):
            raise ValueError('Portable English OCR is not ready. Run scripts/setup_scene_ocr.py --reader portable.')
        if mode == 'auto' and language == 'eng' and vision_ready():
            backend = 'vision'
        elif language == 'eng' and rapid_ready(language):
            backend = 'rapid'
        elif (language == 'eng' or repair) and easy_ready(language):
            backend = 'easy'
    if backend:
        try:
            result = recognize_scene(image,language,policy,backend)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            if not allow_osd:
                raise ValueError('The local OCR reader failed within the remaining pass budget. Capture again or enter checked text.')
            fallback = recognize_tesseract(image,language,policy,repair=repair,allow_osd=False)
            fallback['work']['ocr_passes'] += 1
            fallback['work']['pixels'] += image.width*image.height
            fallback['work']['seconds'] = time.perf_counter()-started
            fallback['quality']['fallback_reason'] = 'Local scene reader failed; bounded Tesseract fallback used'
            return fallback
        if not result['usable'] and allow_osd:
            # Keep this outside the scene exception handler: a failure in the
            # second reader must not trigger a third recognition attempt.
            alternate = recognize_tesseract(image,language,policy,repair=repair,allow_osd=False)
            chosen = alternate if alternate['usable'] else result
            chosen['work'] = {'ocr_passes':2,
                'pixels':result['work']['pixels']+alternate['work']['pixels'],
                'seconds':time.perf_counter()-started}
            chosen['quality']['attempts'] = [{'engine':candidate['quality'].get('engine'),
                'text':candidate['text'],'usable':candidate['usable'],
                'mean_confidence':candidate['quality'].get('ocr_confidence')}
                for candidate in (result,alternate)]
            return chosen
        return result
    result = recognize_tesseract(image,language,policy,repair=repair,allow_osd=allow_osd)
    if (mode in {'auto', 'portable'} and not result['usable'] and allow_osd
            and result['work']['ocr_passes']==1 and easy_ready(language)):
        try:
            scene = recognize_scene(image,language,policy,'easy')
            work = {key: result['work'][key]+scene['work'][key] for key in ('ocr_passes','pixels')}
            work['seconds'] = time.perf_counter()-started
            # Do not swap a rejected first result for another rejected result.
            chosen = scene if scene['usable'] else result
            chosen['work'] = work
            chosen['quality']['scene_fallback_attempted'] = True
            chosen['quality']['attempts'] = [{'engine':candidate['quality'].get('engine'),
                'text':candidate['text'],'usable':candidate['usable'],
                'mean_confidence':candidate['quality'].get('ocr_confidence')}
                for candidate in (result,scene)]
            return chosen
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            result['work']['ocr_passes'] += 1
            result['work']['pixels'] += image.width*image.height
            result['work']['seconds'] = time.perf_counter()-started
            result['quality']['fallback_reason'] = 'Local scene reader failed; original OCR retained for review'
    return result


class Engine:
    def __init__(self, predictor=None, recognizer=None, store=None):
        self.contextual_predictor = predictor is None
        self.predictor = predictor or predict
        self.recognizer = recognizer or recognize
        self.policy = Policy()
        self.store = store or MemoryStore()
        self.lock = threading.RLock()

    def new_session(self):
        with self.lock:
            now = time.time()
            if len(self.store.list()) >= 100:
                raise ValueError("100 saved books reached. Export and delete books before adding more.")
            sid = str(uuid.uuid4())
            session = {"id": sid, "updated": now, "pages": [], "events": [], "prediction": None,
                       "created": now, "revision": 0, "reviews": [], "page_history": [],
                       "policy_version": "adaptive-hierarchy-v3-ocr", "ocr_version": "local-scenes-v2-portable", "model_version": model_version(),
                       "combined_text": "", "work": {"ocr_passes": 0, "pixels": 0, "seconds": 0, "classifier_calls": 0, "duplicate_uploads": 0}}
            session["decision"] = decide([], None, 0, self.policy)
            self.store.save(session)
            return session

    def get(self, sid):
        with self.lock:
            session = self.store.get(sid)
            if session is None:
                raise MissingSession("Book not found. Select a saved book or start a new one.")
            return session

    def list_sessions(self):
        with self.lock:
            return [{"id": s["id"], "updated": s["updated"], "revision": s["revision"],
                     "title": ((s.get("prediction") or {}).get("catalog_match", {}).get("record", {}).get("title") or (s["combined_text"].splitlines() or ["Untitled book"])[0])[:100],
                     "page_count": len(s["pages"])} for s in self.store.list()]

    def get_image(self, sid, pid):
        content = self.store.image(sid, pid)
        if content is None:
            raise ValueError("Image not found")
        # Encoded PNG written by the server after input validation and EXIF removal.
        return image_from_bytes_unlimited(content)

    def execute(self, sid, key, fingerprint, revision, operation):
        """One writer. Record intent before work, and never repeat an uncertain call.

        A crash between intent and completion requires explicit review; it is
        deliberately not silently retried. Successful replays return current state.
        """
        with self.lock:
            session = self.get(sid)
            if key:
                if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", key):
                    raise ValueError("Invalid operation ID")
                receipt = self.store.receipt(sid, key)
                if receipt:
                    if receipt["fingerprint"] != fingerprint:
                        raise Conflict("This operation ID was already used for different evidence.")
                    if receipt["status"] == "complete":
                        if receipt.get("revision") != session["revision"]:
                            raise Conflict("The previous upload was saved, but this book has changed since then. Reload and inspect the evidence before submitting more.")
                        return copy.deepcopy(session)
                    raise Conflict("The previous attempt did not complete reliably. Reload this book and inspect its trace before submitting a new capture.")
            if revision is not None and revision != session["revision"]:
                raise Conflict("This book changed on another page. Reload the book before applying pending evidence.")
            if key:
                self.store.record(sid, key, {"fingerprint": fingerprint, "status": "pending"})
            try:
                result = operation()
            except Exception:
                if key:
                    self.store.record(sid, key, {"fingerprint": fingerprint, "status": "failed"})
                raise
            if key:
                self.store.record(sid, key, {"fingerprint": fingerprint, "status": "complete", "revision": result["revision"]})
            return copy.deepcopy(result)

    def delete(self, sid):
        with self.lock:
            self.store.delete(sid)

    def reclassify(self, sid):
        """Explicitly update saved predictions without rerunning/replacing OCR."""
        with self.lock:
            session=self.get(sid)
            self._validate(session,'cover','eng')
            text=session['combined_text']
            if not text:raise ValueError('Add readable evidence before updating the prediction.')
            history=session.setdefault('prediction_history',[])
            if len(history)>=20:raise ValueError('Prediction history limit reached. Export before further updates.')
            history.append({'at':time.time(),'evidence_revision':session['revision'],
                            'prediction':copy.deepcopy(session['prediction'])})
            attempt={'event':'prediction_update','status':'pending','reason':'Updating classification from saved evidence; OCR is unchanged.'}
            session['events'].append(attempt)
            session['work']['classifier_calls']+=1
            self._save(session)
            try:
                prediction=(self.predictor(text,pages=session['pages']) if self.contextual_predictor else self.predictor(text))
            except Exception:
                attempt.update(status='failed',reason='Prediction update failed; prior result and all evidence are retained.')
                self._save(session)
                raise
            session['prediction']=prediction
            session['model_version']=prediction.get('model_version',model_version())
            decision=decide(session['pages'],prediction,session['work']['ocr_passes'],self.policy)
            if prediction.get('truncated') and prediction.get('result_source')!='local_catalog' and decision['action']=='ready_for_review':
                decision.update(action='human_review',title='Review the full page text',reason='The encoder saw only the first 512 tokens. Review the full evidence.')
            session['decision']=decision
            attempt.update(status='complete',action=decision['action'],reason=decision['reason'])
            self._save(session)
            return session

    def _save(self, session, image=None):
        session["updated"] = time.time()
        session["revision"] += 1
        self.store.save(session, image)

    def add_review(self, sid, code, reviewer, note, book_id):
        with self.lock:
            session = self.get(sid)
            if not re.fullmatch(r"[0-9]{3}", code) or not reviewer.strip():
                raise ValueError("Supply a three-digit DDC section and a reviewer name.")
            if len(session["reviews"]) >= 20:
                raise ValueError("Review history limit reached. Export this book before further review.")
            session["reviews"].append({"section": code, "division": code[:2] + "0", "class": code[0] + "00",
                                       "reviewer": reviewer.strip(), "note": note, "book_id": book_id,
                                       "at": time.time(), "evidence_revision": session["revision"],
                                       "prediction": copy.deepcopy(session["prediction"])})
            self._save(session)
            return session

    def _validate(self, session, kind, language):
        if kind not in {"cover", "back_cover", "contents"} or language not in LANGUAGES:
            raise ValueError("Invalid page type or OCR language")
        if len(session["events"]) >= 40:
            raise ValueError("Session action limit reached. Review this book or start a new session.")

    def add_text(self, sid, kind, text, language):
        with self.lock:
            session = self.get(sid)
            self._validate(session, kind, language)
            if not text.strip() or len(text) > 12000:
                raise ValueError("Enter between 1 and 12,000 characters")
            page = {"id": str(uuid.uuid4()), "kind": kind, "text": text.strip(), "language": language,
                    "source": "transcription", "usable": True, "quality": None, "words": [], "repairs": 0}
            return self._update(session, page, "transcription_added")

    def add_image(self, sid, kind, content, language):
        with self.lock:
            session = self.get(sid)
            self._validate(session, kind, language)
            digest = hashlib.sha256(content).hexdigest()
            for page in session["pages"]:
                if page.get("digest") == digest and page["language"] == language:
                    session["work"]["duplicate_uploads"] += 1
                    session["events"].append({"event": "duplicate_upload_ignored", "reason": "Identical image and OCR language; no processing repeated.", "ocr_passes": session["work"]["ocr_passes"]})
                    self._save(session)
                    return session
            image = image_from_bytes(content)
            result = self._recognize(session, image, language)
            page = dict(result, id=str(uuid.uuid4()), kind=kind, language=language, source="ocr", repairs=0, digest=digest)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return self._update(session, page, "image_analyzed", image=(page["id"], buffer.getvalue()))

    def repair(self, sid, pid, language=None):
        with self.lock:
            session = self.get(sid)
            self._validate(session, "cover", language or "eng")
            previous = next((p for p in session["pages"] if p["id"] == pid), None)
            if not previous or previous["source"] != "ocr":
                raise ValueError("Image page not found")
            target_language = language or previous["language"]
            if previous["repairs"] >= 1:
                raise ValueError("One repair per image is allowed. Capture a clearer image or request human review.")
            if session["work"]["ocr_passes"] >= self.policy.max_ocr_passes:
                raise ValueError("OCR budget exhausted")
            # Reserve the repair before executing: failures cannot bypass its limit.
            previous["repairs"] += 1
            result = self._recognize(session, self.get_image(sid, pid), target_language, repair=True)
            page = dict(previous, **result)
            page.update(language=target_language)
            return self._update(session, page, "ocr_reprocessed")

    def _recognize(self, session, image, language, repair=False):
        remaining = self.policy.max_ocr_passes - session["work"]["ocr_passes"]
        if remaining <= 0:
            raise ValueError("OCR budget exhausted. Review the book or begin a new session.")
        reserved = min(remaining, 2)
        session["work"]["ocr_passes"] += reserved
        event = {"event": "ocr_attempt", "reason": "OCR started; reserved pass count is an upper bound until completion.",
                 "reserved_passes": reserved, "status": "pending", "at": time.time()}
        session["events"].append(event)
        session["decision"] = {**decide(session["pages"], session["prediction"], session["work"]["ocr_passes"], self.policy),
                               "action": "human_review", "title": "OCR attempt pending",
                               "reason": "If the server was interrupted, inspect this attempt before submitting another capture. Reserved passes remain charged until completion."}
        self._save(session)
        start = time.perf_counter()
        try:
            result = self.recognizer(image, language, self.policy, repair=repair, allow_osd=reserved >= 2)
        except Exception:
            session["work"]["seconds"] += time.perf_counter() - start
            event.update(status="failed", reason="OCR failed. Reserved passes remain charged; processed pixels are unknown.")
            session["decision"].update(title="OCR did not finish", reason="The failed OCR attempt is recorded with a conservative pass reservation. Inspect the trace before trying another capture.")
            self._save(session)
            raise
        work = result.pop("work")
        session["work"]["ocr_passes"] += work["ocr_passes"] - reserved
        for key in ("pixels", "seconds"):
            session["work"][key] += work[key]
        event.update(status="complete", reason="OCR completed; actual work recorded.", work=work)
        self._save(session)
        return result

    def _update(self, session, page, event, image=None):
        session.update(policy_version='adaptive-hierarchy-v3-ocr',ocr_version='local-scenes-v2-portable')
        old_page = next((p for p in session["pages"] if p["kind"] == page["kind"]), None)
        others = [dict(p) for p in session["pages"] if p["kind"] != page["kind"]]
        page["sequence"] = len(session["events"])
        pages = others + [page]
        # Recompute after replacement: formerly repeated evidence may now be
        # unique if the page it duplicated was corrected or removed.
        seen = set()
        for current in sorted(pages, key=lambda p: p["sequence"]):
            key = normalized_text(current["text"])
            current["duplicate"] = bool(key and current["usable"] and key in seen)
            if key and current["usable"]:
                seen.add(key)
        combined = combine_evidence(pages)
        previous_combined = session["combined_text"]
        prediction = session["prediction"]
        if old_page:
            session["page_history"].append({"replaced_at": time.time(), "page": copy.deepcopy(old_page)})
        session.update(pages=pages, combined_text=combined)
        catalog_changed = False
        if combined and prediction and self.contextual_predictor:
            from src.ocr_pipeline.catalog import match_catalog
            current_match = match_catalog(pages)
            previous_match = prediction.get('catalog_match', {})
            def identity(match):
                return (match.get('status'), match.get('record', {}).get('id'), match.get('record', {}).get('section'))
            catalog_changed = identity(current_match) != identity(previous_match)
        if combined != previous_combined or catalog_changed or (combined and prediction is None):
            session["prediction"] = None
            session["decision"] = {**decide(pages, None, session["work"]["ocr_passes"], self.policy),
                                   "action": "human_review", "title": "Classification pending",
                                   "reason": "Evidence is saved. Classification has not completed."}
            self._save(session, image)
            image = None
            if combined:
                session["work"]["classifier_calls"] += 1
                self._save(session)
            try:
                prediction = (self.predictor(combined, pages=pages) if self.contextual_predictor
                              else self.predictor(combined)) if combined else None
            except Exception:
                session["events"].append({"event": "classification_failed", "reason": "Evidence and OCR work are saved. Classification failed; inspect the server log before continuing."})
                self._save(session)
                raise
        session.update(pages=pages, prediction=prediction, combined_text=combined, updated=time.time())
        work = page.pop("work", None)
        if work:
            for k in ("ocr_passes", "pixels", "seconds"):
                session["work"][k] += work[k]
        decision = decide(pages, prediction, session["work"]["ocr_passes"], self.policy)
        if prediction and prediction.get("truncated") and prediction.get("result_source") != "local_catalog" and decision["action"] == "ready_for_review":
            decision.update(action="human_review", title="Review the full page text", reason="The encoder saw only the first 512 tokens. Do not treat an incomplete reading as sufficient evidence.")
        session["decision"] = decision
        session["events"].append({"event": event, "page": page["kind"], "language": page["language"],
                                  "action": decision["action"], "reason": decision["reason"],
                                  "ocr_passes": session["work"]["ocr_passes"],
                                  "model_score": prediction["score"] if prediction else None})
        self._save(session, image)
        return session


def image_from_bytes_unlimited(content):
    """Read our own lossless encoding, which can be larger than the upload limit."""
    with Image.open(io.BytesIO(content)) as image:
        image.load()
        return image.convert("RGB")
