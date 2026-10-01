"""Fetch the exact public YuNet model and its upstream license at build time."""
from pathlib import Path
import hashlib
import urllib.request

REVISION = "47534e27c9851bb1128ccc0102f1145e27f23f98"
MODEL_SHA256 = "ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0"
LICENSE_SHA256 = "c83b8120c50ccbd4c4f96edf53141bdd566ebb8f8e9227e415326aa1b1aba958"
ROOT = Path(__file__).resolve().parent / "assets"
BASE = f"opencv/opencv_zoo/{REVISION}/models/face_detection_yunet"


def main():
    files = [("yunet.onnx", f"https://media.githubusercontent.com/media/{BASE}/face_detection_yunet_2026may.onnx", MODEL_SHA256),
             ("YUNET-LICENSE.txt", f"https://raw.githubusercontent.com/{BASE}/LICENSE", LICENSE_SHA256)]
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, url, expected in files:
        destination = ROOT/name
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == expected:
            continue
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Checksum mismatch for {name}; refusing installation")
        temp = destination.with_suffix(".tmp")
        temp.write_bytes(data)
        temp.replace(destination)
    print("Verified YuNet face model and upstream license.")


if __name__ == "__main__":
    main()
