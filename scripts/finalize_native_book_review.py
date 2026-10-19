"""Record review decisions and evidence without promoting uncertain labels to truth."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

CORPUS=Path('data/research/multilingual-pilot-v1')
REVIEW=CORPUS/'review-v3'
OCLC='https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf'
IITGN='https://library.iitgn.ac.in/documents/library_files/Hindi-Books.pdf'

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text).casefold() if c.isalnum())

def run():
    reviews=[json.loads(l) for l in (REVIEW/'source-reviews.jsonl').read_text().splitlines()]
    inventory={r['work_id']:r for r in [json.loads(l) for l in (CORPUS/'corpus-inventory-v2.jsonl').read_text().splitlines()]}
    searches=json.loads((REVIEW/'catalog-search-results.json').read_text())+json.loads((REVIEW/'catalog-recovery-results.json').read_text())
    candidates=defaultdict(list)
    for row in searches:
        candidates[row['work_id']].extend(row.get('records',[]))
    old=[json.loads(l) for l in Path('data/books.jsonl').read_text().splitlines()]
    index=defaultdict(set)
    for row in old:
        for value in [row['document_id'],*row.get('source_work_ids',[]),*row.get('edition_ids',[]),*row.get('isbns',[])]:index[value].add(row['document_id'])
    numeric={
        'hindisamay-work-226':(67,'949','019512','891.4335'),
        'hindisamay-work-233':(69,'976','032638','891.433'),
        'hindisamay-work-238':(69,'977','032639','891.433'),
        'hindisamay-work-259':(67,'958','019545','891.4335'),
        'hindisamay-v2-2':(11,'139','019563','891.4337'),
        'hindisamay-v2-11865':(66,'931','036648','891.433'),
        'hindisamay-v2-1232':(66,'933','036650','891.433')}
    subject_uncertain={'pm-work-55','pm-work-145','pm-work-263','pm-work-410','pm-work-695'}
    decisions=[];sample_candidates=[]
    for review in reviews:
        wid=review['work_id'];book=inventory[wid]
        checks=review['source_page_checks']
        review['source_page_checks']=sorted(checks,key=lambda c:(c['source_pdf'],c['page']))
        review['catalog_search_status']='candidate records found' if candidates[wid] else 'no matched numeric evidence from this search'
        review['catalog_candidates']=candidates[wid]
        review['catalog_overlap_status']='no exact identifier hit in saved original catalog; transliteration and unlinked editions still unresolved'
        hits=[]
        for candidate in candidates[wid]:
            identifiers=[candidate.get('key','').rsplit('/',1)[-1],*candidate.get('edition_key',[])]
            known=set().union(*(index[i] for i in identifiers))
            if known:hits.append({'candidate_catalog_key':candidate.get('key'),'original_catalog_documents':sorted(known),'match_status':'candidate overlap; identity must be resolved'})
        if hits:review['catalog_overlap_status']='possible prior-catalog overlap; exclude from independent test pending identity review'
        review['prior_catalog_candidate_hits']=hits
        review['label_evidence']=[dict(url=OCLC,scope='DDC 23 three-digit vocabulary only; does not classify this specific edition')]
        review['assistant_reviewed_section']=None
        if wid in numeric:
            page,row,accession,number=numeric[wid]
            evidence=dict(url=IITGN,source_pdf='data/research/multilingual-pilot-v1/intake-v1/label-review-v2/sources/iitgn-hindi-catalog.pdf',
                          evidence_image=f'evidence-pages/iitgn-page-{page}.png',page=page,row=row,accession=accession,ddc=number,
                          matched_fields=['original title','original author','Hindi edition'],scope='same original work, different print edition; exact digital edition not verified')
            review['numeric_catalog_evidence'].append(evidence);review['label_evidence'].append(evidence)
            review['assistant_reviewed_section']=number[:3]
            review['label_status']='work-level numeric section corroborated; exact edition unresolved'
        elif wid in {'pm-work-295','pm-work-301'}:
            # Different editors/editions cannot silently settle this original's number.
            alternatives=[dict(key=c['key'],title=c['title'],authors=c.get('author_name',[]),ddc=c.get('ddc',[]),scope='related edited edition, not the acquired digital file') for c in candidates[wid] if c.get('ddc')]
            review['numeric_catalog_evidence']=alternatives
            for evidence in alternatives:
                evidence['edition_sources']=[str(p.relative_to(REVIEW)) for p in sorted((REVIEW/'sources').glob(wid+'-edition-*.json'))]
                evidence['provenance']='Open Library edition cites Harvard bibliographic MARC; acquired edition may differ'
            review['label_status']='conflicting section evidence: proposed 494 versus catalog 894'
            review['label_evidence'].append(dict(source='saved Open Library work and edition records',scope='related-work/edition numeric conflict; not an exact digital-edition match',records=alternatives))
        elif wid in subject_uncertain:
            review['label_status']='grammar/prosody/rhetoric boundary requires adjudication'
        elif wid=='pm-work-147':
            review['label_status']='494 supported by related grammar/commentary catalog; original digital edition unresolved'
            review['assistant_reviewed_section']='494'
            review['label_evidence'].append(dict(url='https://library.cutn.ac.in/cgi-bin/koha/opac-detail.pl?biblionumber=27095',
                local_source='sources/cutn-nannul.html',ddc='494.811',scope='Nannul Uraivalam commentary collection, not the same edition; corroborative subject evidence only'))
        elif wid=='esahity-phakiraa':
            review['label_status']='quarantined anthology identity; no independent-work or single-label approval'
        else:
            review['assistant_reviewed_section']=review['proposed_section']
            review['label_status']='assistant subject-to-section proposal; no matched numeric catalog record'
        # A rule-based proposal is distinct from a catalog-verified benchmark label.
        review['verified_section']=None;review['training_eligible']=False;review['human_checked']=False
        review['identity_status']='source identity checked in acquisition review; catalog/edition resolution pending'
        review['group_resolution_status']=book['group_resolution_status']
        review['review_decision']='hold for label/text/identity resolution'
        if review['label_status'].startswith('work-level numeric') and review['text_status'].startswith('candidate native') and not review['missing_provider_parts']:
            review['review_decision']='priority for experimental text preparation; do not treat as gold benchmark'
        if wid in {'hindisamay-work-233','hindisamay-work-238'}:
            review['group_notes']='Keep Prema and Pratigya in the existing shared conservative rewrite-family group until relationship is conclusively resolved.'
        if wid=='pm-work-718':review['completeness_notes']='The acquired text starts at chapter 17; do not count it as complete original-work coverage.'
        if wid=='pm-work-410':review['completeness_notes']='Publisher warns of unreadable passages in the underlying scan; close OCR/HTML agreement cannot detect shared omissions.'
        if wid=='esahity-saichi_vahi':review['source_notes'].append('Stylized italic Marathi text over lined/background images; sampled OCR is poor and is not an adequate training reference.')
        decisions.append(review)
        if review['review_decision'].startswith('priority for experimental'):
            for window in review['raw_text_sample_candidates']:
                sample_candidates.append(dict(work_id=wid,group_id=review['group_id'],language=review['language'],
                    text_file=window['file'],text_sha256=window['sha256'],proposed_section=review['assistant_reviewed_section'],
                    label_scope='work-level numeric corroboration',reference_status='publisher HTML; assistant review, not checked human transcription',
                    training_eligible=False,evaluation_eligible=False,partition=None))
    (REVIEW/'reviewed-books.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in decisions),encoding='utf-8')
    (REVIEW/'priority-sample-candidates.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in sample_candidates),encoding='utf-8')
    summary=dict(reviewed_at=datetime.now(timezone.utc).isoformat(),titles_assessed=len(decisions),
        text_statuses=dict(Counter(r['text_status'] for r in decisions)),label_statuses=dict(Counter(r['label_status'] for r in decisions)),
        primary_work_level_numeric_correspondences=len(numeric),conflicting_labels=['pm-work-295','pm-work-301'],
        source_pages_checked=sum(len(r['source_page_checks']) for r in decisions),sample_windows_saved=sum(len(r['raw_text_sample_candidates']) for r in decisions),
        priority_experimental_titles=len({r['work_id'] for r in sample_candidates}),verified_training_books=0,model_retrained=False,
        by_language=dict(Counter(r['language'] for r in decisions)),
        note='Completed assistant evidence/quality review pass. Source agreement is heuristic and exact edition labels remain unresolved. No final test split or model fitting performed.')
    write_json(REVIEW/'review-summary.json',summary)
    # Near-duplicate screen applies to saved samples, not all originals.
    fingerprints={}
    for r in decisions:
        joined=' '.join((REVIEW/w['file']).read_text(encoding='utf-8') for w in r['raw_text_sample_candidates'])
        n=norm(joined);fingerprints[r['work_id']]={n[i:i+16] for i in range(0,max(0,len(n)-15),16)}
    pairs=[]
    for i,a in enumerate(decisions):
        for b in decisions[i+1:]:
            if a['language']!=b['language']:continue
            x,y=fingerprints[a['work_id']],fingerprints[b['work_id']];score=len(x&y)/max(1,min(len(x),len(y)))
            if score>=.1:pairs.append(dict(works=[a['work_id'],b['work_id']],sample_shingle_overlap=round(score,4),identity_confirmed=False))
    write_json(REVIEW/'overlap-review.json',dict(old_catalog_records=len(old),identifier_candidate_hits=[dict(work_id=r['work_id'],hits=r['prior_catalog_candidate_hits']) for r in decisions if r['prior_catalog_candidate_hits']],
        near_duplicate_sample_flags=pairs,conservative_shared_groups={'premchand-prema-pratigya':[r['work_id'] for r in decisions if r['work_id'] in {'hindisamay-work-233','hindisamay-work-238'}]},
        unresolved_anthology='esahity-phakiraa',complete_work_independence_certified=False,
        note='Exact identifier and sampled-text checks do not rule out unlinked translations, rewrites, or different catalog spellings. Existing eight development books remain separate.'))
    table=['| Book | Language | Label review | Text review |','| --- | --- | --- | --- |']
    table.extend(f"| {r['title']} | {r['language']} | {r['label_status']} | {r['text_status']} |" for r in decisions)
    lines=['# Book review, third pass','','4 October 2026. Assistant review; no human/librarian review is claimed.','',
        f"Assessed all **{len(decisions)} downloaded titles**. Saved **{summary['source_pages_checked']} rendered PDF page/OCR comparisons** and **{summary['sample_windows_saved']} text windows**. Sources and acquired-book snapshots remain unchanged.",'',
        f"**{len(numeric)} Hindi works have supporting numeric DDC evidence in IIT Gandhinagar’s catalog.** These are matching original titles/authors in other print editions, not exact matches to the digital file. Nannul has additional 494 evidence from a related commentary catalog. Two Tamil texts have 494/894 conflicts.",'',
        '**The collection is not complete and is not a verified training/test dataset.** The next milestone is 60–80 distinct reviewed works for a small pilot. Around 200 is a planning target for the selected subjects, not a proven minimum. More Hindi nonfiction and broader comparison subjects are still needed.','',
        '## What the checks found','',
        '- The earlier 57 “text available” count only meant plausible native-script extraction. It does not mean 57 reliable transcripts. Marathi font decoding often changes actual letters even though the output remains in Devanagari.',
        '- Source concordance compares native-script 12-character shingles between independent OCR of three PDF pages and the existing text. The 0.8 screen threshold is a conservative heuristic. It is not CER, confidence, or proof of a correct transcription; low agreement can reflect OCR errors, sparse/illustrated pages, or an edition mismatch as well as extraction errors.',
        '- Hindi book-body extraction uses publisher content elements. Thirteen complete indexed sequences are available across both batches; Kankal is missing part 3. HTML sampling has no independent page-image transcription comparison.',
        '- Nannul and Velir Varalaru need fidelity investigation after lower agreement on sampled pages. Stylized Saichi Vahi OCR is particularly poor. Sources with unreadable passages or partial chapters remain qualified even when OCR agrees.',
        '- Akapporul Vilakkam and Iraiyanar Akapporul have related catalog records with DDC 894, conflicting with their provisional 494 collection labels. Other prosody/rhetoric works also need subject adjudication; no numbers were silently replaced.',
        '- Prema/Pratigya retain their shared conservative group. The selected-writings anthology is quarantined. Shared series/authors remain potential confounders; an exact-identifier check cannot certify independence.',
        '- A librarian is helpful, not required to collect evidence. Record who actually reviewed each source. Assistant proposals, machine OCR, and confirmed benchmark labels are different states.', '',
        '## Evidence and outputs','',
        '- [IIT Gandhinagar Hindi catalog](https://library.iitgn.ac.in/documents/library_files/Hindi-Books.pdf): rendered evidence pages 11, 66, 67 and 69 saved locally.',
        '- [OCLC DDC 23 summary](https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf): vocabulary evidence only; does not classify individual books.',
        '- [CUTN Nannul commentary catalog](https://library.cutn.ac.in/cgi-bin/koha/opac-detail.pl?biblionumber=27095) and CiNii identity records are saved under sources/.',
        '- `reviewed-books.jsonl`: per-title decisions, source checks, numeric evidence, conflicts and next actions.',
        '- `priority-sample-candidates.jsonl`: a small staged set for further experimental preparation; every row has training/evaluation eligibility false and no assigned split.',
        '- `overlap-review.json`: exact-identifier screening and limited sampled-text duplicate diagnostics.', '',
        '## Per-title review','',*table,'',
        '## Next concrete work','',
        '1. Repair or replace noisy Marathi extraction using source images; keep poor stylized OCR out of training samples.',
        '2. Resolve the two numeric conflicts and the remaining prosody/rhetoric section boundaries using closer catalog editions and content evidence.',
        '3. Collect Hindi nonfiction and more comparison books in each language; expand reviewed independent works rather than generating extra crops of the same book.',
        '4. Freeze work groups and a balanced split, then compare the frozen multilingual encoder with newly trained hierarchical heads and the unchanged baseline. Camera evaluation remains a separate experiment.','']
    (REVIEW/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':run()
