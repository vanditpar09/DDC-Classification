"""Compare layout modes on a local phone photo; manual crop is diagnostic only."""
import json
import time
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/ocr-phone-review'


def run():
    image = Image.open(OUT / 'english-original.png').convert('RGB')
    variants = {'whole_photo': image,
                'manual_cover_crop': image.crop((210, 260, 1750, 2470))}
    results = []
    for name, variant in variants.items():
        for psm in (6, 3, 11):
            started = time.perf_counter()
            data = pytesseract.image_to_data(ImageOps.grayscale(variant), lang='eng',
                config=f'--tessdata-dir "{ROOT / "models/ocr_tessdata"}" --oem 1 --psm {psm}',
                output_type=pytesseract.Output.DICT, timeout=25)
            lines = {}
            confidences = []
            for i, word in enumerate(data['text']):
                if word.strip() and float(data['conf'][i]) >= 0:
                    lines.setdefault((data['block_num'][i], data['par_num'][i], data['line_num'][i]), []).append(word)
                    confidences.append(float(data['conf'][i]))
            text = '\n'.join(' '.join(line) for line in lines.values())
            results.append({'variant':name,'psm':psm,'text':text,
                'mean_confidence':float(np.mean(confidences)) if confidences else 0,
                'low_confidence_fraction':sum(c<55 for c in confidences)/max(1,len(confidences)),
                'seconds':time.perf_counter()-started,'recognition_passes':1})
    report={'diagnostic_not_benchmark':True,'manual_crop_not_automatic':True,'results':results}
    (OUT / 'layout-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    run()
