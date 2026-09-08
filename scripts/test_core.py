#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='veil-tests-') as out:
    compiler = ['javac'] if shutil.which('javac') else ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main']
    subprocess.run(compiler + ['-d', out,
        str(ROOT / 'app/src/main/java/dev/veil/android/DetectionCore.java'),
        str(ROOT / 'app/src/main/java/dev/veil/android/MaskRegions.java'),
        str(ROOT / 'tests/DetectionCoreTest.java'),
        str(ROOT / 'tests/MaskRegionsTest.java')], check=True)
    subprocess.run(['java', '-cp', out, 'dev.veil.android.DetectionCoreTest'], check=True)
    subprocess.run(['java', '-cp', out, 'dev.veil.android.MaskRegionsTest'], check=True)
