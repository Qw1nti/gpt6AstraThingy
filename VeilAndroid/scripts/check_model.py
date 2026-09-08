"""CI-only smoke test of the actual packaged model; no external image fixtures."""
from pathlib import Path
import numpy as np
import onnxruntime as ort

path = Path(__file__).resolve().parents[1] / 'app/src/main/assets/320n.onnx'
session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
entry = session.get_inputs()[0]
assert entry.shape == [1, 3, 320, 320], entry.shape
assert entry.type == 'tensor(float)', entry.type
for value in (0.0, 0.5, 1.0):
    output = session.run(None, {entry.name: np.full((1, 3, 320, 320), value, dtype=np.float32)})[0]
    assert output.ndim == 3 and output.shape[0] == 1 and 22 in output.shape[1:], output.shape
    assert np.isfinite(output).all()
print('ONNX input/output contract and three synthetic inference checks passed.')
