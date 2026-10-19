"""Save public-catalog search candidates; no automatic label verification."""
import sys,json,time
from pathlib import Path
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'scripts');from fetch_native_book_source import fetch
root=Path('data/research/multilingual-pilot-v1');dest=root/'review-v3';aliases={'hindisamay-work-226':('Gaban','Premchand'),'hindisamay-work-233':('Pratigya','Premchand'),'hindisamay-work-259':('Nirmala','Premchand'),'hindisamay-work-238':('Prema','Premchand'),'hindisamay-v2-1':('Devrani jethani ki kahani','Gauri Datt'),'hindisamay-v2-2':('Suraj ka satvan ghora','Bharati'),'hindisamay-v2-3':('Daud','Mamta Kalia'),'hindisamay-v2-4':('Pariksha guru','Shrinivas Das'),'hindisamay-v2-5':('Shahar mein curfew','Vibhuti Narayan Rai'),'hindisamay-v2-6':('Adhkhila phool','Hariaudh'),'hindisamay-v2-7':('Theth Hindi ka that','Hariaudh'),'hindisamay-v2-1232':('Kankal','Prasad'),'hindisamay-v2-11865':('Titli','Prasad'),'hindisamay-des-birana':('Des birana','Suraj Prakash'),'pm-work-147':('Nannul',''),'pm-work-101':('Neminatam',''),'pm-work-257':('Ilakkanac curukkam',''),'pm-work-258':('Tonnul vilakkam',''),'pm-work-217':('Pratapa Mutaliyar carittiram',''),'pm-work-376':('Tiyaka pumi','Kalki'),'pm-work-228':('Colaimalai ilavaraci','Kalki'),'pm-work-145':('Tantiyalankaram',''),'pm-work-55':('Yapparunkalak karikai','')}
rows=[json.loads(l) for l in (root/'corpus-inventory-v2.jsonl').read_text().splitlines()];jobs=[]
for row in rows:
 wid=row['work_id'];title,author=aliases.get(wid,(row['title'],row['author']));params=dict(title=title,limit=5,fields='key,title,author_name,language,ddc,edition_key');params.update({'author':author} if author else {});url='https://openlibrary.org/search.json?'+urlencode(params);jobs.append(dict(work_id=wid,title_query=title,author_query=author,url=url,file=str(dest/'sources'/(wid+'-catalog.json'))))
(dest/'catalog-query-plan.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n')
def run(job):
 try:
  fetch(job['url'],Path(job['file']),limit=5_000_000);d=json.loads(Path(job['file']).read_text());return {**job,'status':'retrieved','num_found':d.get('numFound'), 'records':d.get('docs',[]),'match_status':'search candidates only; exact author/title/edition requires review'}
 except Exception as e:return {**job,'status':'failed','error':str(e)}
 finally:time.sleep(.7)
with ThreadPoolExecutor(max_workers=2) as pool:
 results=[]
 for r in pool.map(run,jobs):
  results.append(r);print(r['work_id'],r['status'],r.get('num_found'),flush=True)
(dest/'catalog-search-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
