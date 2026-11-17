# House Price Predictor (Version 1)

A simple, modular-monolith web application for estimating residential house prices in Indian Rupees (INR). Built with a **FastAPI** backend, **Vanilla HTML/CSS/JavaScript** frontend, synthetic JSON demonstration data, and a clean prediction-service boundary prepared for future **scikit-learn Multiple Linear Regression** integration.

## Scope (Version 1)

- **City**: `City A` (`city-a`)
- **Locality**: `Local 1` (`local-1`)
- **Properties**: `A1` through `A10` (identifiers validated against `[A-Z][1-10]`)
- **Features**:
  - `area_sqft` (positive float)
  - `bedrooms` (integer >= 1)
  - `bathrooms` (integer >= 1)
  - `age_years` (nonnegative float)
- **ML Model Status**: No model is trained or bundled in Version 1. Prediction requests return an explicit `MODEL_NOT_CONFIGURED` response rather than fabricating values.

---

## Project Structure

```text
house-price-predictor/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory & static frontend mount
│   ├── config.py                   # Environment-based configuration
│   ├── schemas.py                  # Pydantic request/response schemas & validators
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # Thin HTTP route handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── property_service.py     # JSON data-access layer
│   │   └── prediction_service.py   # Prediction interface (MODEL_NOT_CONFIGURED)
│   └── data/
│       └── properties.json         # Synthetic property records A1-A10
├── frontend/
│   ├── index.html                  # Single-page UI
│   ├── styles.css                  # Responsive minimal layout & typography
│   └── app.js                      # Fetch API client & validation
├── tests/
│   ├── __init__.py
│   ├── test_api.py                 # API endpoint & validation tests
│   └── test_properties.py          # Service & identifier unit tests
├── requirements.txt                # Pinned Python dependencies
├── .gitignore
└── README.md
```

---

## Component Architecture

1. **Frontend Presentation (`frontend/`)**
   - Pure HTML, CSS, and Vanilla JavaScript using the browser `fetch` API.
   - Populates City, Locality, and Property dropdowns directly from backend endpoints.
   - Loads the selected property's four numerical attributes into editable inputs, validates user edits, and renders loading, error, `MODEL_NOT_CONFIGURED`, and INR price result states.

2. **API Routing (`app/api/routes.py`)**
   - Thin FastAPI handlers prefixed with `/api`.
   - Delegates input validation to Pydantic (`app/schemas.py`), data retrieval to `PropertyService`, and prediction execution to `PredictionService`.

3. **Property Data Access (`app/services/property_service.py`)**
   - Loads `app/data/properties.json` at startup and validates schema integrity and `[A-Z][1-10]` property identifiers.
   - Raises explicit domain errors (`InvalidPropertyIdError`, `ResourceNotFoundError`, `PropertyDataError`) mapped to clean HTTP status codes (`400`, `404`, or startup failure).

4. **Prediction Service (`app/services/prediction_service.py`)**
   - Exposes `PredictionService.predict_price(request)` and `predict_price(features, property_id)`.
   - Returns `status: "MODEL_NOT_CONFIGURED"` when no model artifact is loaded.
   - Designed so a future `joblib`-loaded scikit-learn `LinearRegression` model can be injected at startup without modifying route handlers or frontend code.

5. **Configuration (`app/config.py`)**
   - Reads `APP_ENV`, `APP_HOST`, `APP_PORT`, `DATA_FILE_PATH`, `FRONTEND_DIR`, `MODEL_PATH`, and `MODEL_VERSION` from environment variables so Development, Staging, and Production EC2 instances stay cleanly separated.

---

## Request–Response Flow

1. User opens `/` -> FastAPI serves `frontend/index.html` and static assets under `/static/*`.
2. Frontend calls `GET /api/cities` -> `GET /api/cities/city-a/localities` -> `GET /api/localities/local-1/properties` -> `GET /api/properties/A1`.
3. Numerical fields populate with `A1` features (`area_sqft`, `bedrooms`, `bathrooms`, `age_years`).
4. User adjusts any feature values and clicks **Predict House Price**.
5. Frontend validates inputs and sends `POST /api/predict`:
   ```json
   {
     "property_id": "A1",
     "area_sqft": 850,
     "bedrooms": 2,
     "bathrooms": 1,
     "age_years": 12
   }
   ```
6. Backend validates the payload via `PredictionRequest`, confirms property existence, invokes `prediction_service.predict_price()`, and returns:
   ```json
   {
     "status": "MODEL_NOT_CONFIGURED",
     "property_id": "A1",
     "predicted_price_inr": null,
     "currency": "INR",
     "model_version": null,
     "timestamp": "2026-11-17T01:20:00Z",
     "message": "Prediction model is not configured yet. Train and configure the Multiple Linear Regression model to generate price estimates."
   }
   ```

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health and model configuration status |
| `GET` | `/api/cities` | List available cities |
| `GET` | `/api/cities/{city_id}/localities` | List localities within a city |
| `GET` | `/api/localities/{locality_id}/properties` | List properties within a locality |
| `GET` | `/api/properties/{property_id}` | Retrieve property metadata and four features |
| `POST` | `/api/predict` | Validate features and run prediction service |

---

## Ubuntu Setup & Running Locally (`venv` + Uvicorn)

### 1. System Prerequisites (Ubuntu 22.04 / 24.04)

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
```

### 2. Create Virtual Environment & Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Application with Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://<server-ip>:8000` in your browser.

For local development with auto-reload:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run Automated Tests

```bash
pytest -v
```

---

## Environment Variables (Optional)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Environment name (`development`, `staging`, `production`) |
| `APP_HOST` | `0.0.0.0` | Uvicorn bind host |
| `APP_PORT` | `8000` | Uvicorn bind port |
| `DATA_FILE_PATH` | `app/data/properties.json` | Path to synthetic properties JSON file |
| `FRONTEND_DIR` | `frontend` | Path to static frontend directory |
| `MODEL_PATH` | *(unset)* | Future path to downloaded regression model artifact |
| `MODEL_VERSION` | *(unset)* | Future model version identifier |

---

## systemd Service Example (AWS EC2)

```ini
[Unit]
Description=House Price Predictor FastAPI Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/house-price-predictor
Environment="APP_ENV=production"
ExecStart=/opt/house-price-predictor/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Preview Runtime Note

In Node-only sandboxed preview environments where Python `pip`/`fastapi` are not preinstalled, `server.ts` acts as a lightweight preview host serving the exact same `frontend/` assets and `/api/*` JSON contracts backed by `app/data/properties.json`. All production/EC2 deployments run the FastAPI application (`app/main.py`) via Uvicorn.
