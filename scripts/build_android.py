#!/usr/bin/env python3
"""Build and lint with Java 17, SDK 35 and the checked-in Gradle wrapper."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(args):
    subprocess.run(args, cwd=ROOT, check=True)

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
    wrapper = ROOT / ('gradlew.bat' if os.name == 'nt' else 'gradlew')
    run([str(wrapper), '--no-daemon', ':app:assembleDebug', ':app:lintDebug'])
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
