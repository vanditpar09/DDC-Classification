"""Locate local tools without platform-specific installation assumptions."""
import os
import shutil
from pathlib import Path


def find_tesseract():
    override = os.environ.get('TESSERACT_CMD')
    if override:
        return shutil.which(override) or (override if Path(override).is_file() else None)
    found = shutil.which('tesseract')
    if found:
        return found
    if os.name == 'nt':
        for variable in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
            base = os.environ.get(variable)
            if base:
                path = Path(base) / 'Tesseract-OCR/tesseract.exe'
                if path.is_file():
                    return str(path)
    return None


def disable_network_for_check():
    """Test-only proof that an inference run requires no network connections."""
    import socket
    def denied(*args, **kwargs):
        raise RuntimeError('Network connections disabled during offline demo check')
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
