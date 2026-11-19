
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from torchvision.models import mobilenet_v2
from torchvision import transforms
import torch
import torch.nn as nn
import io
import os
from backend.environment import estimate_storage_demo

app = FastAPI(
    title="Shelf Life Prediction API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

device = torch.device("cpu")

MODEL_PATH = os.getenv(
    "VISION_MODEL_PATH",
    "backend/models/vision_model.pth"
)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=device,
    weights_only=True
)

model = mobilenet_v2(weights=None)
model.classifier[1] = nn.Linear(
    model.last_channel, 2
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model.eval()

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

SUPPORTED_PRODUCE = {"apple", "banana", "orange"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "vision_model_loaded": True
    }

@app.post("/predict")
async def predict(
    image: UploadFile = File(...),
    temperature: float = Form(...),
    humidity: float = Form(...),
    storage_days: float = Form(...),
    produce_type: str = Form(...)
):
    produce_type = produce_type.lower().strip()

    if produce_type not in SUPPORTED_PRODUCE:
        raise HTTPException(
            status_code=422,
            detail="Supported produce: apple, banana, orange"
        )

    if not (-20 <= temperature <= 60):
        raise HTTPException(
            status_code=422,
            detail="Temperature must be between -20 and 60 C"
        )

    if not (0 <= humidity <= 100):
        raise HTTPException(
            status_code=422,
            detail="Humidity must be between 0 and 100%"
        )

    if storage_days < 0:
        raise HTTPException(
            status_code=422,
            detail="Storage days cannot be negative"
        )

    content = await image.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 10 MB limit"
        )

    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        tensor = transform(img).unsqueeze(0)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="Invalid image file"
        )

    with torch.inference_mode():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)
        freshness_score = float(probabilities[0, 1])

    freshness_status = (
        "fresh" if freshness_score >= 0.5 else "rotten"
    )

    environment_result = estimate_storage_demo(
        produce_type=produce_type,
        freshness_score=freshness_score,
        temperature=temperature,
        humidity=humidity,
        storage_days=storage_days
    )



    return {
        "produce_type": produce_type,
        "freshness_score": round(freshness_score, 4),
        "freshness_status": freshness_status,
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "storage_days": storage_days,
        "predicted_remaining_days": None,
        "illustrative_remaining_days": (
            environment_result["illustrative_remaining_days"]
        ),
        "storage_reference": (
            environment_result["storage_reference"]
        ),
        "estimation_method": (
            environment_result["estimation_method"]
        ),
        "shelf_life_model_status": "demo_only",
        "validated": False,
        "recommendations": [
            "The remaining-days estimate is illustrative only.",
            "Do not use this estimate to determine food safety.",
            "Inspect produce for signs of spoilage."
        ],
        "disclaimer": environment_result["disclaimer"]
    }
