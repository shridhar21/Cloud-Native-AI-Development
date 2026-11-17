"""Property data-access service backed by JSON storage."""

import json
from pathlib import Path
from typing import Any

from app.schemas import (
    CityItem,
    LocalityItem,
    PropertyDetail,
    PropertyFeatures,
    PropertySummary,
    validate_property_id_format,
)


class PropertyDataError(RuntimeError):
    """Raised when the property data store cannot be loaded or parsed."""


class ResourceNotFoundError(LookupError):
    """Raised when a requested city, locality, or property does not exist."""


class InvalidPropertyIdError(ValueError):
    """Raised when a property identifier fails [A-Z][1-10] validation."""


class PropertyService:
    """Data-access layer for cities, localities, and synthetic demonstration properties."""

    def __init__(self, data_file_path: Path) -> None:
        self._data_file_path = data_file_path
        self._cities: dict[str, CityItem] = {}
        self._localities: dict[str, LocalityItem] = {}
        self._properties: dict[str, PropertyDetail] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not self._data_file_path.exists():
            raise PropertyDataError(
                f"Property data file not found at '{self._data_file_path}'. "
                "Set DATA_FILE_PATH or ensure app/data/properties.json exists."
            )

        try:
            raw_text = self._data_file_path.read_text(encoding="utf-8")
            payload: dict[str, Any] = json.loads(raw_text)
        except OSError as exc:
            raise PropertyDataError(
                f"Unable to read property data file '{self._data_file_path}': {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise PropertyDataError(
                f"Malformed JSON in property data file '{self._data_file_path}': {exc}"
            ) from exc

        try:
            cities = [CityItem(**item) for item in payload.get("cities", [])]
            self._cities = {city.id: city for city in cities}

            localities = [LocalityItem(**item) for item in payload.get("localities", [])]
            self._localities = {loc.id: loc for loc in localities}

            properties: dict[str, PropertyDetail] = {}
            for raw_prop in payload.get("properties", []):
                prop_id = validate_property_id_format(str(raw_prop["id"]))
                city_id = str(raw_prop["city_id"])
                locality_id = str(raw_prop["locality_id"])

                if city_id not in self._cities:
                    raise PropertyDataError(
                        f"Property '{prop_id}' references unknown city_id '{city_id}'."
                    )
                if locality_id not in self._localities:
                    raise PropertyDataError(
                        f"Property '{prop_id}' references unknown locality_id '{locality_id}'."
                    )

                city = self._cities[city_id]
                locality = self._localities[locality_id]
                if locality.city_id != city.id:
                    raise PropertyDataError(
                        f"Locality '{locality.id}' does not belong to city '{city.id}'."
                    )

                features = PropertyFeatures(**raw_prop["features"])
                properties[prop_id] = PropertyDetail(
                    id=prop_id,
                    city_id=city.id,
                    city_name=city.name,
                    locality_id=locality.id,
                    locality_name=locality.name,
                    features=features,
                )

            self._properties = properties
        except (KeyError, TypeError, ValueError) as exc:
            raise PropertyDataError(
                f"Invalid schema in property data file '{self._data_file_path}': {exc}"
            ) from exc

    def list_cities(self) -> list[CityItem]:
        """Return all available cities."""
        return list(self._cities.values())

    def list_localities(self, city_id: str) -> list[LocalityItem]:
        """Return localities belonging to the given city."""
        if city_id not in self._cities:
            raise ResourceNotFoundError(f"City '{city_id}' not found.")
        return [loc for loc in self._localities.values() if loc.city_id == city_id]

    def list_properties(self, locality_id: str) -> list[PropertySummary]:
        """Return property summaries belonging to the given locality."""
        if locality_id not in self._localities:
            raise ResourceNotFoundError(f"Locality '{locality_id}' not found.")
        return [
            PropertySummary(
                id=prop.id,
                label=prop.id,
                city_id=prop.city_id,
                locality_id=prop.locality_id,
            )
            for prop in self._properties.values()
            if prop.locality_id == locality_id
        ]

    def get_property(self, property_id: str) -> PropertyDetail:
        """Validate property_id format and return the property record."""
        try:
            normalized_id = validate_property_id_format(property_id)
        except ValueError as exc:
            raise InvalidPropertyIdError(str(exc)) from exc

        if normalized_id not in self._properties:
            raise ResourceNotFoundError(f"Property '{normalized_id}' not found.")

        return self._properties[normalized_id]
