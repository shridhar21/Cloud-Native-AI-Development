"""End-to-end FastAPI endpoint tests using TestClient."""

from fastapi.testclient import TestClient
import pytest

from app.main import create_app

client = TestClient(create_app())


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "house-price-predictor"
    assert data["model_configured"] is False
    assert data["model_version"] is None
    assert "timestamp" in data


def test_list_cities_endpoint() -> None:
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert data["cities"] == [{"id": "city-a", "name": "City A"}]


def test_list_localities_for_city_a() -> None:
    response = client.get("/api/cities/city-a/localities")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "city-a"
    assert data["localities"] == [{"id": "local-1", "name": "Local 1", "city_id": "city-a"}]


def test_list_localities_unknown_city_returns_404() -> None:
    response = client.get("/api/cities/city-z/localities")
    assert response.status_code == 404


def test_list_properties_for_local_1() -> None:
    response = client.get("/api/localities/local-1/properties")
    assert response.status_code == 200
    data = response.json()
    assert data["locality_id"] == "local-1"
    assert [item["id"] for item in data["properties"]] == [f"A{i}" for i in range(1, 11)]


@pytest.mark.parametrize("property_id", [f"A{i}" for i in range(1, 11)])
def test_retrieve_each_property_a1_to_a10(property_id: str) -> None:
    response = client.get(f"/api/properties/{property_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == property_id
    assert data["city_id"] == "city-a"
    assert data["locality_id"] == "local-1"
    assert set(data["features"].keys()) == {"area_sqft", "bedrooms", "bathrooms", "age_years"}


@pytest.mark.parametrize("invalid_id", ["A0", "A11", "a1", "INVALID", "99"])
def test_get_property_invalid_identifier_returns_400(invalid_id: str) -> None:
    response = client.get(f"/api/properties/{invalid_id}")
    assert response.status_code == 400


def test_get_property_valid_format_but_missing_returns_404() -> None:
    response = client.get("/api/properties/B1")
    assert response.status_code == 404


def test_predict_when_no_model_configured() -> None:
    response = client.post(
        "/api/predict",
        json={
            "property_id": "A1",
            "area_sqft": 1250,
            "bedrooms": 3,
            "bathrooms": 2,
            "age_years": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "MODEL_NOT_CONFIGURED"
    assert data["property_id"] == "A1"
    assert data["predicted_price_inr"] is None
    assert data["currency"] == "INR"
    assert data["model_version"] is None
    assert data["timestamp"].endswith("Z")
    assert "not configured" in data["message"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"property_id": "A1", "area_sqft": 0, "bedrooms": 2, "bathrooms": 1, "age_years": 5},
        {"property_id": "A1", "area_sqft": -500, "bedrooms": 2, "bathrooms": 1, "age_years": 5},
        {"property_id": "A1", "area_sqft": 1000, "bedrooms": 0, "bathrooms": 1, "age_years": 5},
        {"property_id": "A1", "area_sqft": 1000, "bedrooms": 2, "bathrooms": 0, "age_years": 5},
        {"property_id": "A1", "area_sqft": 1000, "bedrooms": 2, "bathrooms": 1, "age_years": -1},
        {"property_id": "A11", "area_sqft": 1000, "bedrooms": 2, "bathrooms": 1, "age_years": 5},
    ],
)
def test_predict_feature_and_identifier_validation_returns_422(payload: dict) -> None:
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_unknown_property_returns_404() -> None:
    response = client.post(
        "/api/predict",
        json={
            "property_id": "B1",
            "area_sqft": 1200,
            "bedrooms": 2,
            "bathrooms": 2,
            "age_years": 4,
        },
    )
    assert response.status_code == 404
