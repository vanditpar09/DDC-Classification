"""Save the pilot findings, source hashes and honest validation limitations."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/'data/research/multilingual-pilot-v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report=CORPUS/'experiment-v2'
    metrics=json.loads((report/'metrics.json').read_text());dataset=json.loads((CORPUS/'silver-pilot-v2/summary.json').read_text())
    tests=(CORPUS/'regression-v2.log').read_text()
    assert '191 passed' in tests and 'FAILED ' not in tests
    assert sha(ROOT/'models/hierarchy_v1/classifier.joblib')==metrics['protocol']['baseline_sha256']
    assert sha(ROOT/'models/native_silver_v2/classifier.joblib')==metrics['model_sha256']
    assert json.loads((report/'local-server-smoke.json').read_text())['passed']
    browser=json.loads((report/'browser-check.json').read_text())
    assert browser['page_loaded'] and browser['visible_three_levels'] and browser['experimental_note_visible']
    assert browser['console_errors']==[] and browser['model']=='native_silver_v2'
    assert browser['suggested_path']==['800','890','891']
    screenshot=report/browser['screenshot']
    assert screenshot.is_file()
    table=['| Model | L1 class | L2 division | L3 section |','| --- | ---: | ---: | ---: |']
    for name,data in metrics['development'].items():
        table.append('| '+name+' | '+' | '.join(f"{data['overall']['levels'][str(k)]['accuracy']:.1%}" for k in (1,2,3))+' |')
    language=['| Language | Edition samples | Work groups in that language |','| --- | ---: | ---: |']
    for lang,v in metrics['development']['silver_candidate']['by_language'].items():
        language.append(f"| {lang} | {v['books']} | {v['work_groups']} |")
    support=metrics['new_section_support']
    readme=f'''# Multilingual DDC pilot: trained model and local tests

4 October 2026. **The native-language experimental model has now been trained.**
It produces parent-consistent L1/L2/L3 suggestions, including 891 (Hindi/Marathi
literature), 894 (Tamil literature), 494 (Tamil language), and 510 (general
mathematics). The frozen multilingual E5 encoder was not fine-tuned.

This is a silver-label research pilot. Labels were reviewed/proposed by the
assistant from saved source content and catalog evidence; none is represented
as a librarian-certified or human-verified benchmark label. Source OCR is machine
output, not a checked transcription. No patentability finding is made.

## What was completed

- Preserved the original acquisitions and review. Recovered 63 aligned source
  pages at 240 dpi from 21 noisy-text books; 60 passed diagnostic screening.
  Unusable artistic text and the unresolved anthology remain excluded.
- Added NCERT nonfiction comparisons in Hindi, Marathi and Tamil from its
  [publisher index](https://ncert.nic.in/textbook.php). These are selected chapters
  and front matter, not newly acquired complete books. Two missing source files
  exclude those editions; physical geography remains held for label adjudication.
- Prepared **{dataset['edition_samples']} edition samples, {dataset['provisional_work_groups']}
  provisional work groups and {dataset['passages']} passages**. The language counts
  are Hindi 30, Marathi 23 and Tamil 24. All translations of a textbook share a
  group. Prema/Pratigya retain their shared conservative group.
- Fitted new broad and conditional division/section heads on 3,061 original
  catalog training records plus 53 native silver editions in 49 work groups.
  The five-work support rule was retained. Total training support is 891:
  {support['891']}, 894: {support['894']}, 494: {support['494']}, and 510: 5 groups;
  these totals can include original weak catalog records.
- Saved the original experiment (v1) and a second run (v2). The follow-up added
  two mathematics works and moved three Marathi works out of fitting to correct
  deficient development coverage. Every earlier development/test group stayed
  out of training. Four native test groups remain locked and unevaluated.
- Loaded the saved artifact in a separate process, checked finite parameters,
  ran **191 passing regression tests**, and exercised actual local image OCR/API
  calls in all three native languages. These use rendered PDFs, not phone photos.

## Development results and their limits

The development comparison uses **17 edition samples in 13 provisional work
groups**, with equal total weight per work group. The baseline and candidate
receive the same body passages and page-balanced window method. This is continued
development: v1 findings informed the data follow-up. It is not a fresh final test.

{chr(10).join(table)}

**The 100% pilot result is not a claim of general DDC accuracy.** This is a very
small, subject-limited set with silver labels, shared publishers/authors and
unresolved original-work overlap. It covers only five target sections, not the
whole DDC taxonomy. Sparse classes have no independent native development samples.

{chr(10).join(language)}

The per-language group counts overlap because translated textbooks are the same
original work. A previously exposed 200-record catalog development check gave
L1 accuracy 65.5% for the baseline and 68.5% for the candidate. It is a regression
check, not independent validation. The macOS numerical library emitted matrix
warnings during fitting; saved coefficients and observed probability outputs
were finite. The locked native test set has not been opened for model evaluation.

## Local use

The experiment is running at [localhost:8013](http://127.0.0.1:8013/).
Its captures are saved in a separate local database. Restart from the repository:

```sh
FIELDNOTE_DB=output/fieldnote/native-silver-v2.sqlite3 .venv/bin/python -m prototype.run --port 8013 --model native_silver_v2
```

The original default model remains `hierarchy_v1`. The explicit experiment flag
prevents an absent candidate from silently falling back. Scores are uncalibrated;
the candidate cannot automatically approve any book. The website distinguishes
experimental scores from failure to pass a confidence threshold.

Real OCR/API checks suggested Hindi mathematics `500 -> 510 -> 510`, Marathi
fiction `800 -> 890 -> 891`, and a Tamil lexicon `400 -> 490 -> 494`. The Tamil
page exceeded the prototype's 512-token single-input limit; that truncation was
reported. The body-text development comparison uses bounded multi-window pooling.

## Saved files and reproduction

- `silver-pilot-v2/books.jsonl`: experimental labels, source evidence, samples,
  partition membership and explicit non-gold status.
- `metrics.json`, `development-predictions.jsonl`, `protocol.json`, and
  `split-assignments.json`: full results and fitting/holdout membership.
- `local-server-smoke.json` and `*-local-trace.json`: actual local OCR/API traces.
- `browser-check.json` and `local-website.png`: saved website verification of
  three-level Hindi suggestions and the experimental-score notice. This is a
  functional check on authored sample text, not an accuracy or phone benchmark.
- `models/native_silver_v2/classifier.joblib` and `metadata.json`: the small
  trained artifact is included by Git ignore exceptions. The 470 MB encoder and
  embedding caches stay local; restore the documented encoder on other machines.
- `acquisition-v3/v4`, `text-repair-v1`: original selected sources, receipts,
  rendered pages and machine OCR. The complete research folder is about 1.1 GB.
  Source use/redistribution status is not established merely by public access;
  original notices and that unresolved status are retained per book.

Reproduce the fitting run in NEW directories (existing experiment directories
are protected):

```sh
HF_HUB_OFFLINE=1 .venv/bin/python -m src.research.train_silver \\
  --dataset data/research/multilingual-pilot-v1/silver-pilot-v2 \\
  --output-dir models/native_reproduction \\
  --report-dir data/research/multilingual-pilot-v1/experiment-reproduction
```

## What still needs work

1. Resolve ambiguous labels using closer edition evidence; add separate native
   comparison works for the sparse subjects. Existing assistant labels must not
   become verified labels merely because this model predicts them correctly.
2. Obtain checked reference passages for an independent OCR/camera benchmark.
   Then run actual phone captures across lighting, blur and page layouts.
3. Calibrate scores on additional untouched works, freeze the capture controller,
   and compare repair/new-page decisions at matched classification quality.
4. Expand toward the focused ~200-work target using the observed class/language
   gaps. Do not add crops of the same textbook as independent training books.

The immediate model/data improvement cycle is complete. Broad multilingual
validation, phone measurement and the full larger dataset remain future stages.
'''
    (report/'README.md').write_text(readme)
    validation=dict(generated_at=datetime.now(timezone.utc).isoformat(),regression_tests_passed=191,
                    candidate_deserialization_checked=True,finite_parameters_checked=True,
                    real_local_ocr_languages=['hin','mar','tam'],browser_verified=True,
                    browser_screenshot_sha256=sha(screenshot),
                    physical_phone_test=False,locked_test_evaluated=False,baseline_unchanged=True,
                    candidate_sha256=metrics['model_sha256'],baseline_sha256=metrics['protocol']['baseline_sha256'])
    (report/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    scripts=['scripts/collect_ncert_comparisons.py','scripts/repair_native_book_samples.py','scripts/prepare_silver_pilot.py',
             'scripts/smoke_native_server.py','scripts/check_native_browser.cjs','scripts/finalize_silver_experiment.py','src/research/train_silver.py']
    (report/'code-hashes.json').write_text(json.dumps({s:sha(ROOT/s) for s in scripts},indent=2)+'\n')
    for name in ('acquisition-v3','acquisition-v4','text-repair-v1','silver-pilot-v2','experiment-v2'):
        folder=CORPUS/name
        files={str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
        (folder/'manifest.json').write_text(json.dumps(files,indent=2)+'\n')
    print(json.dumps(validation))


if __name__=='__main__':run()
