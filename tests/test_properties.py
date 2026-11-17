"""Unit tests for PropertyService and property identifier validation."""

from pathlib import Path
import pytest

from app.config import DEFAULT_DATA_FILE
from app.schemas import PropertyFeatures
from app.services.prediction_service import PredictionService, predict_price
from app.services.property_service import (
    InvalidPropertyIdError,
    PropertyDataError,
    PropertyService,
    ResourceNotFoundError,
)


def test_list_cities_returns_city_a() -> None:
    service = PropertyService(DEFAULT_DATA_FILE)
    cities = service.list_cities()
    assert len(cities) == 1
    assert cities[0].id == "city-a"
    assert cities[0].name == "City A"


def test_list_localities_returns_local_1() -> None:
    service = PropertyService(DEFAULT_DATA_FILE)
    localities = service.list_localities("city-a")
    assert len(localities) == 1
    assert localities[0].id == "local-1"
    assert localities[0].name == "Local 1"


def test_list_and_get_all_ten_properties_a1_through_a10() -> None:
    service = PropertyService(DEFAULT_DATA_FILE)
    summaries = service.list_properties("local-1")
    ids = [item.id for item in summaries]
    assert ids == [f"A{i}" for i in range(1, 11)]

    for prop_id in ids:
        detail = service.get_property(prop_id)
        assert detail.id == prop_id
        assert detail.city_name == "City A"
        assert detail.locality_name == "Local 1"
        assert detail.features.area_sqft > 0
        assert detail.features.bedrooms >= 1
        assert detail.features.bathrooms >= 1
        assert detail.features.age_years >= 0


@pytest.mark.parametrize("bad_id", ["INVALID", "A0", "A11", "a1", "1A", "AA1", ""])
def test_invalid_property_identifier_format_raises_error(bad_id: str) -> None:
    service = PropertyService(DEFAULT_DATA_FILE)
    with pytest.raises(InvalidPropertyIdError):
        service.get_property(bad_id)


@pytest.mark.parametrize("missing_id", ["B1", "B10", "Z10"])
def test_valid_format_missing_property_raises_not_found(missing_id: str) -> None:
    service = PropertyService(DEFAULT_DATA_FILE)
    with pytest.raises(ResourceNotFoundError):
        service.get_property(missing_id)


def test_missing_data_file_raises_meaningful_startup_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_properties.json"
    with pytest.raises(PropertyDataError, match="Property data file not found"):
        PropertyService(missing_path)


def test_prediction_service_returns_model_not_configured_by_default() -> None:
    service = PredictionService()
    features = PropertyFeatures(area_sqft=1200, bedrooms=2, bathrooms=2, age_years=0)
    result = predict_price(features=features, property_id="A1", service=service)
    assert result.status.value == "MODEL_NOT_CONFIGURED"
    assert result.predicted_price_inr is None
    assert result.model_version is None
    assert result.property_id == "A1"
    assert result.timestamp.endswith("Z")
