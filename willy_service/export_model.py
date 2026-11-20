"""One time, on the server: download multilingual-e5-small and save it as ONNX int8 (~120 MB) + its tokenizer.
Needs the export packages (requirements-export.txt) only for this run; the service itself runs without torch.

    python export_model.py /opt/willy/models
"""
import os
import sys

out = sys.argv[1] if len(sys.argv) > 1 else "/opt/willy/models"
os.makedirs(out, exist_ok=True)
from txtai.pipeline import HFOnnx  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

name = "intfloat/multilingual-e5-small"
HFOnnx()(name, task="pooling", output=os.path.join(out, "e5.onnx"), quantize=True)
AutoTokenizer.from_pretrained(name).save_pretrained(os.path.join(out, "tok"))
print("model saved to", out)
