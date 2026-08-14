# KrishiMitra — AI Crop Type, Moisture Stress Detection &amp; Irrigation Advisory

**Team SpaceHack — Bharatiya Antariksh Hackathon 2026 (ISRO H2S)**
Problem Statement: *AI-Driven Automated Crop type, Moisture Stress Detection and irrigation
advisory Across Growth Stages Using Moderate Resolution Spectral Signatures
(Optical &amp; Microwave Satellite Data)*

---

## Kya bana hai (What this is)

Ek end-to-end working prototype jo PPT mein diye gaye system pipeline ko implement karta hai:

```
Data Ingestion → Preprocessing → Feature Extraction → AI Modeling → Decision Engine → Dashboard
```

| Stage | Implementation (this repo) | Production upgrade path |
|---|---|---|
| Data Ingestion | `model/satellite_sim.py` — deterministic, schema-matched Sentinel-2 (optical) + Sentinel-1 (SAR) simulator, crop-calendar aware | Swap for Google Earth Engine Python API pulling real Sentinel-2/Landsat/AWiFS + Sentinel-1/NISAR |
| Preprocessing | Baked into simulator (cloud-free, terrain-corrected signal) | Sen2Cor atm. correction, FMask cloud masking, SNAP/ISCE SAR speckle filter |
| Feature Extraction | NDVI, NDWI, MSI, VV/VH backscatter + ratio, growth_fraction | Same, computed from real rasters via GDAL/Rasterio/xarray |
| AI Modeling | RandomForest crop classifier (76% acc) + RandomForest stress classifier (96% acc) — `model/train_model.py` | CNN-Transformer (crop ID) + LSTM-Attention (phenology), trained on multi-year labelled Sentinel time series |
| Decision Engine | `model/decision_engine.py` — FAO-56 Kc-based crop water balance + stress-severity irrigation rules | Full CROPWAT/Optirrig integration + live rainfall forecast (OpenWeatherMap/NOAA) |
| Output/Delivery | Web dashboard (Flask) + JSON API + Hinglish advisory text (SMS-ready) | Add Twilio SMS delivery, GeoTIFF/shapefile export |

**Kyun simulated satellite data?** Live Google Earth Engine / Copernicus API access is
sandbox mein available nahi tha (no internet in the build environment). Isliye
`satellite_sim.py` ek deterministic, crop-calendar-aware generator hai jo Sentinel-2/-1
jaisa hi feature schema deta hai — taaki AI model, decision engine, aur dashboard
**exactly wahi** kaam karein jo real data ke saath karenge. Real access milte hi sirf
`satellite_sim.simulate_field()` ko GEE calls se replace karna hai — baaki system untouched.

---

## Project structure

```
krishimitra/
├── app.py                        # Flask backend + REST API
├── requirements.txt
├── Dockerfile
├── model/
│   ├── satellite_sim.py          # simulated Sentinel-2 + Sentinel-1 ingestion
│   ├── generate_training_data.py # synthetic labelled dataset generator
│   ├── train_model.py            # trains + saves crop_model.pkl, stress_model.pkl
│   ├── decision_engine.py         # irrigation advisory rules (FAO-56 Kc)
│   ├── crop_model.pkl / stress_model.pkl / metrics.json   (generated)
├── templates/index.html          # dashboard UI
├── static/style.css, script.js   # dashboard styling + Leaflet map logic
└── tests/test_app.py             # pytest suite (12 tests)
```

---

## Current API (v2 — all original endpoints preserved + new ones added)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/fields` | GET | Original — pipeline results for the 6 demo fields |
| `/api/analyze` | POST | Original — ad-hoc lat/lon analysis (now also logs to history) |
| `/api/model-metrics` | GET | Original — crop/stress model accuracy |
| `/api/health` | GET | Original — health check |
| `/api/weather` | GET `?lat=&lon=` | **New** — OpenWeatherMap if `OPENWEATHER_API_KEY` set, else simulated |
| `/api/search-location` | GET `?q=` | **New** — village/district/state search via Nominatim |
| `/api/history` | GET `?crop=&urgency=&limit=` | **New** — past analyses (SQLite-backed) |
| `/api/dashboard` | GET | **New** — aggregate stats across all demo fields |

**Response format unchanged** for all four original endpoints — nothing that already
worked was modified.

## What's new in this version (Phase 1 + Phase 2)

- **Frontend**: glassmorphism dark space theme, animated sidebar with search/filter chips,
  skeleton loading states, 4 map base layers (Dark/Satellite/Street/Terrain) + NDVI/Stress/Heatmap
  overlay toggles, marker clustering, locate-me + fullscreen controls, risk badges + progress bars
  in the detail panel, growth timeline visual, 4-step Analyze wizard (Location → Crop&Stage →
  Weather → Analyze), animated pipeline architecture diagram + illustrative feature importance chart.
- **Backend**: `model/gee.py` (Google Earth Engine module — auto-initializes if `earthengine-api`
  is installed and credentials are set via `GEE_SERVICE_ACCOUNT`/`GEE_KEY_PATH`; otherwise falls
  back to the existing simulator automatically, no code changes needed elsewhere), `model/weather.py`
  (OpenWeatherMap, env var `OPENWEATHER_API_KEY`), `model/location_search.py` (Nominatim),
  `model/history.py` (SQLite log of every `/api/analyze` call).
- **Not yet implemented** (documented honestly, not silently skipped): PDF report generation,
  JWT auth (farmer/admin login), PWA offline support, WhatsApp/SMS delivery, Chart.js trend
  charts. These are straightforward additions on top of the current structure — ask if you want
  them built out next.

## 1. Setup (ek baar)

```bash
cd krishimitra
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Model train karna (build)

```bash
python3 model/generate_training_data.py   # 6000 synthetic labelled samples banata hai
python3 model/train_model.py              # crop_model.pkl + stress_model.pkl train + save
```

Expected output: crop model ~76% accuracy, stress model ~96% accuracy (`model/metrics.json` mein saved).

## 3. Run karna

```bash
python3 app.py
```

Browser mein kholein: **http://localhost:5000**

- **Field Map** tab — 6 demo fields (UP districts) live pipeline se analyzed, map par color-coded (NDVI health + stress urgency)
- **Naya Field Analyze** tab — koi bhi lat/lon daalo, full pipeline live chalega
- **Pipeline** tab — model accuracy metrics + architecture steps

## 4. Test karna

```bash
pip install pytest   # agar requirements.txt se pehle install nahi hua
pytest tests/ -v
```

12 tests cover: simulator determinism, decision-engine rules, aur poora Flask API
(health check, fields list, analyze endpoint, error handling, model metrics).
Sab pass hone chahiye.

## 5. Quick API check (copy-paste)

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/fields
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"lat": 26.85, "lon": 80.95, "crop": "Wheat"}'
```

## 6. Deploy karna

**Option A — Docker (recommended for demo/judges' laptop):**
```bash
docker build -t krishimitra .
docker run -p 5000:5000 krishimitra
```
Browser: http://localhost:5000

**Option B — Cloud (Render / Railway / any Python host):**
- Push repo, set start command: `python3 app.py`
- Add build command: `pip install -r requirements.txt && python3 model/generate_training_data.py && python3 model/train_model.py`
- `PORT` env var automatically respected by `app.py`

---

## Presentation mein kya bolna hai (talking points)

1. **Problem**: Kisan ko pata nahi chalta ki field mein kaunsi fasal hai, kaunse growth
   stage mein hai, aur kab paani chahiye — satellite data available hai par usable form mein nahi.
2. **Solution**: Ek single AI pipeline jo Optical (NDVI/NDWI/MSI) + SAR (VV/VH) fuse karke
   crop type, growth stage, aur moisture stress teeno automatically nikalta hai, phir
   FAO-56 crop water balance se exact irrigation advisory deta hai.
3. **Live demo**: Dashboard kholo, koi bhi field select karo — 2 second mein AI prediction
   + confidence score + Hinglish advisory dikh jaata hai.
4. **Scale**: Yeh architecture GEE ke saath national-scale par chal sakta hai (cloud-native,
   stateless API, koi per-field manual analysis nahi).
5. **Differentiation**: Existing tools sirf crop map ya sirf moisture map dete hain — yeh
   ek hi pipeline mein dono + stage-aware advisory deta hai (jaisa PPT mein "Integrated
   Intelligence" USP hai).

---

## Known limitations (honestly documented for judges)

- Satellite data **simulated hai** (deterministic, schema-matched) kyunki live GEE access
  build environment mein nahi tha — real deployment se pehle `satellite_sim.py` ko GEE
  calls se replace karna hoga (interface already designed for drop-in swap).
- Crop classifier accuracy 76% hai (RandomForest, prototype-grade) — production mein
  CNN-Transformer + real multi-year training data se improve hoga.
- Dashboard map (Leaflet + CARTO tiles) internet access maangta hai judge ke laptop par
  (normal WiFi/hotspot kaafi hai).
