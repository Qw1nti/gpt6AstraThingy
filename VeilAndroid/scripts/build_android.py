#!/usr/bin/env python3
"""Build a debug APK with Java 17+, Android SDK 35 and verified Gradle 8.11.1."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '8.11.1'

def run(args):
    subprocess.run(args, cwd=ROOT, check=True)

def gradle():
    name = 'gradle.bat' if os.name == 'nt' else 'gradle'
    home = ROOT / '.tools' / ('gradle-' + VERSION)
    executable = home / 'bin' / name
    if executable.exists():
        return executable
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    archive = tools / ('gradle-' + VERSION + '-bin.zip')
    url = 'https://services.gradle.org/distributions/' + archive.name
    print('Downloading Gradle ' + VERSION + ' from its official distribution service…', flush=True)
    with urllib.request.urlopen(url + '.sha256', timeout=60) as response:
        expected = response.read().decode().strip().split()[0]
    with urllib.request.urlopen(url, timeout=180) as response, archive.open('wb') as out:
        shutil.copyfileobj(response, out)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        archive.unlink()
        raise RuntimeError('Gradle checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            path = (tools / entry.filename).resolve()
            if tools.resolve() not in path.parents:
                raise RuntimeError('Unsafe distribution path')
        z.extractall(tools)
    if os.name != 'nt':
        executable.chmod(0o755)
    archive.unlink()
    return executable

def main():
    if not shutil.which('java') or not shutil.which('javac'):
        raise RuntimeError('Install JDK 17 and put java and javac on PATH.')
    candidates = [os.environ.get('ANDROID_HOME'), os.environ.get('ANDROID_SDK_ROOT'),
                  str(Path.home() / 'Library/Android/sdk'), str(Path.home() / 'Android/Sdk'),
                  str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Android/Sdk')]
    sdk = next((Path(x) for x in candidates if x and (Path(x) / 'platforms/android-35/android.jar').exists()), None)
    if sdk is None:
        raise RuntimeError('Android SDK 35 not found. Install Android Studio, use SDK Manager to install Android 15 (API 35) and Build-Tools 35.0.0, then rerun. Set ANDROID_HOME for a custom SDK location.')
    os.environ['ANDROID_HOME'] = str(sdk)
    run([sys.executable, 'scripts/fetch_model.py'])
    run([sys.executable, 'scripts/test_core.py'])
    run([str(gradle()), '--no-daemon', ':app:assembleDebug', ':app:lintDebug'])
    output = ROOT / 'app/build/outputs/apk/debug/app-debug.apk'
    if not output.exists():
        raise RuntimeError('Gradle finished without producing the expected APK')
    print('\nAPK ready: ' + str(output))
    print('Transfer this APK to your phone and tap it to install.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('\nBuild failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)
