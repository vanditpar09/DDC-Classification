"""Local development checks on the saved phone failure and three native pages."""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from prototype.controller import Policy
from prototype.engine import recognize, recognize_tesseract
from prototype.scene_ocr import recognize_scene


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english-only',action='store_true')
    args = parser.parse_args()
    out = ROOT/'output/ocr-upgrade-v1'
    out.mkdir(parents=True,exist_ok=True)
    policy = Policy()
    fixture = ROOT/'data/research/ocr-upgrade-v1/fixtures/phone-english-cover.png'
    original = Image.open(fixture if fixture.exists() else ROOT/'output/ocr-phone-review/english-original.png').convert('RGB')
    rows=[]
    for name,call in [('tesseract-before',lambda:recognize_tesseract(original,'eng',policy,allow_osd=False)),
                      ('auto-after',lambda:recognize(original,'eng',policy)),
                      ('portable-easyocr',lambda:recognize_scene(original,'eng',policy,'easy'))]:
        result=call()
        text=' '.join(result['text'].casefold().split())
        row={'case':'phone-english-cover','reader':name,'title_recovered':'the kite runner' in text,
             'author_recovered':'khaled hosseini' in text,'background_keyboard_text':any(word in text for word in ['control','option','command']),
             'result':result}
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    if not args.english_only:
        old=json.loads((ROOT/'data/research/multilingual-pilot-v1/experiment-v2/local-server-smoke.json').read_text())
        for sample in old['checks']:
            image=Image.open(ROOT/sample['source_image']).convert('RGB')
            lang='eng+'+sample['language']
            result=recognize(image,lang,policy)
            assert result['usable'] and result['text'].strip()
            rows.append({'case':sample['work_id'],'reader':'auto-native','result':result,
                         'reference_is_ground_truth':False,'physical_phone_test':False})
            scene=recognize_scene(image,lang,policy,'easy')
            rows.append({'case':sample['work_id'],'reader':'easy-native-development-comparison','result':scene,
                         'reference_is_ground_truth':False,'physical_phone_test':False})
            print(json.dumps({'native_case':sample['work_id'],'auto_usable':result['usable'],
                              'easy_usable':scene['usable'],'easy_seconds':scene['work']['seconds']}),flush=True)
    passed=rows[1]['title_recovered'] and rows[1]['author_recovered'] and not rows[1]['background_keyboard_text']
    (out/'results.json').write_text(json.dumps({'checked_at':time.time(),'passed':passed,
        'development_diagnostic_not_accuracy_benchmark':True,'checks':rows},ensure_ascii=False,indent=2)+'\n')
    assert passed


if __name__=='__main__':run()
