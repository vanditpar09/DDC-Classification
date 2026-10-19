"""Optional offline scene-text readers and conservative page framing."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'models/ocr_easy'
EASY_FILES = {'eng':'english_g2.pth', 'eng+hin':'devanagari.pth',
              'eng+mar':'devanagari.pth', 'eng+tam':'tamil.pth'}


def vision_ready():
    binary = ROOT / 'output/vision-ocr'
    fingerprint = ROOT / 'output/vision-ocr-source.sha256'
    return (platform.system() == 'Darwin' and binary.is_file() and fingerprint.is_file()
            and fingerprint.read_text().strip() == hashlib.sha256((ROOT / 'prototype/vision_ocr.swift').read_bytes()).hexdigest())


def easy_ready(language):
    return (importlib.util.find_spec('easyocr') is not None
            and (MODEL_DIR / 'manifest.json').is_file()
            and (MODEL_DIR / 'craft_mlt_25k.pth').is_file()
            and (MODEL_DIR / EASY_FILES.get(language, 'unsupported')).is_file())


def rapid_ready(language):
    from prototype.portable_ocr import models_present
    return (language == 'eng' and importlib.util.find_spec('rapidocr') is not None
            and importlib.util.find_spec('onnxruntime') is not None and models_present())


def reading_order(lines):
    """Order fragmented tilted lines left-to-right using geometry, never words."""
    rows = []
    for line in sorted(lines, key=lambda item:(item['top']+item['height']/2, item['left'])):
        center = line['top']+line['height']/2
        target = None
        for row in reversed(rows):
            anchor = row[0]
            minimum_height = min(anchor['height'], line['height'])
            overlap = min(anchor['top']+anchor['height'], line['top']+line['height'])-max(anchor['top'], line['top'])
            if (minimum_height > 0 and overlap >= minimum_height*.5
                    and abs(center-anchor['top']-anchor['height']/2) <= minimum_height*.5):
                target = row
                break
        if target is None:
            rows.append([line])
        else:
            target.append(line)
    return [line for row in rows for line in sorted(row, key=lambda item:item['left'])]


def prepare_page(image):
    """Find a large central convex page; never guess a title/text-specific crop."""
    identity = np.eye(3)
    metadata = {'page_detected':False, 'method':'original', 'polygon':None}
    try:
        import cv2
    except ImportError:
        return image, identity, metadata
    cv2.setNumThreads(1)
    scale = min(1, 768 / max(image.size))
    small = cv2.resize(np.asarray(image),(round(image.width*scale),round(image.height*scale)),interpolation=cv2.INTER_LINEAR)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    candidates = []
    height, width = gray.shape
    for low, high in ((30,100),(60,180),(10,50)):
        edges = cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),low,high)
        edges = cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        contours, _ = cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            perimeter = cv2.arcLength(contour,True)
            for epsilon in (.02,.04,.06):
                quad = cv2.approxPolyDP(contour,epsilon*perimeter,True)
                area = cv2.contourArea(quad)/(width*height)
                if (len(quad)==4 and cv2.isContourConvex(quad) and .20<area<.95
                        and cv2.pointPolygonTest(quad,(width/2,height/2),False)>=0):
                    candidates.append((area,quad.reshape(4,2).astype(np.float32)/scale))
    if not candidates:
        return image, identity, metadata
    points = max(candidates,key=lambda candidate:candidate[0])[1]
    ordered = np.empty((4,2),dtype=np.float32)
    sums = points.sum(axis=1); differences = np.diff(points,axis=1).ravel()
    ordered[0]=points[np.argmin(sums)]; ordered[2]=points[np.argmax(sums)]
    ordered[1]=points[np.argmin(differences)]; ordered[3]=points[np.argmax(differences)]
    if len(np.unique(ordered,axis=0))!=4:
        return image, identity, metadata
    target_w = round(max(np.linalg.norm(ordered[1]-ordered[0]),np.linalg.norm(ordered[2]-ordered[3])))
    target_h = round(max(np.linalg.norm(ordered[3]-ordered[0]),np.linalg.norm(ordered[2]-ordered[1])))
    if min(target_w,target_h)<100 or not .25<target_w/target_h<2.5:
        return image, identity, metadata
    # Avoid enlarging a noisy photo or allocating beyond the input pixel budget.
    resize = min(1,1600/max(target_w,target_h))
    target_w, target_h = round(target_w*resize), round(target_h*resize)
    destination = np.array([[0,0],[target_w-1,0],[target_w-1,target_h-1],[0,target_h-1]],dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(ordered,destination)
    working = cv2.warpPerspective(np.asarray(image),matrix,(target_w,target_h),borderMode=cv2.BORDER_REPLICATE)
    metadata = {'page_detected':True, 'method':'central-quadrilateral-perspective',
                'polygon':ordered.tolist(), 'processed_size':[target_w,target_h]}
    return Image.fromarray(working), np.linalg.inv(matrix), metadata


def recognize_scene(image, language, policy, backend):
    """One bounded detection/recognition pipeline; all data stays on the laptop."""
    started = time.perf_counter()
    working, inverse, capture = prepare_page(image)
    if backend in {'vision', 'rapid'}:
        # Scene readers handle perspective in the original photo. Resampling its
        # decorative lettering can hurt recognition, so retain original pixels
        # and use the detected polygon to exclude background observations.
        working, inverse = image, np.eye(3)
        if capture['page_detected']:
            capture['method'] = 'central-quadrilateral-text-filter'
            capture['processed_size'] = list(image.size)
    with tempfile.TemporaryDirectory(prefix='ddc-local-ocr-') as directory:
        path = Path(directory) / 'page.png'
        working.save(path)
        if backend == 'vision':
            command = [str(ROOT / 'output/vision-ocr'), str(path), 'en-US']
        elif backend == 'easy':
            command = [sys.executable, str(ROOT / 'prototype/easy_ocr_worker.py'), str(path), language]
        elif backend == 'rapid':
            command = [sys.executable, str(ROOT / 'prototype/rapid_ocr_worker.py'), str(path), language]
        else:
            raise ValueError('Unknown local OCR backend')
        response = subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=45,check=False,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    if response.returncode:
        # Do not echo subprocess internals or paths into the phone UI.
        raise RuntimeError('The local scene-text reader could not complete this image')
    result = json.loads(response.stdout)
    if backend in {'vision', 'rapid'} and capture['page_detected']:
        import cv2
        polygon = np.asarray(capture['polygon'],dtype=np.float32)
        result['lines'] = [line for line in result['lines'] if cv2.pointPolygonTest(polygon,
            (line['left']+line['width']/2,line['top']+line['height']/2),False)>=0]
    words = []
    lines = reading_order(result['lines'])
    for line in lines:
        x,y,w,h = (line[k] for k in ('left','top','width','height'))
        corners = np.array([[x,y,1],[x+w,y,1],[x+w,y+h,1],[x,y+h,1]],dtype=float).T
        projected = inverse @ corners; projected = projected[:2]/projected[2:]
        left,top = np.maximum(0,projected.min(axis=1)).astype(int)
        right,bottom = np.minimum(image.size,projected.max(axis=1)).astype(int)
        # Neural reader scores describe a line, not independently scored words.
        for text in line['text'].split():
            words.append({'text':text,'confidence':line['confidence']*100,'left':int(left),'top':int(top),
                          'width':max(1,int(right-left)),'height':max(1,int(bottom-top))})
    confidences = [word['confidence'] for word in words]
    mean = float(np.mean(confidences)) if confidences else 0
    bad = sum(conf<policy.min_ocr_confidence for conf in confidences)/max(1,len(words))
    text = '\n'.join(line['text'] for line in lines if line['text'].strip())
    # Basic rejection checks only; a high neural score still cannot verify text.
    usable = bool(text.strip()) and mean>=policy.min_ocr_confidence and bad<=policy.max_low_confidence_fraction
    from scipy.ndimage import laplace
    sharpness = float(laplace(np.asarray(ImageOps.grayscale(working),dtype=float)).var())
    usable = usable and sharpness>=policy.min_sharpness
    bounds = capture['polygon'] or [[0,0],[image.width,0],[image.width,image.height],[0,image.height]]
    left,top = np.min(bounds,axis=0); right,bottom = np.max(bounds,axis=0)
    return {'text':text,'words':words,'usable':bool(usable),
        'quality':{'ocr_confidence':mean,'low_confidence_fraction':bad,'word_count':len(words),
            'median_character_height':float(np.median([word['height'] for word in words])) if words else 0,
            'sharpness':sharpness,'script':None,'script_mismatch':False,'suggested_languages':[],
            'engine':result['engine'],'confidence_source':'line recognizer; uncalibrated',
            'capture':capture,
            'region':{'left':int(left),'top':int(top),'width':int(right-left),'height':int(bottom-top),
                      'image_width':image.width,'image_height':image.height}},
        'work':{'ocr_passes':1,'pixels':working.width*working.height,'seconds':time.perf_counter()-started}}


def backend_status():
    return {'mode':os.environ.get('FIELDNOTE_OCR','auto'),
            'english_vision_available':vision_ready(),
            'portable_english_available':rapid_ready('eng'),
            'easyocr_languages':[language for language in EASY_FILES if easy_ready(language)],
            'offline_inference':True,'downloads_during_inference':False}
