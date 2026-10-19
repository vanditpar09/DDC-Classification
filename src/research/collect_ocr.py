"""Read permitted collection images locally into a NEW raw-OCR JSONL variant.

No repairs, cloud services, transliteration or correction. References/labels are
preserved; failed/empty OCR remains empty and is counted by the evaluator.
"""
import argparse
import json
from pathlib import Path

from prototype.controller import Policy
from prototype.engine import image_from_bytes, recognize
from src.research.collection import read_jsonl, validate_records


def collect(source,output):
    if output.exists():raise ValueError('Choose a new output file; never overwrite reviewed transcriptions')
    if output.parent.resolve()!=source.parent.resolve():
        raise ValueError('Save the OCR variant beside the source to preserve relative image paths')
    rows=validate_records(read_jsonl(source),source.parent)
    pages=failures=0
    for row in rows:
        language='eng' if row['language']=='eng' else 'eng+'+row['language']
        for page in row['pages']:
            if page['origin']!='native_scan':continue
            pages+=1
            try:
                result=recognize(image_from_bytes((source.parent/page['image_path']).read_bytes()),
                                 language,Policy(),allow_osd=False)
                page['ocr_text']=result['text']
                page['ocr_run']={'language':language,'quality':result['quality'],'work':result['work'],
                                 'strategy':'one_pass_no_repair','error':None}
                if not result['text'].strip():failures+=1
            except ValueError as error:
                failures+=1;page['ocr_text']=''
                page['ocr_run']={'language':language,'strategy':'one_pass_no_repair','error':str(error)}
    output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    return {'output':str(output),'native_scan_pages':pages,'empty_or_failed_pages':failures}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(collect(args.source,args.output),indent=2))


if __name__=='__main__':main()
