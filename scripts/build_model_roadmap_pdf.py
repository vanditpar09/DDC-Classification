"""Build the reviewed project roadmap from measured benchmark results."""
from pathlib import Path
import json
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Flowable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/ddc_multilingual_model_and_roadmap.pdf"
REPORT = json.loads((ROOT / "docs/benchmarks/multilingual_v1.json").read_text())
NAVY = colors.HexColor("#17343D")
TEAL = colors.HexColor("#087F83")
PALE = colors.HexColor("#EBF5F3")
INK = colors.HexColor("#243B42")
GRAY = colors.HexColor("#617279")
GOLD = colors.HexColor("#C38632")
WIDTH = A4[0] - 92

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=29, leading=33, textColor=NAVY, spaceAfter=13))
styles.add(ParagraphStyle(name="Deck", fontName="Helvetica", fontSize=12.5, leading=18, textColor=GRAY, spaceAfter=18))
styles.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=TEAL, spaceAfter=11))
styles.add(ParagraphStyle(name="SectionCustom", fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=NAVY, spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle(name="BodyCustom", fontName="Helvetica", fontSize=10.4, leading=15.2, textColor=INK, spaceAfter=9))
styles.add(ParagraphStyle(name="SmallCustom", fontName="Helvetica", fontSize=8.8, leading=12.4, textColor=GRAY, spaceAfter=7))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK))
styles.add(ParagraphStyle(name="HeadCell", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white))
styles.add(ParagraphStyle(name="CodeCustom", fontName="Courier", fontSize=8.4, leading=12, textColor=NAVY, backColor=PALE, borderPadding=9, spaceAfter=12))


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def h(text):
    return p(text, "SectionCustom")


def table(rows, widths):
    cells = [[p(str(x), "HeadCell" if i == 0 else "Cell") for x in row] for i, row in enumerate(rows)]
    t = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, -1), (-1, -1), .5, colors.HexColor("#CFDCDF")),
    ]))
    return t


def callout(title, text):
    t = Table([[p(title, "Kicker")], [p(text)]], colWidths=[WIDTH])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                          ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#BFDCD5")),
                          ("LEFTPADDING", (0, 0), (-1, -1), 13),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 13),
                          ("TOPPADDING", (0, 0), (-1, 0), 13),
                          ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                          ("BOTTOMPADDING", (0, 1), (-1, -1), 8)]))
    return t


class AccuracyChart(Flowable):
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = 155

    def draw(self):
        c = self.canv
        x0, scale = 142, 3.65
        c.setFont("Helvetica", 8)
        for tick in range(0, 101, 20):
            x = x0 + tick * scale
            c.setStrokeColor(colors.HexColor("#DAE3E4"))
            c.line(x, 17, x, 140)
            c.setFillColor(GRAY)
            c.drawCentredString(x, 5, str(tick) + "%")
        for y, label, old, new in [(109, "Catalog text", 61.27, 65.34), (52, "Title + subtitle", 43.69, 55.21)]:
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(0, y + 6, label)
            for offset, value, color in [(13, old, colors.HexColor("#90A3A8")), (-7, new, TEAL)]:
                c.setFillColor(color)
                c.rect(x0, y + offset, value * scale, 14, fill=1, stroke=0)
                c.setFillColor(INK)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x0 + value * scale + 5, y + offset + 3, f"{value:.1f}%")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(0, 139, "GRAY  Previous model")
        c.setFillColor(TEAL)
        c.drawString(0, 126, "TEAL  New model")


def page_header(c, doc):
    c.saveState()
    c.setFillColor(TEAL)
    c.rect(0, A4[1] - 10, A4[0], 10, fill=1, stroke=0)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, A4[1] - 35, "DDC CLASSIFICATION  /  MODEL & PRODUCT ROADMAP")
    c.setStrokeColor(colors.HexColor("#D6E2E4"))
    c.line(46, 40, A4[0] - 46, 40)
    c.setFont("Helvetica", 8)
    c.drawString(46, 27, "23 September 2026  |  Ten broad DDC classes")
    c.drawRightString(A4[0] - 46, 27, f"{doc.page} / 7")
    c.restoreState()


story = []


def page(kicker, title, subtitle=None):
    if story:
        story.append(PageBreak())
    story.extend([p(kicker, "Kicker"), p(title, "TitleCustom")])
    if subtitle:
        story.append(p(subtitle, "Deck"))


page("01 / RESULTS", "A stronger model.<br/>A more distinctive project.", "Build a multilingual cataloging assistant that can show its evidence and ask for more information.")
story.append(callout("COMPLETED NOW", "Trained a local multilingual E5-small classifier, compared 16 candidates, protected book groups and historical holdouts, and saved a reproducible evaluation. The new model improves overall catalog and cover-proxy results."))
story.extend([Spacer(1, 10), AccuracyChart(), Spacer(1, 8)])
story.append(table([
    ["Same 1,007 test books", "Catalog accuracy", "Cover accuracy"],
    ["Previous saved baseline", "61.27%", "43.69%"],
    ["TF-IDF with matched new splits", "60.48%", "44.59%"],
    ["Selected multilingual E5", "<b>65.34%</b>", "<b>55.21%</b>"],
], [WIDTH * .52, WIDTH * .24, WIDTH * .24]))
story.extend([h("What these results mean"), p("The largest gain is on sparse input: <b>+11.52 percentage points</b> when every test book is reduced to its title and available subtitle. Catalog macro-F1 rose from 0.612 to 0.653; cover-proxy macro-F1 rose from 0.436 to 0.552."),
              p("These are catalog-text results. A cover proxy is clean text, not an image or OCR output. The project still needs independently labeled Indian-language books and real photographs before claiming multilingual scan accuracy.", "SmallCustom")])

page("02 / TRAINING", "What changed in the model", "A pretrained multilingual text encoder, a locally trained DDC head, and separate calibration.")
story.append(table([
    ["Stage", "Implemented protocol"],
    ["Inputs", "Catalog raw_text plus title/subtitle views. Preserve Unicode; exclude labels, IDs, review fields and authors from model features."],
    ["Partition", "3,061 training / 542 calibration / 1,007 test / 424 historical-reserved books. Save exact book and group assignments."],
    ["Selection", "16 candidates, three grouped folds. Optimize the mean of catalog and cover-proxy macro-F1 using training books only."],
    ["Winner", "Frozen multilingual E5-small + logistic regression, C=10. Two text views where available; each book retains total weight 1."],
    ["Calibration", "Sigmoid calibration on separate books, one seeded text view per book. Encoder weights are not fine-tuned."],
], [100, WIDTH - 100]))
story.extend([h("Evidence and tradeoffs"), p("Compared with the previous model, paired book-group bootstrap intervals are <b>+1.10 to +7.18 points</b> for catalog accuracy and <b>+8.26 to +15.09 points</b> for cover accuracy (95%, 2,000 resamples). They describe this dataset; they do not account for OCR or language shift."),
              p("Catalog accuracy on books with subject headings fell from 82.13% to 77.78%; without subjects it rose from 46.71% to 56.66%. The selected model favors the sparse inputs closer to the intended application. The matched TF-IDF reference uses the same new training/calibration books."),
              h("What is verified, and what remains open"),
              p("37 targeted tests passed. The saved model reloads offline. A few Hindi, Marathi and Tamil phrase checks produce plausible labels, but they are not a multilingual test set. The original test was already inspected; an independent photo benchmark remains necessary."),
              p("The unchanged 0.85 auto-accept threshold accepts zero new-model test cases. Keep the candidate separate until routing is validated on development scans. The encoder truncates inputs beyond 512 tokens; long pages need chunking. [1, 2]", "SmallCustom")])

page("03 / RESEARCH", "Where the project can stand out", "Automated classification already exists. Distinction should come from a specific workflow and measurable evidence.")
story.append(table([
    ["Existing work", "What it establishes", "Project opportunity"],
    ["Annif [3]", "Open-source, multilingual subject indexing and classification; used by libraries.", "Evaluate against an established approach rather than claiming the first automated classifier."],
    ["OCLC AI Enrichment [4]", "Suggests DDC, LCC and subject headings from bibliographic records.", "Focus on photographed regional-language books and the process of obtaining sufficient evidence."],
    ["Multilingual E5 [1]", "Reusable multilingual text embeddings.", "Measure local DDC performance by language, script, input richness and OCR quality."],
    ["IndicTrans2 [5]", "Open translation models covering India's 22 scheduled languages.", "Compare native-script classification with a translation-assisted baseline on the same books."],
], [107, 191, WIDTH - 298]))
story.extend([h("Recommended project identity"), callout("PROPOSED POSITIONING", "An evidence-aware multilingual cataloging assistant for Indian libraries: scan a book, inspect its subject evidence, request another page when needed, and let a librarian confirm the result."),
              Spacer(1, 10), p("This is a proposed combination and evaluation focus, not a claim of worldwide novelty. A strong project report should show which components help, against which baselines, and for which languages."),
              h("A research question you can actually test"),
              p("<b>Does requesting the back cover or contents page on uncertain Indian-language books improve classification per additional scan, compared with always using only the front cover?</b> Measure accuracy, time, pages requested and librarian corrections. This turns a UI feature into an experiment.")])

page("04 / DIFFERENTIATORS", "Six practical ways to be distinctive", "Build the first three as the core demonstration. Treat the others as staged extensions.")
features = [
    ("1. Ask for the right next page", "When evidence is weak, request a clearer photo, back-cover description or contents page. Start with explicit rules; learn page selection only after collecting paired scans.", "Measure gain per extra scan and total cataloging time."),
    ("2. Show inspectable evidence", "Display extracted text regions, source page and similar reviewed books from the training catalog. Similar examples are supporting context, not proof of a model's reasoning.", "Have librarians score evidence relevance and correction effort."),
    ("3. Preserve Indian scripts", "Keep the original OCR text and an optional translation side by side. Test Hindi and Marathi first, then expand based on available reviewers and books.", "Report per-language macro-F1 and OCR character error rate."),
    ("4. Admit uncertainty", "Show top alternatives and a review option. Later compare calibrated thresholds with conformal prediction sets using separate calibration data. Coverage assumptions can fail under OCR/language shift. [6]", "Plot accepted-case precision against coverage for each language."),
    ("5. Learn from reviewed corrections", "Prioritize uncertain and diverse development examples for annotation; record who changed the label and why. Retrain only on approved, versioned releases. [7]", "Compare improvement per 100 reviewed books with random sampling."),
    ("6. Verify known editions", "Use a scanned ISBN to retrieve an edition record and attach provenance. Keep catalog lookup results distinct from predictions and score them separately. [8]", "Measure correct-match rate and end-to-end time saved."),
]
for title, body, measure in features:
    story.append(KeepTogether([h(title), p(body), p("<b>Success measure:</b> " + measure, "SmallCustom")]))

page("05 / MULTILINGUAL DATA", "The dataset is the next bottleneck", "Language support in an encoder does not establish subject-classification accuracy in that language.")
story.extend([p("Begin with English and two priority Indian languages, provisionally Hindi and Marathi. A pilot of <b>20 books per class per language</b> gives 600 books across three languages. This is a starting collection target, not enough by itself for precise language-level reliability claims."),
              table([
                  ["Collect for each book", "Why it matters"],
                  ["Original title, language and script", "Do not confuse the language of a book with its subject. A Hindi physics book belongs to science, not automatically class 400."],
                  ["Cover, back cover, contents photos", "Measure extra-page value, blur, glare, rotation and different scripts using real captures."],
                  ["Verified broad DDC label + evidence", "Record a catalog source or librarian decision; review ambiguity rather than guessing from a title."],
                  ["Work/edition/translation links", "Keep related editions, translated copies, photos and text variants in one partition."],
                  ["Human transcription + OCR output", "Separate recognition errors from classification errors; preserve missing fields."],
              ], [177, WIDTH - 177]),
              h("Compare four input conditions"),
              p("Use the same books for human-transcribed titles, OCR titles, title plus description, and title plus description plus contents. Compare the native-script encoder with a translation-assisted baseline. Evaluate each condition by language and class; do not average away a weak language."),
              h("Keep a final test independent"),
              p("Assign new book groups to development and final test before modeling. Keep the final labels out of model selection and human-review sampling. Expand the pilot's test portion until confidence intervals are useful. Machine translations may augment training, but cannot substitute for real native-language test books."),
              p("Current blocker: the local Tesseract path rejects non-Latin scripts. It needs language-pack selection and script-aware handling before this is an end-to-end multilingual scanning system. Tesseract publishes language models, but installed packs still require evaluation on your photos. [9]", "SmallCustom")])

page("06 / DELIVERY PLAN", "A staged plan your team can execute", "Indicative four-week sequence, dependent on access to books and language reviewers.")
story.append(table([
    ["Stage", "Deliverable", "Decision gate"],
    ["Now - completed", "Multilingual text classifier; candidate benchmark; saved splits and metrics; text inference command.", "65.34% catalog accuracy; 55.21% cover-proxy accuracy. 37 targeted tests pass."],
    ["Week 1 - data + OCR", "Choose two Indian languages, recruit reviewers, collect pilot scans, configure OCR packs.", "Human labels and transcripts are auditable; book groups cannot cross splits."],
    ["Week 2 - comparisons", "Native-script vs translation baseline; title vs extra pages; language-wise error analysis.", "Choose using development results; keep the final test sealed."],
    ["Week 3 - useful UI", "Evidence panel, request-another-page flow, top alternatives and correction log.", "Measure time saved and correction burden with librarians."],
    ["Week 4 - final evaluation", "One final evaluation, ablation table, deployment profile and reproducible model card.", "Report accuracy, macro-F1, latency, review rate, calibration and language-specific limits."],
], [93, 217, WIDTH - 310]))
story.extend([h("Handoff: try the new model"),
              p("From the repository root, using the existing virtual environment:", "SmallCustom"),
              p(".venv/bin/python -m src.ocr_pipeline.predict_text \\<br/>&nbsp;&nbsp;&quot;Introduction to computer programming&quot;", "CodeCustom"),
              p("The command also accepts Unicode text. Full setup, download, retraining and integration instructions are in <b>docs/MODEL_IMPROVEMENT.md</b>. The artifact is <b>models/improved_v1/classifier.joblib</b>; also retain the encoder directory when moving it to another machine.", "SmallCustom"),
              h("Before using automatic acceptance"),
              p("Choose a precision/coverage target on representative development scans. For example, 95% accepted-case precision is a possible project goal, not an achieved result. Evaluate the local model, Gemini and their ensemble independently. The current web app still uses the original model; the new classifier is available through local text inference."),
              p("Hardware: this experiment ran locally on CPU. A GPU is optional for encoder fine-tuning later. The downloaded encoder weighs about 449 MiB plus tokenizer files; the classifier alone is not a complete deployment package.", "SmallCustom")])

page("07 / SOURCES & SCOPE", "Research references and limits", "Primary sources consulted on 23 September 2026. Numbered citations refer to these sources.")
sources = [
    ("1", "Multilingual E5: technical report and model card", "https://arxiv.org/abs/2402.05672", "https://huggingface.co/intfloat/multilingual-e5-small"),
    ("2", "scikit-learn: probability calibration", "https://scikit-learn.org/1.6/modules/generated/sklearn.calibration.CalibratedClassifierCV.html", None),
    ("3", "Annif: automated subject indexing and classification", "https://annif.org/", None),
    ("4", "OCLC: AI Enrichment macro", "https://help.oclc.org/Metadata_Services/Connexion/Connexion_client/Connexion_client_toolkits/OCLC_Cataloging_AI_macro", None),
    ("5", "AI4Bharat: IndicTrans2", "https://github.com/AI4Bharat/IndicTrans2", None),
    ("6", "Angelopoulos &amp; Bates: introduction to conformal prediction", "https://arxiv.org/abs/2107.07511", None),
    ("7", "Fang et al.: Learning how to Active Learn", "https://aclanthology.org/D17-1063/", None),
    ("8", "Open Library: edition and ISBN APIs", "https://openlibrary.org/dev/docs/api/books", None),
    ("9", "Tesseract: language model repository", "https://github.com/tesseract-ocr/tessdata", None),
]
for number, title, url, second in sources:
    text = f'<b>[{number}] {title}</b><br/><link href="{escape(url)}" color="#087F83">Open primary source</link>'
    if second:
        text += f' | <link href="{escape(second)}" color="#087F83">Model card</link>'
    story.append(p(text, "SmallCustom"))
story.extend([h("Local evidence"),
              p("The measured results come from models/improved_v1/metrics.json, cv_results.json, split_assignments.json and test_predictions.csv. The source dataset has 5,034 books; its integrity verification passed. The original classifier is retained at models/baseline_classifier.joblib.", "SmallCustom"),
              h("Scope of the claims"),
              p("Completed: a stronger local text classifier and a reproducible training protocol. Proposed: multilingual scan acquisition, script-aware OCR, evidence retrieval, adaptive page requests, reviewed corrections and uncertainty-aware routing. None of those proposed product features is claimed as already delivered.", "SmallCustom"),
              p("The classification target remains ten broad DDC classes. Detailed decimal-number prediction requires different labels, evaluation and an explicit scope change. Accuracy on this purposive catalog sample is not a guarantee for another library, language or photographic condition.", "SmallCustom")])

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=46, leftMargin=46,
                        topMargin=58, bottomMargin=56, title="DDC: Multilingual Model and Project Roadmap",
                        author="DDC Classification project", subject="Measured model improvements and researched project directions")
doc.build(story, onFirstPage=page_header, onLaterPages=page_header)
print(OUT)
