#!/usr/bin/env python3
"""Acquire the exact upstream wheel, verify it, extract model and upstream license only."""
from pathlib import Path
import hashlib
import io
import json
import os
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
WHEEL_NAME = 'nudenet-3.4.2-py3-none-any.whl'
WHEEL_SHA256 = '5937dbd84e5d8e5de038f08ffea5a1bb50a08475776bf2b4795914ce0eaf0331'

def download(url):
    if not url.startswith('https://'):
        raise ValueError('HTTPS required')
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()

def install_wheel(data):
    actual = hashlib.sha256(data).hexdigest()
    if actual != WHEEL_SHA256:
        raise ValueError('NudeNet wheel checksum mismatch; nothing installed')
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        model = wheel.read('nudenet/320n.onnx')
        licenses = [n for n in wheel.namelist() if '.dist-info/' in n and 'license' in n.lower()]
        if not licenses:
            raise ValueError('Upstream license missing from wheel; refusing incomplete packaging')
        license_text = b'\n\n'.join(wheel.read(n) for n in licenses)
    if len(model) < 1_000_000:
        raise ValueError('Unexpected model size')
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, payload in [('320n.onnx', model), ('NUDENET-LICENSE.txt', license_text)]:
        temp = ASSETS / (name + '.tmp')
        temp.write_bytes(payload)
        os.replace(temp, ASSETS / name)
    origin = {'package': 'nudenet', 'version': '3.4.2', 'wheel_sha256': actual,
              'model_sha256': hashlib.sha256(model).hexdigest(),
              'source': 'https://pypi.org/project/nudenet/3.4.2/'}
    (ASSETS / 'model-origin.json').write_text(json.dumps(origin, indent=2) + '\n')
    print('Verified and installed NudeNet 320n model and upstream license.')

def main():
    metadata = ASSETS / 'model-origin.json'
    model = ASSETS / '320n.onnx'
    if metadata.exists() and model.exists() and (ASSETS / 'NUDENET-LICENSE.txt').exists():
        origin = json.loads(metadata.read_text())
        if origin.get('wheel_sha256') == WHEEL_SHA256 and origin.get('model_sha256') == hashlib.sha256(model.read_bytes()).hexdigest():
            print('Verified existing model.'); return
    data = json.loads(download('https://pypi.org/pypi/nudenet/3.4.2/json'))
    entry = next(x for x in data['urls'] if x['filename'] == WHEEL_NAME)
    if entry['digests']['sha256'] != WHEEL_SHA256:
        raise ValueError('Package metadata checksum differs from pinned checksum')
    install_wheel(download(entry['url']))

if __name__ == '__main__':
    main()
