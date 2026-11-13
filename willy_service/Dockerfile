# Willy GRAM — the meaning search (txtai + multilingual-e5-small, ONNX int8). No external API at run time.
# Stage 1 downloads the model once and exports it to ONNX int8; stage 2 runs it without torch (~120 MB model).
FROM python:3.11-slim AS export
RUN pip install --no-cache-dir "txtai[pipeline]==9.*" torch --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir onnx onnxruntime
RUN python - <<'PY'
from txtai.pipeline import HFOnnx
from transformers import AutoTokenizer
HFOnnx()("intfloat/multilingual-e5-small", task="pooling", output="/models/e5.onnx", quantize=True)
AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small").save_pretrained("/models/tok")
PY

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=export /models /models
COPY app.py .
ENV WILLY_DATA=/data OMP_NUM_THREADS=1
VOLUME ["/data"]
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8090/health')"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1"]
