"""One offline, bounded PP-OCR detection/recognition process using CPU ONNX."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prototype.portable_ocr import reader_parameters, verify_models


def run():
    import os
    if os.environ.get('FIELDNOTE_OFFLINE_CHECK') == '1':
        from prototype.runtime import disable_network_for_check
        disable_network_for_check()
    if sys.argv[2] != 'eng':
        raise ValueError('The portable scene reader is validated only for English selection')
    verify_models()
    from rapidocr import RapidOCR
    from rapidocr.utils import DownloadFile

    def no_download(*args, **kwargs):
        raise RuntimeError('Model downloads are disabled during OCR inference')
    DownloadFile.run = no_download
    reader = RapidOCR(params=reader_parameters())
    result = reader(sys.argv[1])
    lines = []
    if result.txts:
        for box, text, confidence in zip(result.boxes, result.txts, result.scores):
            xs, ys = box[:, 0], box[:, 1]
            lines.append({'text': text, 'confidence': float(confidence),
                'left': float(xs.min()), 'top': float(ys.min()),
                'width': float(xs.max()-xs.min()), 'height': float(ys.max()-ys.min())})
    print(json.dumps({'lines': lines, 'engine': 'rapidocr-3.4.0-ppocrv5-server-cpu'}, ensure_ascii=False))


if __name__ == '__main__':
    run()
