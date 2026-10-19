"""Inventory local source PDFs against the saved native_silver_v2 fitting record.

Reads provenance and partition metadata, never held-out passage contents. Original
books remain local; only paths, hashes and source-use metadata are exported.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'data/research/multilingual-pilot-v1'
REPORT = PILOT / 'training-source-inventory-v1'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def main():
    dataset = PILOT / 'silver-pilot-v2/books.jsonl'
    books = [json.loads(line) for line in dataset.read_text().splitlines()]
    model = ROOT / 'models/native_silver_v2/classifier.joblib'
    metadata = json.loads((model.parent / 'metadata.json').read_text())
    assert sha(dataset) == metadata['protocol']['dataset_sha256']
    assert sha(model) == metadata['model_sha256']
    fitting = json.loads((PILOT / 'experiment-v2/native-training-windows.json').read_text())
    assert {b['work_id'] for b in books if b['assigned_partition'] == 'train'} == {b['work_id'] for b in fitting}
    use = defaultdict(list)
    for book in books:
        for sample in book['samples']:
            source = sample['provenance'].get('source_pdf')
            if not source:
                continue
            path = relative(ROOT / source)
            assert (ROOT / path).is_file(), path
            use[path].append(dict(work_id=book['work_id'], title=book['title'],
                                  language=book['language'], partition=book['assigned_partition'],
                                  page=sample['provenance'].get('page'),
                                  passage=sample['text_file'], method=sample['provenance']['method']))
    inventory = []
    for path in sorted(PILOT.rglob('*.pdf')):
        name = relative(path)
        uses = use.get(name, [])
        partitions = sorted({u['partition'] for u in uses})
        assert not ('train' in partitions and len(partitions) > 1), name
        receipt_path = path.with_name(path.name + '.receipt.json')
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        digest = sha(path)
        if receipt.get('sha256'):
            assert digest == receipt['sha256'], name
        inventory.append(dict(path=name, bytes=path.stat().st_size, sha256=digest,
                              used_for_current_model_fitting='train' in partitions,
                              partitions=partitions, passage_uses=uses,
                              source_url=receipt.get('source_url'),
                              role=('passage_source' if uses else
                                    'reference_only' if '/sources/' in name else
                                    'collected_not_used_as_pdf_passage_source')))
    assert set(use) <= {p['path'] for p in inventory}
    training = [p for p in inventory if p['used_for_current_model_fitting']]
    pdf_work_ids = {u['work_id'] for p in training for u in p['passage_uses'] if u['partition'] == 'train'}
    train_books = [b for b in books if b['assigned_partition'] == 'train']
    summary = dict(total_local_source_pdfs=len(inventory), fitting_source_pdfs=len(training),
                   fitting_pdf_editions=len(pdf_work_ids), native_fitting_editions=len(train_books),
                   native_fitting_work_groups=len({b['group_id'] for b in train_books}),
                   native_fitting_passages=sum(len(b['samples']) for b in train_books),
                   fitting_editions_using_publisher_text_without_pdf_provenance=len(train_books)-len(pdf_work_ids),
                   development_source_pdfs=sum('development' in p['partitions'] for p in inventory),
                   locked_test_source_pdfs=sum('test' in p['partitions'] for p in inventory),
                   other_source_pdfs=sum(not p['partitions'] for p in inventory),
                   fitting_pdf_bytes=sum(p['bytes'] for p in training),
                   original_catalog_fitting_records=metadata['protocol']['original_catalog_train'])
    report = dict(model='native_silver_v2', model_sha256=sha(model), dataset=relative(dataset),
                  dataset_sha256=sha(dataset), scope='Original source PDFs in multilingual-pilot-v1; generated output/report/package PDFs excluded.',
                  interpretation='Fitting used prepared text/OCR passages, not entire PDFs. Native labels are silver, not independently verified gold.',
                  locked_test_passage_contents_read=False, original_pdfs_committed=False,
                  summary=summary, pdfs=inventory)
    REPORT.mkdir(exist_ok=True)
    (REPORT / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    lines = ['# PDFs used for the current model', '',
             f"The saved `native_silver_v2` fitting record traces to **{len(training)} PDF files across {len(pdf_work_ids)} native-language editions**. "
             'These are the sources of selected OCR passages, not whole-book training inputs.', '',
             f"The full fitting run used {summary['original_catalog_fitting_records']:,} catalog metadata records plus "
             f"{len(train_books)} native editions ({summary['native_fitting_work_groups']} work groups, {summary['native_fitting_passages']} passages). "
             f"The other {len(train_books)-len(pdf_work_ids)} native editions used publisher text with no PDF passage provenance.", '',
             '## Find the files', '',
             'Paths below are relative to the repository root. These links work in the local checkout; original PDFs are ignored by Git and absent from a fresh clone. '
             'The JSON inventory includes all source PDFs, hashes, page numbers, passage paths, source URLs where receipts exist, and saved partition membership.', '',
             '[Full inventory](inventory.json). Regenerate locally with `python3 scripts/inventory_training_pdfs.py`.', '',
             'Most files are under `../acquisition-v1/books/` through `../acquisition-v4/books/`. NCERT often supplies separate chapter PDFs. '
             'File counts therefore do not equal book counts.', '',
             '## Fitting PDF sources', '', '| Book | Language | Source PDF | Sampled PDF pages |',
             '|---|---|---|---|']
    for p in training:
        uses = [u for u in p['passage_uses'] if u['partition'] == 'train']
        titles = ' / '.join(sorted({u['title'] for u in uses})).replace('|', '\\|')
        languages = ', '.join(sorted({u['language'] for u in uses}))
        pages = ', '.join(str(v) for v in sorted({u['page'] for u in uses if u['page'] is not None}))
        local = Path(p['path']).relative_to(PILOT.relative_to(ROOT)).as_posix()
        lines.append(f"| {titles} | {languages} | [{local}](../{local}) | {pages} |")
    lines += ['', '## What the remaining PDFs mean', '',
              f"Of {len(inventory)} local source PDFs, {summary['development_source_pdfs']} supplied development passages and "
              f"{summary['locked_test_source_pdfs']} are linked to the locked test partition; neither entered fitting. "
              f"The other {summary['other_source_pdfs']} are collected companion chapters/editions, inbox books or reference documents without PDF passage use in this run.", '',
              'A downloaded PDF of a book whose publisher HTML was used is still not counted as a PDF fitting source. '
              'Original inbox PDFs are not automatically training data. No locked-test passage text was opened for this inventory.', '',
              'The saved labels are provisional assistant labels. These counts do not establish model accuracy or redistribution rights. '
              'Source PDFs remain on the collection laptop. The repository retains the prepared passages, source receipts, partition assignments, trained classifier and this inventory.', '']
    (REPORT / 'README.md').write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
