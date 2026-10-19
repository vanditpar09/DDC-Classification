"""Offline reader routing, last-pass bounds, fallback accounting and geometry."""
import numpy as np
import pytest
from PIL import Image

from prototype.controller import Policy
from prototype import engine, scene_ocr


def result(usable=True,passes=1):
    return {'text':'Observed page text','words':[],'usable':usable,'quality':{},
            'work':{'ocr_passes':passes,'pixels':100,'seconds':.1}}


def setup(monkeypatch):
    monkeypatch.setenv('FIELDNOTE_OCR','auto')
    monkeypatch.setattr(scene_ocr,'vision_ready',lambda:True)
    monkeypatch.setattr(scene_ocr,'easy_ready',lambda language:True)
    monkeypatch.setattr(scene_ocr,'rapid_ready',lambda language:False)


def test_selected_indian_script_never_uses_english_vision(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result())
    def unexpected(*args,**kwargs):
        pytest.fail('A readable Indian page must not be sent to English Vision')
    monkeypatch.setattr(scene_ocr,'recognize_scene',unexpected)
    assert engine.recognize(Image.new('RGB',(100,100)),'eng+hin',Policy())['usable']


def test_failed_scene_reader_is_charged_before_tesseract_fallback(monkeypatch):
    setup(monkeypatch)
    def failed(*args,**kwargs):raise RuntimeError('reader failed')
    monkeypatch.setattr(scene_ocr,'recognize_scene',failed)
    seen=[]
    def tesseract(*args,**kwargs):seen.append(kwargs['allow_osd']);return result()
    monkeypatch.setattr(engine,'recognize_tesseract',tesseract)
    output=engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())
    assert seen==[False]
    assert output['work']['ocr_passes']==2
    assert output['work']['pixels']==10100


def test_rejected_neural_read_can_use_tesseract_without_unbounded_retries(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:result(False))
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result(True))
    output=engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())
    assert output['usable'] and output['work']['ocr_passes']==2
    assert len(output['quality']['attempts'])==2


def test_second_reader_failure_never_repeats_that_reader(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:result(False))
    calls=[]
    def failed(*args,**kwargs):calls.append(1);raise RuntimeError('second reader failed')
    monkeypatch.setattr(engine,'recognize_tesseract',failed)
    with pytest.raises(RuntimeError,match='second reader failed'):
        engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())
    assert calls==[1]


def test_scene_failure_with_one_pass_left_cannot_run_another_reader(monkeypatch):
    setup(monkeypatch)
    def failed(*args,**kwargs):raise RuntimeError('reader failed')
    monkeypatch.setattr(scene_ocr,'recognize_scene',failed)
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:pytest.fail('OCR budget exceeded'))
    with pytest.raises(ValueError,match='remaining pass budget'):
        engine.recognize(Image.new('RGB',(100,100)),'eng',Policy(),allow_osd=False)


def test_unreliable_native_page_can_use_second_pass_for_scene_ocr(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result(False))
    used=[]
    def scene(image,language,policy,backend):used.append((language,backend));return result(True)
    monkeypatch.setattr(scene_ocr,'recognize_scene',scene)
    output=engine.recognize(Image.new('RGB',(100,100)),'eng+mar',Policy())
    assert used==[('eng+mar','easy')]
    assert output['usable'] and output['work']['ocr_passes']==2


def test_native_fallback_does_not_exceed_two_reserved_passes(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result(False,2))
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:pytest.fail('Third OCR pass'))
    assert engine.recognize(Image.new('RGB',(100,100)),'eng+tam',Policy())['work']['ocr_passes']==2


def test_explicit_tesseract_mode_does_not_call_scene_reader(monkeypatch):
    setup(monkeypatch);monkeypatch.setenv('FIELDNOTE_OCR','tesseract')
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result(False))
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:pytest.fail('Unexpected scene reader'))
    assert not engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())['usable']


def test_blank_image_is_not_cropped():
    image=Image.new('RGB',(500,700),'white')
    working,inverse,metadata=scene_ocr.prepare_page(image)
    assert not metadata['page_detected'] and working.size==image.size
    assert np.array_equal(inverse,np.eye(3))


def test_page_perspective_maps_back_to_original_image():
    cv2=pytest.importorskip('cv2')
    original=np.zeros((700,500,3),dtype=np.uint8)
    quad=np.array([[90,80],[420,120],[390,630],[65,600]],dtype=np.int32)
    cv2.fillConvexPoly(original,quad,(240,240,240))
    working,inverse,metadata=scene_ocr.prepare_page(Image.fromarray(original))
    assert metadata['page_detected']
    assert working.width<500 and working.height<700
    corners=np.array([[0,0,1],[working.width-1,0,1],[working.width-1,working.height-1,1],[0,working.height-1,1]]).T
    projected=inverse@corners;projected=projected[:2]/projected[2:]
    assert np.max(np.abs(projected.T-np.array(metadata['polygon'])))<.01


def test_windows_auto_uses_portable_reader_without_vision(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(scene_ocr,'vision_ready',lambda:False)
    monkeypatch.setattr(scene_ocr,'rapid_ready',lambda language:language=='eng')
    used=[]
    def scene(image,language,policy,backend):used.append(backend);return result()
    monkeypatch.setattr(scene_ocr,'recognize_scene',scene)
    engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())
    assert used==['rapid']


def test_portable_demo_mode_cannot_accidentally_use_mac_vision(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setenv('FIELDNOTE_OCR','portable')
    monkeypatch.setattr(scene_ocr,'rapid_ready',lambda language:language=='eng')
    used=[]
    def scene(image,language,policy,backend):used.append(backend);return result()
    monkeypatch.setattr(scene_ocr,'recognize_scene',scene)
    engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())
    assert used==['rapid']


def test_portable_demo_mode_fails_clearly_if_models_are_missing(monkeypatch):
    setup(monkeypatch);monkeypatch.setenv('FIELDNOTE_OCR','portable')
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:pytest.fail('Demo reader missing'))
    with pytest.raises(ValueError,match='not ready'):
        engine.recognize(Image.new('RGB',(100,100)),'eng',Policy())


def test_portable_mode_preserves_selected_indian_script(monkeypatch):
    setup(monkeypatch);monkeypatch.setenv('FIELDNOTE_OCR','portable')
    monkeypatch.setattr(scene_ocr,'rapid_ready',lambda language:language=='eng')
    monkeypatch.setattr(engine,'recognize_tesseract',lambda *args,**kwargs:result())
    monkeypatch.setattr(scene_ocr,'recognize_scene',lambda *args,**kwargs:pytest.fail('English reader received Indian selection'))
    assert engine.recognize(Image.new('RGB',(100,100)),'eng+hin',Policy())['usable']


def test_reading_order_handles_tilted_fragments_without_title_hints():
    lines=[{'text':'third','left':160,'top':10,'height':30},
           {'text':'second','left':90,'top':15,'height':30},
           {'text':'first','left':20,'top':20,'height':30},
           {'text':'next row','left':20,'top':80,'height':30}]
    assert [line['text'] for line in scene_ocr.reading_order(lines)]==['first','second','third','next row']
