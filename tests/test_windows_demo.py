"""Windows tool discovery and portable model integrity without a Windows host."""
import json
import os
from pathlib import Path

import pytest
from prototype import portable_ocr, runtime, share


def test_explicit_tesseract_path_can_contain_spaces(monkeypatch,tmp_path):
    executable=tmp_path/'Program Files'/'Tesseract-OCR'/'tesseract.exe'
    executable.parent.mkdir(parents=True);executable.write_bytes(b'fixture')
    monkeypatch.setenv('TESSERACT_CMD',str(executable))
    monkeypatch.setattr(runtime.shutil,'which',lambda name:None)
    assert runtime.find_tesseract()==str(executable)


def test_invalid_tesseract_override_is_not_silently_ignored(monkeypatch):
    monkeypatch.setenv('TESSERACT_CMD','nonexistent-ddc-tool')
    monkeypatch.setattr(runtime.shutil,'which',lambda name:None)
    assert runtime.find_tesseract() is None


def test_windows_program_files_detection(monkeypatch,tmp_path):
    # Mock os.name only inside the runtime module: pathlib must keep host semantics.
    from types import SimpleNamespace
    executable=tmp_path/'Tesseract-OCR'/'tesseract.exe'
    executable.parent.mkdir();executable.write_bytes(b'fixture')
    monkeypatch.setattr(runtime,'os',SimpleNamespace(name='nt',environ={'ProgramFiles':str(tmp_path)}))
    monkeypatch.setattr(runtime.shutil,'which',lambda name:None)
    assert runtime.find_tesseract()==str(executable)


def test_sharing_code_writer_does_not_require_unix_fchmod(monkeypatch,tmp_path):
    monkeypatch.delattr(os,'fchmod',raising=False)
    path=tmp_path/'nested'/'access.secret'
    share.private_write(path,'test-only-code\n')
    assert path.read_text()=='test-only-code\n'


def test_manifest_alone_cannot_make_missing_models_ready(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{row['name']:row['sha256'] for row in portable_ocr.MODELS.values()}}))
    assert not portable_ocr.models_present(tmp_path)


def test_modified_portable_model_is_rejected(tmp_path):
    for row in portable_ocr.MODELS.values():
        (tmp_path/row['name']).write_bytes(b'corrupted model')
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{row['name']:row['sha256'] for row in portable_ocr.MODELS.values()}}))
    with pytest.raises(ValueError,match='checksum failed'):
        portable_ocr.verify_models(tmp_path)


def test_inference_downloads_are_denied_even_if_called(monkeypatch):
    from prototype import rapid_ocr_worker
    from rapidocr import RapidOCR
    from rapidocr.utils import DownloadFile
    def unexpected(params):
        DownloadFile.run('test-only-download')
    monkeypatch.setattr(rapid_ocr_worker,'verify_models',lambda:None)
    monkeypatch.setattr('rapidocr.RapidOCR',unexpected)
    monkeypatch.setattr(DownloadFile,'run',DownloadFile.run)
    monkeypatch.setattr('sys.argv',['worker','fixture.png','eng'])
    with pytest.raises(RuntimeError,match='downloads are disabled'):
        rapid_ocr_worker.run()
