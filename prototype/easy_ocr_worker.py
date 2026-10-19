"""Bounded offline EasyOCR child process. Never download a model while serving."""
import json
import sys
import os
from pathlib import Path

import easyocr
import torch
from easyocr_compat import configure_tamil

ROOT = Path(__file__).resolve().parents[1]
if os.environ.get('FIELDNOTE_OFFLINE_CHECK') == '1':
    sys.path.insert(0, str(ROOT))
    from prototype.runtime import disable_network_for_check
    disable_network_for_check()
LANGUAGES = {'eng':['en'],'eng+hin':['en','hi'],'eng+mar':['en','mr'],'eng+tam':['en','ta']}
torch.set_num_threads(4)
configure_tamil()
reader = easyocr.Reader(LANGUAGES[sys.argv[2]],gpu=False,model_storage_directory=str(ROOT/'models/ocr_easy'),
                       user_network_directory=str(ROOT/'models/ocr_easy/user_network'),
                       download_enabled=False,verbose=False)
results = reader.readtext(sys.argv[1],detail=1,paragraph=False,decoder='greedy',
                          canvas_size=1600,mag_ratio=1,min_size=12,workers=0)
lines = []
for box,text,confidence in results:
    x = [float(point[0]) for point in box]; y = [float(point[1]) for point in box]
    lines.append({'text':text,'confidence':float(confidence),'left':min(x),'top':min(y),
                  'width':max(x)-min(x),'height':max(y)-min(y)})
print(json.dumps({'lines':lines,'engine':'easyocr-1.7.2-craft'},ensure_ascii=False))
