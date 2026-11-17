"""Prediction service interface and Version 1 unconfigured placeholder."""

from datetime import datetime, timezone
from typing import Protocol

from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionStatus,
    PropertyFeatures,
)


class RegressionModelProtocol(Protocol):
    """Protocol for future scikit-learn Multiple Linear Regression models loaded via joblib."""

    def predict(self, X: list[list[float]]) -> list[float]:
        """Return predicted prices in INR for the provided 4-feature vectors."""


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
                property_id=request.property_id,
                predicted_price_inr=None,
                currency="INR",
                model_version=None,
                timestamp=timestamp,
                message=(
                    "Prediction model is not configured yet. "
                    "Train and configure the Multiple Linear Regression model to generate price estimates."
                ),
            )

        features = PropertyFeatures(
            area_sqft=request.area_sqft,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            age_years=request.age_years,
        )
        feature_vector = [
            [
                float(features.area_sqft),
                float(features.bedrooms),
                float(features.bathrooms),
                float(features.age_years),
            ]
        ]
        prediction = float(self._model.predict(feature_vector)[0])

        return PredictionResponse(
            status=PredictionStatus.SUCCESS,
            property_id=request.property_id,
            predicted_price_inr=round(prediction, 2),
            currency="INR",
            model_version=self._model_version,
            timestamp=timestamp,
            message="House price prediction generated successfully.",
        )


def predict_price(
    features: PropertyFeatures,
    property_id: str,
    service: PredictionService | None = None,
) -> PredictionResponse:
    """Convenience function matching predict_price(features) -> prediction_result interface."""
    active_service = service or PredictionService()
    request = PredictionRequest(
        property_id=property_id,
        area_sqft=features.area_sqft,
        bedrooms=features.bedrooms,
        bathrooms=features.bathrooms,
        age_years=features.age_years,
    )
    return active_service.predict_price(request)
