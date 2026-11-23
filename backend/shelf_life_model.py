from pathlib import Path

import joblib
import pandas as pd

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "shelf_life_rf.joblib"
)

SUPPORTED_FRUITS = {"apple", "banana"}
SUPPORTED_STORAGE = {"room", "shade", "sun"}

_model = None


def load_shelf_life_model():
    global _model

    if _model is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Shelf-life model not found: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def predict_remaining_days(
    produce_type: str,
    storage: str,
    temperature: float,
    storage_days: float,
):
    produce_type = produce_type.lower().strip()
    storage = storage.lower().strip()

    if produce_type not in SUPPORTED_FRUITS:
        return None

    if storage not in SUPPORTED_STORAGE:
        return None

    if not (-20 <= temperature <= 60):
        return None

    if storage_days < 0:
        return None

    model = load_shelf_life_model()

    features = pd.DataFrame([
        {
            "class": produce_type,
            "storage": storage,
            "ambient_temp_c": temperature,
            "elapsed_hours": storage_days * 24,
        }
    ])

    prediction = float(model.predict(features)[0])

    return {
        "predicted_remaining_days": round(
            max(0.0, prediction), 1
        ),
        "estimation_method": "random_forest_fruitlife",
        "shelf_life_model_status": "experimental",
        "validated": False,
        "prediction_target": (
            "Approximate days until FruitLife spoilage stage 3"
        ),
        "disclaimer": (
            "Experimental model trained on FruitLife observations. "
            "Not validated for food safety or general real-world "
            "shelf-life prediction. Humidity and visual freshness "
            "scores are not inputs to this regression model."
        ),
    }
