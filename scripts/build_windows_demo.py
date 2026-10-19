"""Export an allowlisted private demo project with local models, without secrets."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENCODER_FILES=('config.json','model.safetensors','modules.json','sentence_bert_config.json',
    'sentencepiece.bpe.model','special_tokens_map.json','tokenizer.json','tokenizer_config.json','1_Pooling/config.json')


def selected_files():
    paths=set()
    for directory in ('prototype','src'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.log'):
                paths.add(path)
    for name in ('requirements-ml.txt','requirements-ocr.txt','requirements-windows.txt','prototype/requirements.txt',
                 'docs/WINDOWS_DEMO.md','docs/LOCAL_SCENE_OCR.md',
                 'scripts/setup_windows_demo.py','scripts/setup_scene_ocr.py','scripts/check_windows_demo.py',
                 'scripts/windows-setup.cmd','scripts/windows-start.cmd','scripts/windows-check.cmd','scripts/windows-share.cmd',
                 'models/native_silver_v2/classifier.joblib','models/native_silver_v2/metadata.json',
                 'data/research/ocr-upgrade-v1/fixtures/phone-english-cover.png',
                 'data/research/ocr-upgrade-v1/source-receipt.json',
                 'data/research/multilingual-pilot-v1/experiment-v2/local-server-smoke.json'):
        paths.add(ROOT/name)
    for name in ENCODER_FILES:
        paths.add(ROOT/'models/encoders/multilingual-e5-small'/name)
    for directory,patterns in [('ocr_tessdata',('*.traineddata','setup_manifest.json')),
                               ('ocr_easy',('*.pth','manifest.json'))]:
        for pattern in patterns:
            paths.update((ROOT/'models'/directory).glob(pattern))
    import sys
    sys.path.insert(0,str(ROOT))
    from prototype.portable_ocr import MODEL_DIR,MODELS,verify_models
    verify_models()
    paths.add(MODEL_DIR/'manifest.json')
    for row in MODELS.values():paths.add(MODEL_DIR/row['name'])
    for row in json.loads((ROOT/'data/research/multilingual-pilot-v1/experiment-v2/local-server-smoke.json').read_text(encoding='utf-8'))['checks']:
        paths.add(ROOT/row['source_image'])
    missing=[str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:raise ValueError('Missing demo files: '+', '.join(missing))
    return sorted(paths)


def run():
    from build_demo_packages import build
    build('windows')


if __name__=='__main__':run()
