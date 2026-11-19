"""Load and run the Bengaluru house-price regression pipeline."""

from collections.abc import Sequence
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Protocol
import warnings

import joblib
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.utils.validation import check_is_fitted

from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionStatus,
)

MODEL_FEATURES = ("location", "total_sqft", "bhk", "bath")
RUPEES_PER_LAKH = 100_000


class RegressionModelProtocol(Protocol):
    """Interface of the fitted regression pipeline."""

    def predict(self, X: pd.DataFrame) -> Sequence[float]:
        """Return predicted prices in lakhs of rupees."""


def utc_timestamp_iso() -> str:
    """Return current UTC ISO-8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PredictionService:
    """Encapsulates house price prediction using an injected or startup-loaded ML model."""

    def __init__(
        self,
        model: RegressionModelProtocol | None = None,
        model_version: str | None = None,
    ) -> None:
        self._model = model
        self._model_version = model_version

    @classmethod
    def from_artifact(cls, path: str | None, version: str | None = None) -> "PredictionService":
        """Load a deployment-provided artifact once when the app starts."""
        if path is None:
            return cls()

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                model = joblib.load(Path(path))
            check_is_fitted(model)
            if not callable(getattr(model, "predict", None)) or tuple(
                getattr(model, "feature_names_in_", ())
            ) != MODEL_FEATURES:
                raise ValueError(f"Expected a fitted predictor with columns {MODEL_FEATURES}.")
        except Exception as exc:
            raise RuntimeError(f"Could not load prediction model from MODEL_PATH '{path}': {exc}") from exc

        return cls(model=model, model_version=version)

    @property
    def is_model_configured(self) -> bool:
        """Whether a trained regression model is currently loaded in memory."""
        return self._model is not None

    @property
    def model_version(self) -> str | None:
        """Configured model version identifier, if loaded."""
        return self._model_version if self._model is not None else None

    def predict_price(self, request: PredictionRequest) -> PredictionResponse:
        """Run prediction against the configured model, or return MODEL_NOT_CONFIGURED."""
        timestamp = utc_timestamp_iso()

        if self._model is None:
            return PredictionResponse(
                status=PredictionStatus.MODEL_NOT_CONFIGURED,
                location=request.location,
                predicted_price_inr=None,
                currency="INR",
                model_version=None,
                timestamp=timestamp,
                message=(
                    "Prediction model is not configured yet. "
                    "Train and configure the Multiple Linear Regression model to generate price estimates."
                ),
            )

        features = pd.DataFrame(
            [(request.location, request.area_sqft, request.bedrooms, request.bathrooms)],
            columns=MODEL_FEATURES,
        )
        price_inr = float(self._model.predict(features)[0]) * RUPEES_PER_LAKH
        if not math.isfinite(price_inr):
            raise RuntimeError("Prediction model returned a non-finite price.")

        return PredictionResponse(
            status=PredictionStatus.SUCCESS,
            location=request.location,
            predicted_price_inr=round(price_inr, 2),
            currency="INR",
            model_version=self._model_version,
            timestamp=timestamp,
            message="House price prediction generated successfully.",
        )
