"""Thin FastAPI route handlers delegating business logic to application services."""

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas import (
    CityListResponse,
    HealthResponse,
    LocalityListResponse,
    PredictionRequest,
    PredictionResponse,
    PropertyDetail,
    PropertySummaryListResponse,
)
from app.services.prediction_service import PredictionService, utc_timestamp_iso
from app.services.property_service import (
    InvalidPropertyIdError,
    PropertyService,
    ResourceNotFoundError,
)

router = APIRouter(prefix="/api", tags=["house-price-predictor"])


def _get_property_service(request: Request) -> PropertyService:
    return request.app.state.property_service


def _get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    """Return service health and model configuration readiness."""
    settings = request.app.state.settings
    prediction_service = _get_prediction_service(request)
    return HealthResponse(
        status="ok",
        service="house-price-predictor",
        environment=settings.environment,
        model_configured=prediction_service.is_model_configured,
        model_version=prediction_service.model_version,
        timestamp=utc_timestamp_iso(),
    )


@router.get("/cities", response_model=CityListResponse)
def list_cities(request: Request) -> CityListResponse:
    """List available cities."""
    property_service = _get_property_service(request)
    return CityListResponse(cities=property_service.list_cities())


@router.get("/cities/{city_id}/localities", response_model=LocalityListResponse)
def list_localities(city_id: str, request: Request) -> LocalityListResponse:
    """List localities within a given city."""
    property_service = _get_property_service(request)
    try:
        localities = property_service.list_localities(city_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LocalityListResponse(city_id=city_id, localities=localities)


@router.get("/localities/{locality_id}/properties", response_model=PropertySummaryListResponse)
def list_properties(locality_id: str, request: Request) -> PropertySummaryListResponse:
    """List properties within a given locality."""
    property_service = _get_property_service(request)
    try:
        properties = property_service.list_properties(locality_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PropertySummaryListResponse(locality_id=locality_id, properties=properties)


@router.get("/properties/{property_id}", response_model=PropertyDetail)
def get_property(property_id: str, request: Request) -> PropertyDetail:
    """Retrieve details and four numerical features for a specific property."""
    property_service = _get_property_service(request)
    try:
        return property_service.get_property(property_id)
    except InvalidPropertyIdError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/predict", response_model=PredictionResponse)
def predict_house_price(payload: PredictionRequest, request: Request) -> PredictionResponse:
    """Validate property existence and invoke the prediction service."""
    property_service = _get_property_service(request)
    prediction_service = _get_prediction_service(request)

    try:
        property_service.get_property(payload.property_id)
    except InvalidPropertyIdError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return prediction_service.predict_price(payload)
