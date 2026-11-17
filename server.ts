import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

const PORT = Number(process.env.PORT || 3000);
const DATA_PATH = path.resolve(process.cwd(), 'app', 'data', 'properties.json');
const FRONTEND_DIR = path.resolve(process.cwd(), 'frontend');
const PROPERTY_ID_REGEX = /^[A-Z](?:10|[1-9])$/;

interface CityRecord {
  id: string;
  name: string;
}

interface LocalityRecord {
  id: string;
  name: string;
  city_id: string;
}

interface PropertyFeaturesRecord {
  area_sqft: number;
  bedrooms: number;
  bathrooms: number;
  age_years: number;
}

interface PropertyRecord {
  id: string;
  city_id: string;
  locality_id: string;
  features: PropertyFeaturesRecord;
}

interface DatasetPayload {
  cities: CityRecord[];
  localities: LocalityRecord[];
  properties: PropertyRecord[];
}

function loadDataset(): DatasetPayload {
  if (!fs.existsSync(DATA_PATH)) {
    throw new Error(`Property data file not found at ${DATA_PATH}`);
  }
  const raw = fs.readFileSync(DATA_PATH, 'utf-8');
  return JSON.parse(raw) as DatasetPayload;
}

function utcTimestampIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

const dataset = loadDataset();
const app = express();
app.use(express.json());
app.use('/static', express.static(FRONTEND_DIR));

app.get('/api/health', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    service: 'house-price-predictor',
    environment: process.env.APP_ENV || 'development',
    model_configured: false,
    model_version: null,
    timestamp: utcTimestampIso(),
  });
});

app.get('/api/cities', (_req: Request, res: Response) => {
  res.json({ cities: dataset.cities });
});

app.get('/api/cities/:cityId/localities', (req: Request, res: Response) => {
  const { cityId } = req.params;
  const cityExists = dataset.cities.some((c) => c.id === cityId);
  if (!cityExists) {
    res.status(404).json({ detail: `City '${cityId}' not found.` });
    return;
  }
  const localities = dataset.localities.filter((l) => l.city_id === cityId);
  res.json({ city_id: cityId, localities });
});

app.get('/api/localities/:localityId/properties', (req: Request, res: Response) => {
  const { localityId } = req.params;
  const localityExists = dataset.localities.some((l) => l.id === localityId);
  if (!localityExists) {
    res.status(404).json({ detail: `Locality '${localityId}' not found.` });
    return;
  }
  const properties = dataset.properties
    .filter((p) => p.locality_id === localityId)
    .map((p) => ({
      id: p.id,
      label: p.id,
      city_id: p.city_id,
      locality_id: p.locality_id,
    }));
  res.json({ locality_id: localityId, properties });
});

app.get('/api/properties/:propertyId', (req: Request, res: Response) => {
  const propertyId = String(req.params.propertyId || '').trim();
  if (!PROPERTY_ID_REGEX.test(propertyId)) {
    res.status(400).json({
      detail: 'Invalid property identifier. Expected format [A-Z][1-10], such as A1 through A10.',
    });
    return;
  }

  const prop = dataset.properties.find((p) => p.id === propertyId);
  if (!prop) {
    res.status(404).json({ detail: `Property '${propertyId}' not found.` });
    return;
  }

  const city = dataset.cities.find((c) => c.id === prop.city_id);
  const locality = dataset.localities.find((l) => l.id === prop.locality_id);
  res.json({
    id: prop.id,
    city_id: prop.city_id,
    city_name: city ? city.name : prop.city_id,
    locality_id: prop.locality_id,
    locality_name: locality ? locality.name : prop.locality_id,
    features: prop.features,
  });
});

app.post('/api/predict', (req: Request, res: Response) => {
  const body = req.body ?? {};
  const propertyId = typeof body.property_id === 'string' ? body.property_id.trim() : '';

  if (!PROPERTY_ID_REGEX.test(propertyId)) {
    res.status(422).json({
      detail: 'Invalid property identifier. Expected format [A-Z][1-10], such as A1 through A10.',
    });
    return;
  }

  const areaSqft = Number(body.area_sqft);
  const bedrooms = Number(body.bedrooms);
  const bathrooms = Number(body.bathrooms);
  const ageYears = Number(body.age_years);

  if (!Number.isFinite(areaSqft) || areaSqft <= 0 || areaSqft > 100000) {
    res.status(422).json({ detail: 'area_sqft must be greater than 0 and at most 100000.' });
    return;
  }
  if (!Number.isInteger(bedrooms) || bedrooms < 1 || bedrooms > 50) {
    res.status(422).json({ detail: 'bedrooms must be an integer between 1 and 50.' });
    return;
  }
  if (!Number.isInteger(bathrooms) || bathrooms < 1 || bathrooms > 50) {
    res.status(422).json({ detail: 'bathrooms must be an integer between 1 and 50.' });
    return;
  }
  if (!Number.isFinite(ageYears) || ageYears < 0 || ageYears > 200) {
    res.status(422).json({ detail: 'age_years must be a nonnegative number up to 200.' });
    return;
  }

  const exists = dataset.properties.some((p) => p.id === propertyId);
  if (!exists) {
    res.status(404).json({ detail: `Property '${propertyId}' not found.` });
    return;
  }

  res.json({
    status: 'MODEL_NOT_CONFIGURED',
    property_id: propertyId,
    predicted_price_inr: null,
    currency: 'INR',
    model_version: null,
    timestamp: utcTimestampIso(),
    message:
      'Prediction model is not configured yet. Train and configure the Multiple Linear Regression model to generate price estimates.',
  });
});

app.get('/', (_req: Request, res: Response) => {
  res.sendFile(path.join(FRONTEND_DIR, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`House Price Predictor preview server listening on http://0.0.0.0:${PORT}`);
});
