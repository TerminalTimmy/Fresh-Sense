# ── Stage 1: Convert PyTorch model to ONNX ──────────────────────────
FROM python:3.11-slim AS converter

WORKDIR /build

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir onnx

COPY backend/models/vision_model.pth /build/vision_model.pth
COPY convert_to_onnx.py /build/convert_to_onnx.py

# Run the conversion script adapted for Docker paths
RUN python -c "\
import torch, torch.nn as nn, os;\
from torchvision.models import mobilenet_v2;\
cp = torch.load('/build/vision_model.pth', map_location='cpu', weights_only=True);\
m = mobilenet_v2(weights=None);\
m.classifier[1] = nn.Linear(m.last_channel, 2);\
m.load_state_dict(cp['model_state_dict']);\
m.eval();\
torch.onnx.export(m, torch.randn(1,3,224,224), '/build/vision_model.onnx',\
  input_names=['input'], output_names=['output'],\
  dynamic_axes={'input':{0:'batch'},'output':{0:'batch'}}, opset_version=17);\
print('ONNX model size:', round(os.path.getsize('/build/vision_model.onnx')/1024/1024,1), 'MB')"


# ── Stage 2: Lightweight production image (no PyTorch) ──────────────
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

COPY backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend

# Replace the .pth model with the converted .onnx model
COPY --from=converter /build/vision_model.onnx /app/backend/models/vision_model.onnx

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
