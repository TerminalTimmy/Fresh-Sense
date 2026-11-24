
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
import numpy as np
import onnxruntime as ort
import io
import os
from backend.shelf_life_model import predict_remaining_days
from backend.environment import (
    estimate_storage_demo,
    get_storage_recommendations
)

# Register HEIF/HEIC support so iPhones' native format is accepted.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

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

MODEL_PATH = os.getenv(
    "VISION_MODEL_PATH",
    "backend/models/vision_model.onnx"
)

session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CPUExecutionProvider"]
)
INPUT_NAME = session.get_inputs()[0].name

# ImageNet normalization constants
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_image(img: Image.Image) -> np.ndarray:
    """Replicate torchvision: Resize(256), CenterCrop(224), ToTensor, Normalize."""
    # Resize so shortest side = 256, preserve aspect ratio
    w, h = img.size
    if w < h:
        new_w = 256
        new_h = int(h * 256 / w)
    else:
        new_h = 256
        new_w = int(w * 256 / h)
    img = img.resize((new_w, new_h), Image.BILINEAR)

    # Center crop to 224x224
    w, h = img.size
    left = (w - 224) // 2
    top = (h - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))

    # Convert to float32 array [0, 1], then normalize
    arr = np.array(img, dtype=np.float32) / 255.0  # (224, 224, 3)
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD

    # HWC -> CHW, add batch dim
    arr = arr.transpose(2, 0, 1)  # (3, 224, 224)
    return arr[np.newaxis, ...]    # (1, 3, 224, 224)


def softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    return exp / np.sum(exp, axis=1, keepdims=True)


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
    produce_type: str = Form(...),
    storage_environment: str | None = Form(None)
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
        tensor = preprocess_image(img)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="Invalid image file"
        )

    logits = session.run(None, {INPUT_NAME: tensor})[0]
    probabilities = softmax(logits)
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

    regression_result = None

    if storage_environment is not None:
        storage_environment = storage_environment.lower().strip()

        if storage_environment not in {"room", "shade", "sun"}:
            raise HTTPException(
                status_code=422,
                detail="Storage environment must be room, shade, or sun"
            )

        regression_result = predict_remaining_days(
            produce_type=produce_type,
            storage=storage_environment,
            temperature=temperature,
            storage_days=storage_days,
        )

    return {
        "produce_type": produce_type,
        "freshness_score": round(freshness_score, 4),
        "freshness_status": freshness_status,
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "storage_days": storage_days,
        "predicted_remaining_days": (
            regression_result["predicted_remaining_days"]
            if regression_result else None
        ),
        "illustrative_remaining_days": (
            environment_result["illustrative_remaining_days"]
        ),
        "storage_reference": (
            environment_result["storage_reference"]
        ),
        "estimation_method": (
            regression_result["estimation_method"]
            if regression_result
            else environment_result["estimation_method"]
        ),
        "shelf_life_model_status": (
            "experimental" if regression_result else "demo_only"
        ),
        "prediction_target": (
            regression_result["prediction_target"]
            if regression_result else None
        ),
        "storage_environment": storage_environment,
        "validated": False,
        "recommendations": get_storage_recommendations(
            produce_type=produce_type,
            temperature=temperature,
            humidity=humidity,
            freshness_status=freshness_status
        ),
        "disclaimer": (
            regression_result["disclaimer"]
            if regression_result
            else environment_result["disclaimer"]
        )
    }
