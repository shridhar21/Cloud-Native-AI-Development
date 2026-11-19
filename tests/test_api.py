"""End-to-end FastAPI endpoint tests using TestClient."""

from dataclasses import replace
from itertools import product

from fastapi.testclient import TestClient
import joblib
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.config import load_settings
from app.main import create_app

PREDICTION_INPUT = {
    "location": "Whitefield",
    "area_sqft": 1200,
    "bedrooms": 2,
    "bathrooms": 2,
}


@pytest.fixture(scope="module")
def client():
    settings = replace(load_settings(), model_path=None, model_version=None)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "house-price-predictor"
    assert data["model_configured"] is False
    assert data["model_version"] is None
    assert "timestamp" in data


def test_list_cities_endpoint(client) -> None:
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert data["cities"] == [{"id": "city-a", "name": "City A"}]


def test_list_localities_for_city_a(client) -> None:
    response = client.get("/api/cities/city-a/localities")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "city-a"
    assert data["localities"] == [{"id": "local-1", "name": "Local 1", "city_id": "city-a"}]


def test_list_localities_unknown_city_returns_404(client) -> None:
    response = client.get("/api/cities/city-z/localities")
    assert response.status_code == 404


def test_list_properties_for_local_1(client) -> None:
    response = client.get("/api/localities/local-1/properties")
    assert response.status_code == 200
    data = response.json()
    assert data["locality_id"] == "local-1"
    assert [item["id"] for item in data["properties"]] == [f"A{i}" for i in range(1, 11)]


@pytest.mark.parametrize("property_id", [f"A{i}" for i in range(1, 11)])
def test_retrieve_each_property_a1_to_a10(client, property_id: str) -> None:
    response = client.get(f"/api/properties/{property_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == property_id
    assert data["city_id"] == "city-a"
    assert data["locality_id"] == "local-1"
    assert set(data["features"].keys()) == {"area_sqft", "bedrooms", "bathrooms", "age_years"}


@pytest.mark.parametrize("invalid_id", ["A0", "A11", "a1", "INVALID", "99"])
def test_get_property_invalid_identifier_returns_400(client, invalid_id: str) -> None:
    response = client.get(f"/api/properties/{invalid_id}")
    assert response.status_code == 400


def test_get_property_valid_format_but_missing_returns_404(client) -> None:
    response = client.get("/api/properties/B1")
    assert response.status_code == 404


def test_predict_when_no_model_configured(client) -> None:
    response = client.post("/api/predict", json=PREDICTION_INPUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "MODEL_NOT_CONFIGURED"
    assert data["location"] == "Whitefield"
    assert data["predicted_price_inr"] is None
    assert data["currency"] == "INR"
    assert data["model_version"] is None
    assert data["timestamp"].endswith("Z")
    assert "not configured" in data["message"].lower()


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"area_sqft": 0},
        {"area_sqft": -500},
        {"bedrooms": 0},
        {"bathrooms": 0},
        {"location": "   "},
        {"location": "x" * 201},
        {"age_years": 5},
    ],
)
def test_predict_input_validation_returns_422(client, invalid_fields: dict) -> None:
    response = client.post("/api/predict", json={**PREDICTION_INPUT, **invalid_fields})
    assert response.status_code == 422


def test_predict_loads_pipeline_and_returns_rupees(tmp_path) -> None:
    rows = pd.DataFrame(
        list(product(["Whitefield", "Indiranagar"], [900, 1500], [2, 3], [1, 2])),
        columns=["location", "total_sqft", "bhk", "bath"],
    )
    targets = rows.total_sqft / 20 + 5 * rows.bhk + 3 * rows.bath + 20 * (rows.location == "Indiranagar")
    preprocessor = ColumnTransformer([
        ("location", OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=41,
                                   sparse_output=False), ["location"]),
        ("numeric", "passthrough", ["total_sqft", "bhk", "bath"]),
    ])
    model = Pipeline([("preprocessor", preprocessor), ("regressor", LinearRegression())])
    model.fit(rows, targets)
    artifact_path = tmp_path / "model.joblib"
    joblib.dump(model, artifact_path)
    settings = replace(load_settings(), model_path=str(artifact_path), model_version="test-v1")

    with TestClient(create_app(settings)) as configured_client:
        artifact_path.unlink()
        health = configured_client.get("/api/health").json()
        assert health["model_configured"] is True
        assert health["model_version"] == "test-v1"

        response = configured_client.post("/api/predict", json={**PREDICTION_INPUT, "location": " Whitefield "})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["location"] == "Whitefield"
        assert data["predicted_price_inr"] == 7_600_000
        assert data["model_version"] == "test-v1"


def test_configured_model_must_be_loadable(tmp_path) -> None:
    settings = replace(load_settings(), model_path=str(tmp_path / "missing.joblib"))
    with pytest.raises(RuntimeError, match="Could not load prediction model from MODEL_PATH"):
        with TestClient(create_app(settings)):
            pass
