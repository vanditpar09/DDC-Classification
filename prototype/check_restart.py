"""Real HTTP/OCR check across two independent local server processes on port 8013."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager

import httpx

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8013'


@contextmanager
def server(db, log):
    env=dict(os.environ,FIELDNOTE_DB=str(db),FIELDNOTE_ORIGINS=BASE,HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    with open(log,'ab') as output:
        process=subprocess.Popen([sys.executable,'-m','uvicorn','prototype.app:app','--host','127.0.0.1','--port','8013'],cwd=ROOT,env=env,stdout=output,stderr=output)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Test server failed to start; check the test log')
                try:
                    if httpx.get(BASE+'/api/status',timeout=1).status_code==200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('Test server did not become ready')
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()


def main():
    output=ROOT/'output/fieldnote'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        db=Path(directory)/'restart.db'
        with httpx.Client(base_url=BASE,timeout=120) as client:
            with server(db,output/'restart-check.log'):
                sid=client.post('/api/sessions').json()['id']
                response=client.post(f'/api/sessions/{sid}/image',data={'kind':'cover','language':'eng'},
                                     files={'image':('small.png',(ROOT/'prototype/samples/small_text.png').read_bytes(),'image/png')})
                response.raise_for_status();before=response.json()
                assert before['decision']['action']=='reprocess_region'
            with server(db,output/'restart-check.log'):
                recovered=client.get(f'/api/sessions/{sid}').json()
                assert recovered==before
                pid=recovered['pages'][0]['id']
                assert client.get(f'/api/sessions/{sid}/pages/{pid}/image').status_code==200
                headers={'Idempotency-Key':'restart-repair-1','X-Book-Revision':str(recovered['revision'])}
                response=client.post(f'/api/sessions/{sid}/pages/{pid}/repair',json={'language':'eng'},headers=headers)
                response.raise_for_status();after=response.json()
                assert [p['label'] for p in after['prediction']['hierarchy']['path']]==['000','000','005']
                repeated=client.post(f'/api/sessions/{sid}/pages/{pid}/repair',json={'language':'eng'},headers=headers)
                repeated.raise_for_status();assert repeated.json()==after
                report={'passed':True,'separate_server_processes':2,'checks':['saved image and exact state survive restart','real OCR repair after restart returns L1/L2/L3','lost-response repair replay does not repeat work'],
                        'model_version':after['prediction']['model_version'],'work':after['work']}
                (output/'restart-results.json').write_text(json.dumps(report,indent=2)+'\n')
                print('PASS: real HTTP restart, restored image, three-level inference and repair replay')


if __name__=='__main__':
    main()
