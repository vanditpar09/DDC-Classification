"""Collect bounded, explicitly partial nonfiction samples from NCERT's index.

Translations share a work group. Subject labels are assistant proposals, not
catalog-verified labels. No whole-book completeness or redistribution licence
is inferred. This script downloads data and never executes downloaded content.
"""
import json
from pathlib import Path
import re
import argparse
from concurrent.futures import ThreadPoolExecutor
from fetch_native_book_source import fetch

ROOT = Path('data/research/multilingual-pilot-v1/acquisition-v3')


def run(root=ROOT, extra_math=False):
    global ROOT
    ROOT=Path(root)
    ROOT.mkdir(parents=True,exist_ok=True)
    index = Path('data/research/multilingual-pilot-v1/acquisition-v3/catalogs/ncert-textbooks.html')
    source = re.sub(r'/\*.*?\*/', '', index.read_text(), flags=re.S)
    options = {code: (title.strip(), int(n)) for title, code, n in re.findall(
        r'tbook.options\[\d+\].text\s*=\s*"([^"]+)";\s*document.test.tbook.options\[\d+\].value\s*=\s*"textbook.php\?([^"=]+)=0-(\d+)"', source)}
    choices = []
    for grade, prefix in ((6, 'f'), (7, 'g'), (8, 'h')):
        for subject, section in (('gp', '510'), ('cu', '500')):
            for language, marker in (('hin', 'h'), ('mar', 'mr'), ('tam', 'tm')):
                choices.append((prefix + marker + subject + '1', language, section,
                                f'ncert-class-{grade}-{subject}',
                                'Mathematics' if subject == 'gp' else 'General science'))
    for code, section, subject in (
        ('khph1', '530', 'Physics'), ('khch1', '540', 'Chemistry'),
        ('khbo1', '570', 'Biology'), ('khpy1', '150', 'Psychology'),
        ('khsy1', '301', 'Sociology'), ('khps1', '320', 'Political theory'),
        ('khec1', '330', 'Economics'), ('khac1', '657', 'Accounting'),
        ('khfa1', '709', 'Indian art history'), ('khgy2', '910', 'Physical geography')):
        # Physical geography crosses 550/910; collect evidence, hold the label.
        choices.append((code, 'hin', section, 'ncert-class-11-' + subject.lower().replace(' ', '-'), subject))
    if extra_math:
        choices=[('ihmh1','hin','510','ncert-class-9-mathematics','Mathematics'),
                 ('jhmh1','hin','510','ncert-class-10-mathematics','Mathematics')]
    works, jobs = [], []
    for code, language, section, group, subject in choices:
        title, chapters = options[code]  # All codes must actually occur in the saved publisher index.
        pages = sorted({1, max(1, chapters // 2), chapters})
        files = [dict(file=f'books/{code}/{code}{part:02d}.pdf',
                      source_url=f'https://ncert.nic.in/textbook/pdf/{code}{part:02d}.pdf',
                      chapter=part) for part in pages]
        files.append(dict(file=f'books/{code}/{code}ps.pdf',
                          source_url=f'https://ncert.nic.in/textbook/pdf/{code}ps.pdf', chapter=0))
        work = dict(work_id='ncert-' + code, group_id=group, title=title,
                    author='NCERT', language=language, candidate_ddc_section=section,
                    subject=subject, catalog_url='https://ncert.nic.in/textbook.php', files=files,
                    label_basis='Assistant broad subject mapping from publisher index and sampled chapter content; not numeric catalog evidence',
                    label_hold=code == 'khgy2', verified_section=None, human_checked=False,
                    training_eligible=False, coverage_status='Three selected chapters plus front matter; NOT a complete book',
                    training_rights_status='Not established by public access; original notices retained',
                    group_resolution_status='Publisher translations grouped by grade and subject; Part I shares the original textbook family')
        works.append(work)
        jobs.extend(files)
    (ROOT / 'selected-works.json').write_text(json.dumps(works, ensure_ascii=False, indent=2) + '\n')
    def download(entry):
        try:
            return dict(file=entry['file'], status='downloaded', receipt=fetch(entry['source_url'], ROOT / entry['file']))
        except Exception as exc:
            return dict(file=entry['file'], status='failed', error=str(exc))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(download, jobs))
    (ROOT / 'download-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(candidate_editions=len(works), source_files=len(jobs), failed=sum(r['status']=='failed' for r in results))))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--extra-math',action='store_true')
    a=p.parse_args();run(a.root,a.extra_math)
