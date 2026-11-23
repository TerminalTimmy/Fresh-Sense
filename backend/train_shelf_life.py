from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fruitlife"
MODELS = ROOT / "backend" / "models"
MODELS.mkdir(exist_ok=True)

manifest = pd.read_csv(DATA / "manifest_v2_b6consensus.csv")
events = pd.read_csv(DATA / "stage_event_intervals.csv")
environment = pd.read_csv(DATA / "environmental_covariates.csv")

# Only use observed, consensus stage-3 transitions.
events = events[
    (events["threshold"] == 3)
    & (events["stage_source"] == "consensus")
    & (events["censoring"] == "interval")
].copy()

events["event_midpoint_hours"] = (
    events["L"] + events["U"]
) / 2

# Join each observation with its specimen's observed event.
data = manifest.merge(
    events[["specimen_id", "event_midpoint_hours", "L", "U"]],
    on="specimen_id",
    how="inner",
    validate="many_to_one",
)

data = data.merge(
    environment[["shot_id", "ambient_temp_c"]],
    on="shot_id",
    how="left",
    validate="one_to_one",
)

# Exclude observations at/after the earliest possible event time.
data = data[data["elapsed_hours"] < data["L"]].copy()

data["remaining_days"] = (
    data["event_midpoint_hours"] - data["elapsed_hours"]
) / 24

features = [
    "class",
    "storage",
    "ambient_temp_c",
    "elapsed_hours",
]

data = data.dropna(subset=features + ["remaining_days"])
data = data[data["remaining_days"] > 0].copy()

X = data[features]
y = data["remaining_days"]
groups = data["specimen_id"]

print("=== TRAINING DATA ===")
print("Observations:", len(data))
print("Independent specimens:", groups.nunique())
print("Fruit types:", sorted(data["class"].unique()))
print("Target range (days):", round(y.min(), 2), "to", round(y.max(), 2))

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            ["class", "storage"],
        ),
        (
            "numeric",
            "passthrough",
            ["ambient_temp_c", "elapsed_hours"],
        ),
    ]
)

def make_model():
    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=200,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )),
    ])

# Grouped evaluation prevents images of the same fruit
# appearing in both training and test sets.
cv = GroupKFold(n_splits=6)
predictions = np.zeros(len(data))

for fold, (train_idx, test_idx) in enumerate(
    cv.split(X, y, groups), start=1
):
    model = make_model()
    model.fit(X.iloc[train_idx], y.iloc[train_idx])
    predictions[test_idx] = model.predict(X.iloc[test_idx])

    fold_mae = mean_absolute_error(
        y.iloc[test_idx], predictions[test_idx]
    )
    print(f"Fold {fold} MAE: {fold_mae:.3f} days")

mae = mean_absolute_error(y, predictions)
rmse = np.sqrt(mean_squared_error(y, predictions))
r2 = r2_score(y, predictions)

print("\n=== GROUPED CROSS-VALIDATION ===")
print(f"MAE:  {mae:.3f} days")
print(f"RMSE: {rmse:.3f} days")
print(f"R2:   {r2:.3f}")

# Fit a final research model using all available observations.
final_model = make_model()
final_model.fit(X, y)

model_path = MODELS / "shelf_life_rf.joblib"
joblib.dump(final_model, model_path)

metrics = {
    "dataset": "FruitLife v1.5",
    "target": "Approximate days until spoilage stage 3",
    "target_method": "Midpoint of observed event interval",
    "evaluation": "6-fold GroupKFold by physical specimen",
    "mae_days": float(mae),
    "rmse_days": float(rmse),
    "r2": float(r2),
    "observations": int(len(data)),
    "independent_specimens": int(groups.nunique()),
    "features": features,
    "limitations": [
        "Exploratory research model, not food-safety validated",
        "Only six independent specimens per fruit type",
        "Humidity unavailable in training data",
        "Temperature is reconstructed or fixed setpoint",
        "Stage-3 transition time approximated by interval midpoint",
        "Oranges not represented in the training dataset",
        "Visual MobileNetV2 scores are not yet included",
    ],
}

metrics_path = MODELS / "shelf_life_metrics.json"
metrics_path.write_text(json.dumps(metrics, indent=2))

print("\n=== SAVED ===")
print(model_path)
print(metrics_path)
print("\nTraining completed.")
