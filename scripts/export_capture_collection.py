"""Rebuild readable tables/photos from an existing capture database, without OCR."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True)
    args=parser.parse_args()
    if not args.db.is_file():parser.error('The saved database does not exist')
    from prototype.storage import SQLiteStore
    store=SQLiteStore(args.db)
    if store.export_error:raise SystemExit('Records remain saved in SQLite; export failed: '+store.export_error)
    print(f'Exported {len(store.list())} books to {store.export_root}')


if __name__=='__main__':run()
