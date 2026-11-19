
from pathlib import Path
from datetime import datetime, timezone
import json

import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# 1. File locations
DATASET_PATH = Path(
    "/home/ubuntu/data/house_dataset/Bengaluru_House_Data.csv"
)
ARTIFACT_DIR = Path("/home/ubuntu/artifacts/house-price/v1")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# 2. Convert square-footage values into numbers
def parse_sqft(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        parts = str(value).split("-")
        if len(parts) == 2:
            try:
                return (float(parts[0]) + float(parts[1])) / 2
            except ValueError:
                pass
        return np.nan


# 3. Load and clean the dataset
df = pd.read_csv(DATASET_PATH)

print("Original rows:", len(df))

df["total_sqft"] = df["total_sqft"].apply(parse_sqft)
df["bhk"] = pd.to_numeric(
    df["size"].astype(str).str.extract(r"(\d+)")[0],
    errors="coerce"
)
df["bath"] = pd.to_numeric(df["bath"], errors="coerce")
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["location"] = df["location"].str.strip()

df = df.dropna(
    subset=["location", "total_sqft", "bhk", "bath", "price"]
)

# Basic data-quality filters
df = df[
    (df["total_sqft"] > 0) &
    (df["bhk"] >= 1) &
    (df["bhk"] <= 10) &
    (df["bath"] >= 1) &
    (df["bath"] <= 10) &
    (df["price"] > 0) &
    (df["total_sqft"] / df["bhk"] >= 250)
]

print("Cleaned rows:", len(df))


# 4. Select input features and prediction target
features = ["location", "total_sqft", "bhk", "bath"]

X = df[features]
y = df["price"]  # Price in lakhs


# 5. Split data: 80% training, 20% testing
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)


# 6. Preprocess locations and train the regression model
preprocessor = ColumnTransformer([
    ("location", OneHotEncoder(
        handle_unknown="infrequent_if_exist",
        max_categories=41,
        sparse_output=False
    ), ["location"]),
    ("numeric", "passthrough", ["total_sqft", "bhk", "bath"])
])

model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", LinearRegression())
])

model.fit(X_train, y_train)


# 7. Evaluate on unseen test data
predictions = model.predict(X_test)

metrics = {
    "mae_lakh": float(mean_absolute_error(y_test, predictions)),
    "rmse_lakh": float(np.sqrt(mean_squared_error(y_test, predictions))),
    "r2": float(r2_score(y_test, predictions))
}

print("Evaluation metrics:", metrics)


# 8. Save the model and evaluation artifacts
joblib.dump(model, ARTIFACT_DIR / "model.joblib")

metadata = {
    "model_version": "v1",
    "algorithm": "LinearRegression",
    "trained_at_utc": datetime.now(timezone.utc).isoformat(),
    "training_rows": len(X_train),
    "testing_rows": len(X_test),
    "sklearn_version": sklearn.__version__,
    "dataset": str(DATASET_PATH)
}

feature_schema = {
    "inputs": {
        "location": "string",
        "total_sqft": "number (square feet)",
        "bhk": "integer",
        "bath": "number"
    },
    "target": "price in INR lakhs"
}

for filename, content in [
    ("metrics.json", metrics),
    ("metadata.json", metadata),
    ("feature_schema.json", feature_schema)
]:
    with open(ARTIFACT_DIR / filename, "w") as f:
        json.dump(content, f, indent=4)

print("Training completed successfully!")
print("Artifacts saved to:", ARTIFACT_DIR)
