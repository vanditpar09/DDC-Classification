"""Narrow runtime fix for the published Tamil model's truncated alphabet.

Source: JaidedAI/EasyOCR PR #1333, commit a241a7f (16 November 2024).
The official weights have 143 outputs including the CTC blank. Version 1.7.2's
config omits the final 16 alphabet entries. Never alter their ordering.
"""


def configure_tamil():
    from easyocr.config import recognition_models
    model = recognition_models['gen1']['tamil_g1']
    characters = model['characters']
    if len(characters) == 126 and characters.endswith('ரறலளழ'):
        model['characters'] += 'வஷஸஹாிீுூெேைொோௌ்'
    if len(model['characters']) != 142:
        raise RuntimeError('Unsupported Tamil recognition alphabet; check the pinned OCR package')
