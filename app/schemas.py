"""Pydantic schemas for API requests, responses, and domain entities."""

from enum import Enum
import math
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROPERTY_ID_PATTERN = re.compile(r"^[A-Z](?:10|[1-9])$")


def validate_property_id_format(value: str) -> str:
    """Validate property identifier matches [A-Z][1-10], e.g. A1 through Z10."""
    cleaned = value.strip()
    if not PROPERTY_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "Invalid property identifier. Expected format [A-Z][1-10], such as A1 through A10."
        )
    return cleaned


class PredictionStatus(str, Enum):
    """Explicit prediction outcome status."""

    SUCCESS = "SUCCESS"
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"


class HealthResponse(BaseModel):
    """Service health payload."""

    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["house-price-predictor"])
    environment: str = Field(..., examples=["development"])
    model_configured: bool
    model_version: Optional[str] = None
    timestamp: str


class CityItem(BaseModel):
    """City option returned to selectors."""

    id: str
    name: str


class CityListResponse(BaseModel):
    """List of supported cities."""

    cities: list[CityItem]


class LocalityItem(BaseModel):
    """Locality option within a city."""

    id: str
    name: str
    city_id: str


class LocalityListResponse(BaseModel):
    """List of localities for a given city."""

    city_id: str
    localities: list[LocalityItem]


class PropertySummary(BaseModel):
    """Lightweight property option for selector dropdowns."""

    id: str
    label: str
    city_id: str
    locality_id: str


class PropertySummaryListResponse(BaseModel):
    """List of properties for a given locality."""

    locality_id: str
    properties: list[PropertySummary]


class PropertyFeatures(BaseModel):
    """Four numerical input features for house price prediction."""

    model_config = ConfigDict(extra="forbid")

    area_sqft: float = Field(..., gt=0, le=100000, description="Floor area in square feet")
    bedrooms: int = Field(..., ge=1, le=50, description="Number of bedrooms")
    bathrooms: int = Field(..., ge=1, le=50, description="Number of bathrooms")
    age_years: float = Field(..., ge=0, le=200, description="Property age in years")

    @field_validator("area_sqft", "age_years")
    @classmethod
    def check_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Value must be a finite number.")
        return value


class PropertyDetail(BaseModel):
    """Full property record with location metadata and features."""

    id: str
    city_id: str
    city_name: str
    locality_id: str
    locality_name: str
    features: PropertyFeatures


class PredictionRequest(BaseModel):
    """Request payload for POST /api/predict."""

    model_config = ConfigDict(extra="forbid")

    property_id: str = Field(..., description="Property identifier in format [A-Z][1-10]")
    area_sqft: float = Field(..., gt=0, le=100000, description="Floor area in square feet (positive)")
    bedrooms: int = Field(..., ge=1, le=50, description="Number of bedrooms (at least 1)")
    bathrooms: int = Field(..., ge=1, le=50, description="Number of bathrooms (at least 1)")
    age_years: float = Field(..., ge=0, le=200, description="Property age in years (nonnegative)")

    @field_validator("property_id")
    @classmethod
    def validate_property_id(cls, value: str) -> str:
        return validate_property_id_format(value)

    @field_validator("area_sqft", "age_years")
    @classmethod
    def check_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Value must be a finite number.")
        return value


class PredictionResponse(BaseModel):
    """Structured prediction response for configured and unconfigured model states."""

    status: PredictionStatus
    property_id: str
    predicted_price_inr: Optional[float] = None
    currency: str = "INR"
    model_version: Optional[str] = None
    timestamp: str
    message: str
