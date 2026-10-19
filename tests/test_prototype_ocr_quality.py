"""A high mean must not hide many unreliable words in decorative cover OCR."""
import numpy as np
from PIL import Image

from prototype.controller import Policy, combine_evidence
from prototype.engine import recognize_tesseract as recognize


def test_noisy_cover_is_excluded_despite_high_mean_confidence(monkeypatch):
    rng = np.random.default_rng(42)
    image = Image.fromarray(rng.integers(0, 255, (300, 300), dtype=np.uint8)).convert('RGB')
    words = ['Recognized'] * 10 + ['n0!$e'] * 8
    data = dict(text=words, conf=[96] * 10 + [30] * 8,
                left=[20] * 18, top=[20] * 18, width=[120] * 18, height=[30] * 18,
                block_num=[1] * 18, par_num=[1] * 18, line_num=list(range(18)))
    monkeypatch.setattr('prototype.engine.pytesseract.image_to_data', lambda *args, **kwargs: data)
    result = recognize(image, 'eng', Policy(), allow_osd=False)
    assert result['quality']['ocr_confidence'] > Policy().min_ocr_confidence
    assert not result['usable']
    assert combine_evidence([dict(result, kind='cover')]) == ''
    # Keep raw OCR for inspection, even when it cannot reach the classifier.
    assert 'n0!$e' in result['text']


def test_clear_page_remains_eligible_for_classification(monkeypatch):
    rng = np.random.default_rng(42)
    image = Image.fromarray(rng.integers(0, 255, (300, 300), dtype=np.uint8)).convert('RGB')
    data = dict(text=['Introduction', 'to', 'mathematics'], conf=[96, 97, 95],
                left=[20, 160, 20], top=[20, 20, 70], width=[120, 30, 120], height=[30] * 3,
                block_num=[1] * 3, par_num=[1] * 3, line_num=[1, 1, 2])
    monkeypatch.setattr('prototype.engine.pytesseract.image_to_data', lambda *args, **kwargs: data)
    result = recognize(image, 'eng', Policy(), allow_osd=False)
    assert result['usable']
    assert combine_evidence([dict(result, kind='cover')]) == 'Introduction to\nmathematics'
