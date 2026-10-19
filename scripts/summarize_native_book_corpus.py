"""Inventory saved acquisition batches without approving labels or changing models."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(corpus):
    corpus = Path(corpus)
    batches = sorted(p for p in corpus.glob('acquisition-v*') if (p / 'collected-books.jsonl').exists())
    records = []
    for batch in batches:
        for line in (batch / 'collected-books.jsonl').read_text().splitlines():
            record = json.loads(line)
            if record['acquisition_status'] == 'downloaded':
                records.append({'batch_root': str(batch), **record})
    (corpus / 'corpus-inventory-v2.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    usable_identity = [r for r in records if 'anthology membership unresolved' not in r['group_resolution_status']]
    incomplete = [dict(work_id=r['work_id'], title=r['title'], missing_parts=r['missing_provider_parts'])
                  for r in records if r.get('missing_provider_parts')]
    summary = dict(generated_at=datetime.now(timezone.utc).isoformat(), downloaded_titles=len(records),
                   by_language=dict(Counter(r['language'] for r in records)),
                   native_text_available_unverified=sum(bool(r['text_available']) for r in records),
                   provisional_group_count=len({r['group_id'] for r in records}),
                   groups_excluding_quarantined_anthology=len({r['group_id'] for r in usable_identity}),
                   verified_training_books=sum(bool(r['training_eligible']) for r in records),
                   model_retrained=False, incomplete_sequences=incomplete,
                   candidate_sections=dict(Counter(r['candidate_ddc_section'] for r in records)),
                   planning_targets={'first_reviewed_pilot': [60, 80], 'focused_mvp': 200})
    write_json(corpus / 'corpus-summary-v2.json', summary)
    table = ['| Language / collection stratum | Downloaded titles | Target distinct reviewed works |',
             '| --- | ---: | ---: |']
    buckets = [
        ('Hindi literature', 'hin', {'891'}, 40), ('Marathi literature', 'mar', {'891'}, 40),
        ('Tamil literature', 'tam', {'894'}, 40), ('Tamil language/grammar', 'tam', {'494'}, 40),
        ('Comparison subjects', None, {'914', '915', '917', '954'}, 40)]
    for title, language, sections, target in buckets:
        count = sum(r['candidate_ddc_section'] in sections and (not language or r['language'] == language) for r in records)
        table.append(f'| {title} | {count} | {target} |')
    lines = ['# Native-book collection status', '', 'Updated 4 October 2026.', '',
             f"Two saved acquisition batches contain **{len(records)} downloaded titles**, with **{summary['native_text_available_unverified']} unverified native text extractions**. There are **{summary['provisional_group_count']} provisional work groups**, or **{summary['groups_excluding_quarantined_anthology']} after excluding the quarantined anthology**. These counts do not certify independent originals or complete books.", '',
             '**Verified training books: 0. The model has not been retrained on these batches.** Labels, text fidelity, source-use status, and overlap with the original catalog/development books still require review.', '',
             *table, '',
             'The counts in this table are collection proposals, not verified DDC assignments. Hindi and Marathi literature share candidate DDC section 891. The Marathi literature total includes an unresolved selected-writings anthology. Several Tamil grammar/prosody texts have competing possible classifications.', '',
             'The focused MVP recommendation is 200 reviewed original-work groups. A 60–80-work reviewed pilot is sufficient to begin a small training experiment, not to claim broad accuracy. See [the dataset targets](../../../docs/MVP_DATASET_TARGETS.md) for sampling, splits, within-language subject balance, and evaluation.', '',
             'The immediate collection gap is comparison subjects in Hindi and more nonfiction across all three languages. Also resolve OCR needs, exact numeric labels and related-work identities before assigning an untouched test split.', '',
             'Saved files include original PDFs/HTML, acquisition receipts and checksums, Unicode text derivatives, indexed Hindi EPUB derivatives, page previews, quality notes, and exclusions. Existing development books are separate and are not included in these new collection counts.', '',
             '- [First batch report](acquisition-v1/README.md)', '- [Second batch report](acquisition-v2/README.md)',
             '- [Combined inventory](corpus-inventory-v2.jsonl)', '- [Combined summary](corpus-summary-v2.json)', '']
    (corpus / 'CORPUS_STATUS.md').write_text('\n'.join(lines), encoding='utf-8')
    latest = batches[-1]
    current = [r for r in records if r['batch_root'] == str(latest)]
    rows = ['| Title | Author | Language | Proposed section | Native text |', '| --- | --- | --- | --- | --- |']
    for r in current:
        text = 'unverified' if r['text_available'] else 'OCR / alternate text needed'
        if r.get('missing_provider_parts'): text += '; incomplete indexed sequence'
        rows.append(f"| {r['title']} | {r['author']} | {r['language']} | {r['candidate_ddc_section']} | {text} |")
    missing_files = [f for r in current for f in r['files'] if not (latest / f['file']).exists()]
    readme = ['# Native-book acquisition, second batch', '', 'Saved 4 October 2026. Separate from the immutable first batch and the eight earlier development books.', '',
              f"**{len(current)} titles downloaded:** " + ', '.join(f'{k}: {v}' for k, v in Counter(r['language'] for r in current).items()) + '.',
              f"**{sum(r['text_available'] for r in current)} titles have candidate native text.** All records retain `human_checked=false`, `verified_section=null`, and `training_eligible=false`.", '',
              '## Book inventory', '', *rows, '', '## Identity and extraction checks', '',
              '- Marathi covers/title pages 1–3 were rendered and inspected by the assistant. Full titles and authors were corrected from the source, including the Detective Alpha book, Hirana, and the four travel books. This is not a claim of human text review or verified numeric DDC labels.',
              '- Tamil PDF pages 1–2 were rendered and visually inspected by the assistant. Catalog titles and genres remain proposals where edition or subject boundaries are uncertain; history, literary rhetoric, and grammar need classification corroboration.',
              '- Hindi legacy HTML uses explicitly selected book-content elements, excluding author biographies and site navigation. Theth Hindi ka That uses the novel link rather than its introduction. Adhkhila Phool excludes the long introduction from its book-body derivative.',
              '- Preserve Kankal empty query responses separately from linked-source recovery attempts. An incomplete sequence cannot produce a complete derived EPUB. Derived EPUBs follow provider web parts, not necessarily the original chapter numbering.',
              '- Iravati returned a navigation-only page and is excluded; Des Birana was collected across six indexed parts instead. Source extent is not a guarantee of complete original-work coverage. Kankal remains incomplete: part 3 returned empty content through both access paths; parts 2 and 4 were recovered from indexed links.',
              '- Project Madurai 839 has a PDF but its indexed Unicode link returned 404. Its legacy-font extraction needs OCR or an alternate matching text. Europe-Kavadse also failed the native-script extraction screen.',
              '- A predominantly native-script extraction can still substitute visually different letters. No extraction is yet a checked transcription. Retain publisher notices and establish training-use status separately.', '',
              '## Reproduce offline preparation and verification', '',
              'Use the bundled document Python runtime with lxml and pypdf:', '',
              '```text', 'python scripts/prepare_native_book_batch_v2.py data/research/multilingual-pilot-v1/acquisition-v2',
              'python scripts/validate_native_book_batch.py data/research/multilingual-pilot-v1/acquisition-v2',
              'python scripts/summarize_native_book_corpus.py data/research/multilingual-pilot-v1', '```', '',
              'Downloads use only the explicit `selected-works.json` list and preserve originals with receipts. Failed source entries: ' + str(len(missing_files)) + '.',
              'Preparation output is not added to training automatically. See the combined status and dataset plan for the next review/training experiment.', '']
    (latest / 'README.md').write_text('\n'.join(readme), encoding='utf-8')
    baseline = json.loads((batches[0] / 'model-unchanged.json').read_text())
    unchanged = digest(Path(baseline['model_file'])) == baseline['sha256']
    if not unchanged: raise ValueError('Model differs from the collection baseline')
    write_json(latest / 'model-unchanged.json', {**baseline, 'matches_previous_head_coverage': unchanged})
    original_manifest = json.loads((batches[0] / 'manifest.json').read_text())
    mismatches = [entry['file'] for entry in original_manifest['files'] if digest(batches[0] / entry['file']) != entry['sha256']]
    if mismatches: raise ValueError('First batch snapshot changed: ' + ', '.join(mismatches))
    write_json(latest / 'previous-batch-validation.json', {'files_checked': len(original_manifest['files']), 'hash_mismatches': mismatches})
    entries = [dict(file=str(p.relative_to(latest)), bytes=p.stat().st_size, sha256=digest(p))
               for p in sorted(latest.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    scripts = ['fetch_native_book_source.py', 'download_native_book_batch.py', 'prepare_native_book_batch_v2.py', 'validate_native_book_batch.py', 'summarize_native_book_corpus.py']
    write_json(latest / 'manifest.json', {'collection': latest.name, 'file_count': len(entries), 'files': entries,
                                        'preparation_scripts': [{'file': 'scripts/' + name, 'sha256': digest(Path('scripts') / name)} for name in scripts]})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus')
    summarize(parser.parse_args().corpus)
