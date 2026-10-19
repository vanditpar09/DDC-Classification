import unicodedata

import pytest

from src.research.intake_cleaning import prepare_text, script_profile


def test_indic_marks_joiners_and_ordinary_numbers_survive_cleaning():
    text = 'हिन्दी क्\u200dष\nதமிழ் மொழி\nIn 1859, 823 samples cost 294.50 rupees.'
    clean, audit = prepare_text(unicodedata.normalize('NFD', text))
    assert clean == unicodedata.normalize('NFC', text)
    assert '\u200d' in clean
    assert not audit['removed_lines']


def test_only_explicit_call_number_fields_are_removed():
    text = 'Call number: 891.433 PRE\nDDC: 894.8113\nDewey Decimal Classification: 823.7\nChapter 494\nWe call number 823 an example.\n891.433'
    clean, audit = prepare_text(text)
    assert clean == 'Chapter 494\nWe call number 823 an example.\n891.433'
    assert len(audit['removed_lines']) == 3


def test_gutenberg_license_is_not_a_training_chapter():
    text = 'Source metadata\n*** START OF THE PROJECT GUTENBERG EBOOK BOOK ***\nBody\n*** END OF THE PROJECT GUTENBERG EBOOK BOOK ***\nLicense'
    clean, audit = prepare_text(text, gutenberg=True)
    assert clean == 'Body'
    assert len(audit['removed_regions']) == 2
    clean, _ = prepare_text('THE FULL PROJECT GUTENBERG™ LICENSE\n*** END OF THE PROJECT GUTENBERG EBOOK BOOK ***\nLegal text', gutenberg=True)
    assert clean == ''
    # A Gutenberg reference within ordinary prose does not remove the chapter.
    assert prepare_text('We discuss Project Gutenberg here.', gutenberg=True)[0]


def test_only_configured_footer_removed_and_pdf_page_numbers_are_opt_in():
    text = 'श्यामची आई\nwww.esahity.com\nSee www.example.org for the algorithm.\n17'
    clean, audit = prepare_text(text, ['www.esahity.com'], pdf=True)
    assert clean == 'श्यामची आई\nSee www.example.org for the algorithm.'
    assert len(audit['removed_lines']) == 2
    assert prepare_text('17')[0] == '17'


def test_legacy_tamil_extraction_does_not_pass_script_diagnostic():
    assert not script_profile('¦¾¡ø¸¡ôÀ¢Âõ', 'tam')['has_expected_script']
    assert script_profile('தொல்காப்பியம்', 'tam')['has_expected_script']
    assert script_profile('', 'hin')['expected_script_fraction'] is None
    with pytest.raises(ValueError):
        script_profile('example', 'unknown')
