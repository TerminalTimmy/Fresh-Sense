"""Convert the PyTorch MobileNetV2 model to ONNX format."""
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2

MODEL_PATH = "backend/models/vision_model.pth"
ONNX_PATH = "backend/models/vision_model.onnx"

device = torch.device("cpu")

# Load the original model
checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)

model = mobilenet_v2(weights=None)
model.classifier[1] = nn.Linear(model.last_channel, 2)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Create dummy input (batch=1, channels=3, 224x224)
dummy_input = torch.randn(1, 3, 224, 224)

# Export to ONNX
torch.onnx.export(
    model,
    dummy_input,
    ONNX_PATH,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=17,
)

print(f"Exported ONNX model to {ONNX_PATH}")

import os
size_mb = os.path.getsize(ONNX_PATH) / (1024 * 1024)
print(f"ONNX model size: {size_mb:.1f} MB")
