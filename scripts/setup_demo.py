"""Shared Windows/macOS CPU setup for a clone or extracted release package."""
import argparse
import os
import platform
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, default=ROOT / '.venv', help='Optional separate Python environment for verification')
    args = parser.parse_args()
    system = platform.system()
    if system not in ('Windows', 'Darwin') or sys.version_info[:2] != (3, 11):
        raise SystemExit('Use Python 3.11 on Windows x64 or an Apple Silicon Mac. See RUN_GUIDE.md.')
    machine = platform.machine().lower()
    if (system == 'Windows' and machine not in ('amd64','x86_64')) or (system == 'Darwin' and machine not in ('arm64','aarch64')):
        raise SystemExit('This release supports Windows x64 and native Apple Silicon Python. Intel Mac / Windows ARM need separate dependency validation; see RUN_GUIDE.md.')
    from prototype.runtime import find_tesseract
    if not find_tesseract():
        raise SystemExit('Install Tesseract first. See RUN_GUIDE.md. For a custom location, set TESSERACT_CMD.')
    if not (ROOT / 'models/native_silver_v2/classifier.joblib').is_file():
        raise SystemExit('Restore the saved native_silver_v2 classifier from this project before setup.')
    environment = args.environment.resolve()
    python = environment / ('Scripts/python.exe' if system == 'Windows' else 'bin/python')
    if environment.exists() and not python.exists():
        raise SystemExit('This .venv belongs to another operating system. Copy the project without .venv, or rename that folder.')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    target_version = subprocess.check_output([str(python), '-c', 'import sys; print("%d.%d"%sys.version_info[:2])'], text=True).strip()
    if target_version != '3.11':
        raise SystemExit('Use a fresh Python 3.11 project environment; the existing .venv was left unchanged.')
    env = {**os.environ, 'PYTHONUTF8':'1', 'PYTHONIOENCODING':'utf-8', 'HF_HUB_OFFLINE':'0'}
    def command(*args):
        subprocess.run([str(python), *args], cwd=ROOT, env=env, check=True)
    command('-m', 'pip', 'install', '--upgrade', 'pip')
    if system == 'Windows':
        command('-m', 'pip', 'install', 'torch==2.8.0', 'torchvision==0.23.0',
                '--index-url', 'https://download.pytorch.org/whl/cpu')
    command('-m', 'pip', 'install', '-r', 'requirements-windows.txt' if system == 'Windows' else 'requirements-macos.txt')
    command('-m', 'prototype.setup_ocr')
    command('scripts/setup_scene_ocr.py', '--skip-vision')
    encoder = ROOT / 'models/encoders/multilingual-e5-small'
    encoder_files = ('config.json', 'model.safetensors', 'tokenizer.json', 'modules.json',
                     '1_Pooling/config.json', 'tokenizer_config.json', 'special_tokens_map.json',
                     'sentencepiece.bpe.model', 'sentence_bert_config.json')
    if all((encoder / name).is_file() for name in encoder_files):
        print('Reusing the packaged local classifier encoder.', flush=True)
    else:
        command('-m', 'src.ocr_pipeline.download_encoder')
    command('scripts/check_windows_demo.py')
    print('Setup complete. Use scripts/windows-start.cmd or scripts/macos-start.command to run the demo. For a custom environment, run its Python with -m prototype.run --port 8013 --model native_silver_v2.')


if __name__ == '__main__':
    run()
