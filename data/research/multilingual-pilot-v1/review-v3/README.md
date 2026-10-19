# Book review, third pass

4 October 2026. Assistant review; no human/librarian review is claimed.

Assessed all **61 downloaded titles**. Saved **141 rendered PDF page/OCR comparisons** and **183 text windows**. Sources and acquired-book snapshots remain unchanged.

**7 Hindi works have supporting numeric DDC evidence in IIT Gandhinagar’s catalog.** These are matching original titles/authors in other print editions, not exact matches to the digital file. Nannul has additional 494 evidence from a related commentary catalog. Two Tamil texts have 494/894 conflicts.

**The collection is not complete and is not a verified training/test dataset.** The next milestone is 60–80 distinct reviewed works for a small pilot. Around 200 is a planning target for the selected subjects, not a proven minimum. More Hindi nonfiction and broader comparison subjects are still needed.

## What the checks found

- The earlier 57 “text available” count only meant plausible native-script extraction. It does not mean 57 reliable transcripts. Marathi font decoding often changes actual letters even though the output remains in Devanagari.
- Source concordance compares native-script 12-character shingles between independent OCR of three PDF pages and the existing text. The 0.8 screen threshold is a conservative heuristic. It is not CER, confidence, or proof of a correct transcription; low agreement can reflect OCR errors, sparse/illustrated pages, or an edition mismatch as well as extraction errors.
- Hindi book-body extraction uses publisher content elements. Thirteen complete indexed sequences are available across both batches; Kankal is missing part 3. HTML sampling has no independent page-image transcription comparison.
- Nannul and Velir Varalaru need fidelity investigation after lower agreement on sampled pages. Stylized Saichi Vahi OCR is particularly poor. Sources with unreadable passages or partial chapters remain qualified even when OCR agrees.
- Akapporul Vilakkam and Iraiyanar Akapporul have related catalog records with DDC 894, conflicting with their provisional 494 collection labels. Other prosody/rhetoric works also need subject adjudication; no numbers were silently replaced.
- Prema/Pratigya retain their shared conservative group. The selected-writings anthology is quarantined. Shared series/authors remain potential confounders; an exact-identifier check cannot certify independence.
- A librarian is helpful, not required to collect evidence. Record who actually reviewed each source. Assistant proposals, machine OCR, and confirmed benchmark labels are different states.

## Evidence and outputs

- [IIT Gandhinagar Hindi catalog](https://library.iitgn.ac.in/documents/library_files/Hindi-Books.pdf): rendered evidence pages 11, 66, 67 and 69 saved locally.
- [OCLC DDC 23 summary](https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf): vocabulary evidence only; does not classify individual books.
- [CUTN Nannul commentary catalog](https://library.cutn.ac.in/cgi-bin/koha/opac-detail.pl?biblionumber=27095) and CiNii identity records are saved under sources/.
- `reviewed-books.jsonl`: per-title decisions, source checks, numeric evidence, conflicts and next actions.
- `priority-sample-candidates.jsonl`: a small staged set for further experimental preparation; every row has training/evaluation eligibility false and no assigned split.
- `overlap-review.json`: exact-identifier screening and limited sampled-text duplicate diagnostics.

## Per-title review

| Book | Language | Label review | Text review |
| --- | --- | --- | --- |
| நேமிநாதம் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| வடமலை நிகண்டு | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| சூடாமணி நிகண்டு | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| நன்னூல் | tam | 494 supported by related grammar/commentary catalog; original digital edition unresolved | needs source-fidelity investigation |
| சோலைமலை இளவரசி | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| இலக்கணச் சுருக்கம் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| ஐந்திலக்கணம் தொன்னூல் விளக்கம் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| தியாக பூமி | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| பார்வதி பி.ஏ. (புதினம்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| இருளும் ஒளியும் (நாவல்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| लोकशाहीर अण्णा भाऊ साठे निवडक वाङ्मय | mar | quarantined anthology identity; no independent-work or single-label approval | extraction unusable; sampled OCR will be stored separately |
| डिटेक्टिव्ह अल्फा आणि रत्नजडित खंजिराचे रहस्य | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| मुन्नी | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| आनंद | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| फुल्लारी | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| सईची वही | mar | assistant subject-to-section proposal; no matched numeric catalog record | extraction unusable; sampled OCR will be stored separately |
| गबन | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| प्रतिज्ञा | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| निर्मला | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| प्रेमा | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| காதலினால் அல்ல | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| யாப்பெருங்கலக் காரிகை | tam | grammar/prosody/rhetoric boundary requires adjudication | sampled source agreement; unverified full transcription |
| தண்டி அலங்காரம் | tam | grammar/prosody/rhetoric boundary requires adjudication | sampled source agreement; unverified full transcription |
| அந்திம காலம் (நாவல்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| பிரதாப முதலியார் சரித்திரம் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| சிந்துப்பாவியல் | tam | grammar/prosody/rhetoric boundary requires adjudication | sampled source agreement; unverified full transcription |
| அகப்பொருள் விளக்கம் | tam | conflicting section evidence: proposed 494 versus catalog 894 | sampled source agreement; unverified full transcription |
| களவியல் என்னும் இறையனார் அகப்பொருள் | tam | conflicting section evidence: proposed 494 versus catalog 894 | sampled source agreement; unverified full transcription |
| சேரன் செங்குட்டுவன் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| சிதம்பரப்பாட்டியல் (மு. இராகவ ஐயங்கார் உரையுடன்) | tam | grammar/prosody/rhetoric boundary requires adjudication | sampled source agreement; unverified full transcription |
| வேளிர் வரலாறு | tam | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| செய்யுளிலக்கணம் - கத்தியரூபம் | tam | grammar/prosody/rhetoric boundary requires adjudication | sampled source agreement; unverified full transcription |
| வளர்ப்பு மகள் (நாவல்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| ஒரு கோட்டுக்கு வெளியே (நாவல்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| கபோதிபுரத்துக் காதல் | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| நெற்றிக் கண் (2 பாகங்களாக) | tam | assistant subject-to-section proposal; no matched numeric catalog record | extraction unusable; sampled OCR will be stored separately |
| அவள் விழித்திருந்தாள் ( நாவல்) | tam | assistant subject-to-section proposal; no matched numeric catalog record | sampled source agreement; unverified full transcription |
| इब्लिस | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| ऐंद्रजाल | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| बाप : ग्रेट हिरो | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| ओमेगा अपग्रेडेड | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| डिटेक्टिव्ह अल्फा आणि अर्धप्रकाशित खिडकी | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| हिरणं | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| मात | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| पिंजरा | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| परिमार्जन | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| गुप्तहेर सत्यवीर आणि भूतबंगल्याचे रहस्य | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| देवरानी जेठानी की कहानी | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| सूरज का सातवाँ घोड़ा | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| दौड़ | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| परीक्षा गुरु | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| शहर में कर्फ्यू | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| अधखिला फूल | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| ठेठ हिंदी का ठाट | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| कंकाल | hin | work-level numeric section corroborated; exact edition unresolved | partial native source; complete-work claim rejected |
| तितली | hin | work-level numeric section corroborated; exact edition unresolved | candidate native text; source-sample concordance pending |
| देस बिराना | hin | assistant subject-to-section proposal; no matched numeric catalog record | candidate native text; source-sample concordance pending |
| युरोप-कवडसे | mar | assistant subject-to-section proposal; no matched numeric catalog record | extraction unusable; sampled OCR will be stored separately |
| दक्षिण केरळ अर्थात कोची – मुन्नार – तेक्कडी – आलप्पुळा | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| मला भावलेला कॅनडा | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |
| रंग ईशान्येचे | mar | assistant subject-to-section proposal; no matched numeric catalog record | needs source-fidelity investigation |

## Next concrete work

1. Repair or replace noisy Marathi extraction using source images; keep poor stylized OCR out of training samples.
2. Resolve the two numeric conflicts and the remaining prosody/rhetoric section boundaries using closer catalog editions and content evidence.
3. Collect Hindi nonfiction and more comparison books in each language; expand reviewed independent works rather than generating extra crops of the same book.
4. Freeze work groups and a balanced split, then compare the frozen multilingual encoder with newly trained hierarchical heads and the unchanged baseline. Camera evaluation remains a separate experiment.
