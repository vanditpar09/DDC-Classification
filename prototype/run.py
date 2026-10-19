"""Single-process local launcher with explicit origins for optional LAN HTTPS."""
import argparse
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8011)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--origin',action='append',default=[],help='Exact phone-facing origin, e.g. https://192.168.1.20:8011')
    parser.add_argument('--cert',type=Path)
    parser.add_argument('--key',type=Path)
    parser.add_argument('--model', choices=('hierarchy_v1', 'native_silver_v1', 'native_silver_v2'), default='hierarchy_v1',
                        help='Use the existing model or the separately trained native silver experiment')
    args=parser.parse_args()
    if bool(args.cert)!=bool(args.key):
        parser.error('Use both --cert and --key for HTTPS')
    if args.host not in ('127.0.0.1','localhost') and not args.origin:
        parser.error('LAN listening requires an explicit --origin. This prototype has no user authentication.')
    scheme='https' if args.cert else 'http'
    origins=[f'{scheme}://127.0.0.1:{args.port}',f'{scheme}://localhost:{args.port}',*args.origin]
    os.environ['FIELDNOTE_ORIGINS']=','.join(origins)
    os.environ['FIELDNOTE_MODEL']=args.model
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    import uvicorn
    uvicorn.run('prototype.app:app',host=args.host,port=args.port,workers=1,
                ssl_certfile=str(args.cert) if args.cert else None,
                ssl_keyfile=str(args.key) if args.key else None)


if __name__=='__main__':
    main()
