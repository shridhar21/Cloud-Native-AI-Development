# House Price Predictor (Version 1)

A FastAPI and vanilla JavaScript application that uses a scikit-learn regression pipeline to estimate Bengaluru house prices in rupees.

## Scope (Version 1)

- **Prediction area** — Bengaluru.
- **Features**:
  - `area_sqft` (positive float)
  - `bedrooms` (integer >= 1)
  - `bathrooms` (integer >= 1)
  - `location` (Bengaluru locality)
- **Model artifact** — Configure a fitted `model.joblib` through `MODEL_PATH`. The API returns `MODEL_NOT_CONFIGURED` when the path is unset.

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
│   │   └── prediction_service.py   # Model loading and inference
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
   - Accepts the four prediction inputs directly and displays the estimate in rupees.

2. **API Routing (`app/api/routes.py`)**
   - Thin FastAPI handlers prefixed with `/api`.
   - Delegates input validation to Pydantic (`app/schemas.py`), data retrieval to `PropertyService`, and prediction execution to `PredictionService`.

3. **Property Data Access (`app/services/property_service.py`)**
   - Loads `app/data/properties.json` at startup and validates schema integrity and `[A-Z][1-10]` property identifiers.
   - Raises explicit domain errors (`InvalidPropertyIdError`, `ResourceNotFoundError`, `PropertyDataError`) mapped to clean HTTP status codes (`400`, `404`, or startup failure).

4. **Prediction Service (`app/services/prediction_service.py`)**
   - Loads the configured pipeline once at FastAPI startup and retains it in memory.
   - Maps the request to the model columns `location`, `total_sqft`, `bhk`, and `bath`. The model's output is in lakhs and the service converts it to rupees.

5. **Configuration (`app/config.py`)**
   - Reads `APP_ENV`, `APP_HOST`, `APP_PORT`, `DATA_FILE_PATH`, `FRONTEND_DIR`, `MODEL_PATH`, and `MODEL_VERSION` from environment variables so Development, Staging, and Production EC2 instances stay cleanly separated.

---

## Request–Response Flow

1. User opens `/` -> FastAPI serves `frontend/index.html` and static assets under `/static/*`.
2. The user enters a Bengaluru locality, area, bedrooms, and bathrooms.
3. The frontend sends `POST /api/predict` with the four inputs.
   ```json
   {
     "location": "Whitefield",
     "area_sqft": 850,
     "bedrooms": 2,
     "bathrooms": 1
   }
   ```
4. FastAPI validates the inputs and calls `prediction_service.predict_price()`. An example response for a configured model follows.
   ```json
   {
     "status": "SUCCESS",
     "location": "Whitefield",
     "predicted_price_inr": 7500000,
     "currency": "INR",
     "model_version": "v1",
     "timestamp": "2026-11-17T01:20:00Z",
     "message": "House price prediction generated successfully."
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

Use the same scikit-learn version recorded in the model's `metadata.json`. Set the path to a trusted local artifact before starting FastAPI. On Development EC2, the training script writes the v1 artifact under `$HOME/artifacts/house-price/v1`.

```bash
export MODEL_PATH="$HOME/artifacts/house-price/v1/model.joblib"
export MODEL_VERSION=v1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

When `MODEL_PATH` is set, an unreadable or incompatible artifact causes startup to fail. Check `/api/health` for `model_configured` and `model_version` once the app is running.

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
| `MODEL_PATH` | *(unset)* | Local path to the fitted `model.joblib` artifact |
| `MODEL_VERSION` | *(unset)* | Version reported by the health and prediction endpoints |

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
Environment="MODEL_PATH=/opt/house-price-predictor/models/v1/model.joblib"
Environment="MODEL_VERSION=v1"
ExecStart=/opt/house-price-predictor/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Preview Runtime Note

The Node preview serves the same frontend and sample-property endpoints. Its prediction endpoint returns `MODEL_NOT_CONFIGURED`. Run FastAPI with `MODEL_PATH` configured to serve actual estimates.
