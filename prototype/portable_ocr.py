"""Pinned PP-OCR models and offline CPU configuration shared by all platforms."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'models/ocr_rapid'
UPSTREAM = 'https://raw.githubusercontent.com/RapidAI/RapidOCR/v3.4.0/python/rapidocr/default_models.yaml'
BASE = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.4.0/onnx/'
MODELS = {
    'det': {'name': 'ch_PP-OCRv5_server_det.onnx', 'source': BASE+'PP-OCRv5/det/ch_PP-OCRv5_server_det.onnx',
            'sha256': '0f8846b1d4bba223a2a2f9d9b44022fbc22cc019051a602b41a7fda9667e4cad'},
    'rec': {'name': 'ch_PP-OCRv5_rec_server_infer.onnx', 'source': BASE+'PP-OCRv5/rec/ch_PP-OCRv5_rec_server_infer.onnx',
            'sha256': 'e09385400eaaaef34ceff54aeb7c4f0f1fe014c27fa8b9905d4709b65746562a'},
    'cls': {'name': 'ch_ppocr_mobile_v2.0_cls_infer.onnx', 'source': BASE+'PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_infer.onnx',
            'sha256': 'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c'},
    # RapidOCR creates visualization metadata even when only reading text.
    # A local OFL font prevents an unrelated font download at inference time.
    'font': {'name': 'NotoSans.ttf',
             'source': 'https://raw.githubusercontent.com/google/fonts/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf',
             'sha256': 'bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d'},
    'font_license': {'name': 'OFL.txt',
             'source': 'https://raw.githubusercontent.com/google/fonts/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notosans/OFL.txt',
             'sha256': 'cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a'},
}


def models_present(directory=MODEL_DIR):
    try:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        return all((directory / row['name']).is_file() and
                   manifest['files'].get(row['name']) == row['sha256'] for row in MODELS.values())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def verify_models(directory=MODEL_DIR):
    if not models_present(directory):
        raise ValueError('Portable OCR models are missing. Run scripts/setup_scene_ocr.py --reader portable.')
    for row in MODELS.values():
        with (directory / row['name']).open('rb') as handle:
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1024*1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != row['sha256']:
            raise ValueError('Portable OCR model checksum failed: '+row['name'])


def reader_parameters(directory=MODEL_DIR):
    return {
        'Det.model_path': str(directory / MODELS['det']['name']),
        'Rec.model_path': str(directory / MODELS['rec']['name']),
        'Cls.model_path': str(directory / MODELS['cls']['name']),
        'Global.log_level': 'error', 'Global.max_side_len': 1600,
        'Global.font_path': str(directory / MODELS['font']['name']),
        'EngineConfig.onnxruntime.intra_op_num_threads': 4,
        'EngineConfig.onnxruntime.inter_op_num_threads': 1,
        'EngineConfig.onnxruntime.use_cuda': False,
        'EngineConfig.onnxruntime.use_dml': False,
        'Det.limit_side_len': 960, 'Det.limit_type': 'max',
        'Det.max_candidates': 256,
    }
