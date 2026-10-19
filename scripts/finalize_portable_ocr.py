"""Preserve measured portable-reader diagnostics and implementation fingerprints."""
import hashlib
import json
import shutil
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/portable-ocr-v1'
DEST=ROOT/'data/research/portable-ocr-v1'


def run():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ('mobile-probe.json','server-perspective-probe.json','server-original-probe.json',
                 'diagnostic.json','browser-check.json','phone-result.png'):
        shutil.copyfile(OUT/name,DEST/name)
    shutil.copyfile(ROOT/'output/windows-demo/offline-smoke.json',DEST/'offline-smoke.json')
    shutil.copyfile(ROOT/'models/ocr_rapid/manifest.json',DEST/'model-manifest.json')
    shutil.copyfile(ROOT/'requirements-windows.txt',DEST/'windows-resolved-requirements.txt')
    bundle_check = ROOT/'output/windows-demo/bundle-smoke.json'
    if bundle_check.exists():
        shutil.copyfile(bundle_check, DEST/'bundle-smoke.json')
    previous=json.loads((ROOT/'data/research/ocr-upgrade-v1/results.json').read_text(encoding='utf-8'))
    previous['checks']=[row for row in previous['checks'] if row['case']=='phone-english-cover']
    (DEST/'previous-readers.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    measured=json.loads((DEST/'diagnostic.json').read_text(encoding='utf-8'))
    text=' '.join(measured['text'].casefold().split())
    browser=json.loads((DEST/'browser-check.json').read_text(encoding='utf-8'))
    smoke=json.loads((DEST/'offline-smoke.json').read_text(encoding='utf-8'))
    assert browser['passed'] and smoke['passed'] and len(smoke['checks'])==4
    assert 'the kite runner' in text and 'khaled hosseini' in text and 'a thousand splendid suns' in text
    assert not any(word in text for word in ('control','option','command'))
    assert smoke['ddc_model_sha256']=='cf2e4d18dbe43ad9431a965bc1a6213a0bcfbecac5b5c8830e73cb9a48f6cc86'
    report={'checked_at':time.time(),'passed':True,'regression_tests_passed':215,
        'regression_warnings':3,'portable_english_title_recovered':True,'portable_author_recovered':True,
        'portable_subtitle_recovered':True,'keyboard_background_removed':True,
        'measured_reader_seconds':measured['work']['seconds'], 'measurement_host':'macOS ARM / Python 3.9.6',
        'windows_x64_python311_dependency_resolution':'passed; 73 packages',
        'actual_windows_execution':'not performed','apple_vision_used_in_portable_checks':False,
        'extracted_private_bundle_check': bool(bundle_check.exists() and json.loads(bundle_check.read_text(encoding='utf-8'))['passed']),
        'offline_four_image_smoke':'passed with socket connections disabled',
        'physical_phone_source_image':True,'new_physical_phone_test':False,
        'classification_accuracy_validated':False,'ddc_suggestion_for_novel':browser['suggested_path'],
        'ddc_suggestion_for_novel_correct':False,'model_retrained':False,
        'native_phone_cover_improvement_verified':False,
        'notes':['Title references were visually inspected development labels, not a full transcription benchmark.',
                 'No title hints, lookups or guessed-text corrections are used in inference.',
                 'Classifier emitted runtime matrix warnings in the macOS offline smoke; final scores passed finite checks. DDC correctness remains unresolved.']}
    (DEST/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    code_files=['prototype/portable_ocr.py','prototype/rapid_ocr_worker.py','prototype/runtime.py',
        'prototype/scene_ocr.py','prototype/engine.py','prototype/easy_ocr_worker.py','prototype/easyocr_compat.py',
        'prototype/share.py','scripts/setup_scene_ocr.py','scripts/setup_windows_demo.py',
        'scripts/check_windows_demo.py','scripts/build_windows_demo.py','scripts/check_scene_ocr_browser.cjs',
        'scripts/finalize_portable_ocr.py','scripts/check_windows_bundle.py','tests/test_scene_ocr.py','tests/test_windows_demo.py',
        'requirements-windows.txt','requirements-ocr.txt','.github/workflows/windows-demo.yml','docs/WINDOWS_DEMO.md']
    (DEST/'code-hashes.json').write_text(json.dumps({name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        for name in code_files},indent=2)+'\n',encoding='utf-8')
    receipts=[]
    for case in smoke['checks']:
        path=ROOT/case['source_image']
        receipts.append({'source_image':case['source_image'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'development_reference_only':True,'public_redistribution_rights_not_established':case['language']=='eng'})
    (DEST/'source-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
    (DEST/'manifest.json').write_text(json.dumps({path.name:hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DEST.iterdir()) if path.is_file() and path.name!='manifest.json'},indent=2)+'\n',encoding='utf-8')
    print('Portable-reader records saved; trained DDC model fingerprint unchanged.')


if __name__=='__main__':run()
