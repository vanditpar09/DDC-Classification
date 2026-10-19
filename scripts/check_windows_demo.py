"""Check portable demo assets and optionally run an offline four-image smoke test."""
import argparse
import hashlib
import importlib.util
import importlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='Asset checks only, without photo recognition/classification')
    args = parser.parse_args()
    os.environ.update(FIELDNOTE_OCR='portable', FIELDNOTE_MODEL='native_silver_v2',
                      HF_HUB_OFFLINE='1', FIELDNOTE_OFFLINE_CHECK='1', TOKENIZERS_PARALLELISM='false')
    from prototype.runtime import find_tesseract
    from prototype.portable_ocr import verify_models
    issues = []
    for package in ('torch', 'torchvision', 'sentence_transformers', 'rapidocr', 'onnxruntime',
                    'easyocr', 'cv2', 'pytesseract', 'fastapi', 'uvicorn', 'multipart'):
        if importlib.util.find_spec(package) is None:
            issues.append('Missing Python package: '+package)
        else:
            try:
                importlib.import_module(package)
            except (ImportError, OSError, RuntimeError) as error:
                issues.append('Package could not load: '+package+' ('+str(error)+
                    '). For missing Windows DLLs, install the Microsoft Visual C++ x64 runtime; see docs/WINDOWS_DEMO.md.')
    executable = find_tesseract()
    if not executable:
        issues.append('Install Tesseract, or set TESSERACT_CMD to its executable path')
    else:
        try:
            subprocess.run([executable, '--version'], capture_output=True, check=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            issues.append('Tesseract could not run')
    for name in ('eng', 'osd', 'hin', 'mar', 'tam'):
        if not (ROOT / 'models/ocr_tessdata' / (name+'.traineddata')).is_file():
            issues.append('Missing Tesseract language pack: '+name)
    try:
        verify_models()
    except (ValueError, OSError) as error:
        issues.append(str(error))
    from prototype.scene_ocr import easy_ready
    for language in ('eng+hin', 'eng+mar', 'eng+tam'):
        if not easy_ready(language):
            issues.append('EasyOCR fallback not prepared: '+language)
    classifier = ROOT / 'models/native_silver_v2/classifier.joblib'
    if not classifier.is_file():
        issues.append('Missing trained native_silver_v2 classifier')
    encoder = ROOT / 'models/encoders/multilingual-e5-small'
    for name in ('config.json', 'model.safetensors', 'tokenizer.json', 'modules.json', '1_Pooling/config.json'):
        if not (encoder / name).is_file():
            issues.append('Missing local classifier encoder file: '+name)
    report = {'checked_at':time.time(), 'host_platform':platform.system(),
        'host_python':platform.python_version(), 'reader_mode':'portable',
        'apple_vision_used':False, 'physical_windows_test':platform.system()=='Windows',
        'physical_phone_test':False, 'accuracy_benchmark':False,
        'classification_accuracy_validated':False, 'catalog_regression_validated':False, 'issues':issues, 'checks':[],
        'quick_asset_check_only':args.quick}
    if not issues and not args.quick:
        from prototype.runtime import disable_network_for_check
        disable_network_for_check()
        from PIL import Image
        from prototype.engine import Engine
        cases = [{'case':'phone-english-cover','language':'eng',
            'source_image':'data/research/ocr-upgrade-v1/fixtures/phone-english-cover.png'}]
        cases += [{'case':row['work_id'], 'language':'eng+'+row['language'], 'source_image':row['source_image']}
                  for row in json.loads((ROOT / 'data/research/multilingual-pilot-v1/experiment-v2/local-server-smoke.json').read_text(encoding='utf-8'))['checks']]
        engine = Engine()
        for case in cases:
            try:
                image = Image.open(ROOT / case['source_image']).convert('RGB')
                import io
                content = io.BytesIO(); image.save(content, format='PNG')
                sid = engine.new_session()['id']
                state = engine.add_image(sid, 'cover', content.getvalue(), case['language'])
                page = state['pages'][0]
                text = ' '.join(page['text'].casefold().split())
                passed = page['usable'] and len(state['prediction']['hierarchy']['path']) == 3
                if case['language'] == 'eng':
                    passed = passed and 'the kite runner' in text and 'khaled hosseini' in text
                    passed = passed and not any(word in text for word in ('control', 'option', 'command'))
                    passed = passed and [r['label'] for r in state['prediction']['hierarchy']['path']] == ['800','810','813']
                    passed = passed and state['prediction'].get('result_source') == 'local_catalog'
                    report['catalog_regression_validated'] = bool(passed)
                report['checks'].append({**case, 'passed':bool(passed), 'text':page['text'],
                    'quality':page['quality'], 'work':state['work'],
                    'suggested_path':[level['label'] for level in state['prediction']['hierarchy']['path']],
                    'result_source':state['prediction'].get('result_source'),
                    'ddc_correctness_asserted':case['language']=='eng'})
                if not passed:
                    issues.append('Offline photo check failed: '+case['case'])
            except Exception as error:
                issues.append('Offline photo check failed: '+case['case']+' ('+type(error).__name__+': '+str(error)+')')
    report['passed'] = not issues
    if classifier.is_file():
        report['ddc_model_sha256'] = hashlib.sha256(classifier.read_bytes()).hexdigest()
    destination = ROOT / 'output/windows-demo'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / ('preflight.json' if args.quick else 'offline-smoke.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for issue in issues:
        print('Needs attention: '+issue)
    print(('PASS' if report['passed'] else 'FAIL')+': '+
          ('portable demo asset checks' if args.quick else 'offline portable demo smoke test')+
          ' on '+platform.system()+'. Report: '+str(destination))
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    run()
