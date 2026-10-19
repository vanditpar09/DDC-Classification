"""Build a reproducible local match index from saved catalog responses only."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.ocr_pipeline.catalog import section_from_codes


def run():
    entries=[]
    for row in map(json.loads,(ROOT/'data/books.jsonl').read_text(encoding='utf-8').splitlines()):
        section=section_from_codes(row['ddc_raw'])
        if section and section[0]==row['label_level_1'][0] and row['authors']:
            entries.append({'id':row['document_id'],'title':row['title'],'authors':row['authors'],
                'section':section,'ddc_raw':row['ddc_raw'],'isbns':row['isbns'],
                'source_urls':row['source_urls'],'curated':False,
                'label_note':'Existing weak catalog metadata, not independent librarian verification'})
    for filename in ('openlibrary-demo-response.json','edition-check-response.json','hemingway-edition-response.json'):
        for row in json.loads((ROOT/'data/catalog'/filename).read_text(encoding='utf-8'))['response'].values():
            codes=(row.get('classifications') or {}).get('dewey_decimal_class',[])
            section=section_from_codes(codes)
            entries.append({'id':row['key'],'title':row['title'],'authors':[a['name'] for a in row.get('authors',[])],
                'section':section,'ddc_raw':codes,'isbns':row.get('identifiers',{}).get('isbn_13',[]),
                'source_urls':[row['url'].replace('http://','https://')], 'curated':bool(section),
                'label_note':'Cached edition metadata; title matching is work-level and requires edition review'})
    path=ROOT/'data/catalog/index.json'
    path.write_text(json.dumps({'version':1,'entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(len(entries),'local catalog entries;',sum(bool(r['section']) for r in entries),'with source-reported sections')


if __name__=='__main__':run()
