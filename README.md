# Race Wrangler POC

A local-first timing and scoring system for grassroots motorsports events. This proof-of-concept demonstrates the core workflow: **Starter confirms car at start line → Finish worker confirms car at finish line → Timing staff manage penalties and results**.

## Overview

Race Wrangler replaces traditional timing systems with a human-in-loop approach that eliminates false triggers and provides real-world workflow alignment. This POC showcases three key worker interfaces:

1. **Starter UI** — Confirms car identity with photo before run begins
2. **Finish Worker UI** — Confirms car identity with photo when run completes  
3. **Timing & Scoring UI** — Manages run results, penalties, DNF, and abort statuses

### Quick Start (Docker)

```bash
# Start everything with one command
docker-compose up

# Access the system:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Local Development Setup

### Prerequisites

- **Python 3.11+** (Backend)
- **Node.js 18+** (Frontend)
- **Git**

### Backend Setup

#### 1. Create Python virtual environment

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Run the server

```bash
# Seed database and start FastAPI
python app.py

# Or use uvicorn directly with hot reload
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend will:
- Initialize SQLite database at `./race_wrangler.db`
- Seed 5 cars from `docs/poc/hardcoded cars list.json`
- Serve API on `http://localhost:8000`
- Provide interactive API docs at `http://localhost:8000/docs`

### Frontend Setup

#### 1. Install dependencies

```bash
cd frontend
npm install
```

#### 2. Start development server

```bash
npm run dev
```

The frontend will:
- Start on `http://localhost:3000`
- Proxy API calls to `http://localhost:8000/api`
- Hot-reload on file changes

### HTTPS for phone camera access

Mobile browsers usually require a secure context for camera access. To test the Starter UI on your phone, run the Vite dev server over HTTPS and trust a local certificate.

#### 1. Install mkcert on Windows and create a trusted local CA

```powershell
winget install FiloSottile.mkcert
mkcert -install
```

#### 2. Create a certificate for your Windows LAN IP

Replace `192.168.1.42` with your Windows machine's LAN IP:

```powershell
mkdir C:\certs\racewrangler
cd C:\certs\racewrangler
mkcert 192.168.1.42 localhost 127.0.0.1 ::1
```

This produces a cert/key pair such as:
- `192.168.1.42+3.pem`
- `192.168.1.42+3-key.pem`

#### 3. Start the frontend with HTTPS enabled

From WSL:

```bash
cd frontend
VITE_HTTPS_CERT_PATH=/mnt/c/certs/racewrangler/192.168.1.42+3.pem \
VITE_HTTPS_KEY_PATH=/mnt/c/certs/racewrangler/192.168.1.42+3-key.pem \
npm run dev
```

The frontend will serve on `https://localhost:3000` inside WSL and, with Windows port forwarding, on `https://<your-windows-lan-ip>:3000` from your phone.

#### 4. Trust the certificate on your phone

You must trust mkcert's root CA on the phone, otherwise the browser will block camera access.

- iPhone: install the CA profile, then enable trust under `Settings > General > About > Certificate Trust Settings`
- Android: install the CA as a certificate authority in security settings

#### 5. Keep the frontend API path relative

The app uses `/api` by default so the browser talks to the frontend origin and the Vite proxy forwards requests to the backend.

#### 3. Build for production

```bash
npm run build
npm run preview
```

## Project Structure

```
racewrangler/
├── backend/
│   ├── app.py                 # FastAPI application entry point
│   ├── database.py            # SQLAlchemy database configuration
│   ├── models.py              # Car and Run data models
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── routes/
│   │   └── runs.py            # API endpoints: /start, /finish, /runs, /runs/{id}/update
│   ├── seed_data.py           # Database seeding from hardcoded cars list
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile             # Production Docker image
│   └── venv/                  # Local virtual environment (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main React component with tab navigation
│   │   ├── main.tsx           # React entry point
│   │   ├── components/
│   │   │   ├── StarterUI.tsx          # Starter interface
│   │   │   ├── FinishWorkerUI.tsx     # Finish worker interface
│   │   │   └── TimingAndScoringUI.tsx # Timing & scoring dashboard
│   │   ├── services/
│   │   │   └── api.ts         # API client with fetch wrapper
│   │   └── styles/
│   │       └── main.css       # Global styles
│   ├── index.html             # HTML entry point
│   ├── package.json           # Node dependencies
│   ├── tsconfig.json          # TypeScript configuration
│   ├── vite.config.ts         # Vite build configuration
│   ├── Dockerfile             # Production Docker image
│   ├── node_modules/          # Dependencies (gitignored)
│   └── dist/                  # Built files (gitignored)
│
├── storage/
│   └── photos/
│       ├── start/             # Start-line photos
│       └── finish/            # Finish-line photos
│
├── docs/
│   ├── Product Vision.md
│   ├── System Overview.md
│   ├── poc/
│   │   ├── backend-tech-stack.md
│   │   ├── hardcoded cars list.json (used as seed data)
│   │   ├── minimal-api-spec.md
│   │   ├── scope.md
│   │   └── ui-component-overview.md
│   └── data-model/
│
├── docker-compose.yml         # Docker Compose for full POC
├── README.md                  # This file
└── LICENSE
```

## API Endpoints

All responses use a consistent envelope format:

```json
{
  "success": true,
  "data": { /* response data */ },
  "error": null
}
```

### GET /api/cars

Get all available cars.

**Response:**
```json
[
  {
    "id": 1,
    "number": "1",
    "class_name": "LMP1",
    "model": "Audi R18 e-tron quattro"
  }
]
```

### POST /api/start

Start a new run with car and photo.

**Request:**
```
Content-Type: multipart/form-data
car_id: 1
photo: [binary file]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "car_id": 1,
    "start_time": "2026-04-02T12:34:56",
    "start_photo_url": "/photos/start/photo_20260402_123456_000000.jpg",
    "penalties": 0,
    "is_dnf": false,
    "is_aborted": false,
    "finish_confirmed": false
  }
}
```

### POST /api/finish

Complete a run with finish photo.

**Request:**
```
Content-Type: multipart/form-data
run_id: 1
photo: [binary file]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "car_id": 1,
    "start_time": "2026-04-02T12:34:56",
    "finish_time": "2026-04-02T12:35:02",
    "raw_time": 6.123,
    "adjusted_time": 6.123,
    "start_photo_url": "/photos/start/photo_20260402_123456_000000.jpg",
    "finish_photo_url": "/photos/finish/photo_20260402_123502_000000.jpg",
    "penalties": 0,
    "is_dnf": false,
    "is_aborted": false,
    "finish_confirmed": true
  }
}
```

### GET /api/runs

Get all runs (optionally filtered).

**Query Parameters:**
- `status` (optional): `"active"` or `"completed"`

**Response:**
```json
{
  "success": true,
  "data": {
    "runs": [ /* array of run objects */ ]
  }
}
```

### POST /api/runs/{run_id}/update

Update run properties (penalties, DNF, abort).

**Request:**
```json
{
  "penalties": 2,
  "is_dnf": false,
  "is_aborted": false
}
```

**Response:**
```json
{
  "success": true,
  "data": { /* updated run object */ }
}
```

## Usage Workflow

### 1. Starter

1. Navigate to **Starter UI** tab
2. Search for and select a car by **number or model name** (searchable dropdown)
3. Allow camera access when prompted
4. Click **📸 Take Photo** to capture vehicle/driver
5. Review photo preview
6. Click **✓ Confirm Start** to begin run
7. Toast notification confirms run created

### 2. Finish Worker

1. Navigate to **Finish Worker UI** tab
2. Wait for active runs to appear (displays photos from starter)
3. Click **⏱️ Simulate Finish Trigger** to simulate timing detection
4. When trigger shows as active, select the matching car photo from the grid
5. Click **✓ Confirm Finish** to complete run
6. Run immediately appears in Timing & Scoring UI

### 3. Timing & Scoring Staff

1. Navigate to **Timing & Scoring** tab
2. View all runs in real-time table (auto-refreshes every 1.5 seconds)
3. Manage each run:
   - **+1 / +2 Cone buttons** — Add penalty units (2 seconds each)
   - **✕ button** — Clear all penalties
   - **DNF toggle** — Mark as Did Not Finish
   - **Abort toggle** — Mark as Aborted
4. Adjusted time computes automatically: `raw_time + (penalties × 2.0 seconds)`

## Time Calculation

- **Raw Time**: Finish timestamp - Start timestamp (in seconds)
- **Penalties**: Cone/rule violations (default: 2 seconds per unit)
- **Adjusted Time**: `raw_time + (penalties × 2.0)`

Example:
- Car crosses finish in 47.234 seconds
- Timing staff adds 2 penalties (knocked 2 cones)
- Adjusted time: 47.234 + (2 × 2.0) = **51.234 seconds**

## Data Storage

- **Database**: SQLite file at `./race_wrangler.db` (or in-memory for testing)
- **Photos**: Stored locally in `./storage/photos/{start,finish}/`
- **Files**: Named with ISO timestamp for unique identification

## POC Limitations

The following features are **out of scope** for this POC and will be addressed in future phases:

- ❌ Worker authentication or user accounts
- ❌ Event configuration UI (POC uses hardcoded 5 cars)
- ❌ Competitor registration systems
- ❌ Run groups, heat management, or complex scheduling
- ❌ Validation logic or error correction workflow
- ❌ Finalization/results locking system
- ❌ Rerun management
- ❌ Real OCR or camera hardware integration
- ❌ Multi-event support
- ❌ Admin UI for event management
- ❌ Series scoring or PAX calculations

## Development Notes

### Adding a New Car

1. Edit `docs/poc/hardcoded cars list.json`
2. Add a new object with `id`, `number`, `class`, `model`
3. Delete `race_wrangler.db` to reseed on next run, or manually add via SQL

### Testing the System

1. **Start a run**: Select car → take photo → confirm start
2. **Finish a run**: Trigger finish → select photo → confirm finish
3. **Manage penalties**: Add penalties and verify adjusted time computes correctly
4. **Try DNF/Abort**: Toggle statuses and watch badges update

### Backend Debugging

- Check SQLite schema: `sqlite3 race_wrangler.db ".schema"`
- View all runs: `sqlite3 race_wrangler.db "SELECT * FROM runs;"`
- Enable SQL logging: Change `echo=False` to `echo=True` in `database.py`

### Frontend Debugging

- Open browser DevTools (F12)
- Check Network tab for API calls
- Check Console for errors
- API proxying configured in `vite.config.ts`

## Troubleshooting

### Backend won't start
```bash
# Ensure Python 3.11+ and virtual env is activated
python --version
which python

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Reset database
rm race_wrangler.db
python app.py
```

### Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Camera not working
- Give browser permission to access camera
- Try a different browser (Chrome works best)
- Check system camera permissions

### Photos not saving
- Ensure `./storage/photos/{start,finish}/` directories exist
- Check file permissions on storage directory
- Inspect browser Console for blob errors

### Docker issues
```bash
# Clean up containers
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend Framework** | FastAPI | 0.104+ |
| **Server** | Uvicorn | 0.24+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database** | SQLite | (file-based) |
| **Validation** | Pydantic | 2.5+ |
| **Frontend Framework** | React | 18.2+ |
| **Language** | TypeScript | 5.3+ |
| **Build Tool** | Vite | 5.0+ |
| **Container** | Docker | (optional) |
| **Orchestration** | Docker Compose | (optional) |

## Architecture Decisions

1. **FastAPI + Uvicorn**: Fast development, excellent Copilot support, built-in OpenAPI docs
2. **SQLite**: Zero-config local database, perfect for POC, seamless SQLAlchemy integration
3. **React + TypeScript**: Type safety, component reusability, familiar ecosystem
4. **Vite**: Fast dev server, excellent HMR, minimal configuration
5. **Local-first storage**: No external dependencies, works offline
6. **Standard JSON envelope**: Consistent API responses across endpoints
7. **No authentication**: Simplified for POC (add role tokens in production)

## Future Enhancements

- 🔐 Worker authentication via ephemeral role tokens
- 📸 Real OCR for number detection from camera feeds
- 🎥 Hardware camera integration with CameraSession
- 📅 Event configuration and competitor registration UIs
- ☁️ Optional cloud sync and backup
- 📊 Advanced results and PAX scoring
- 🔄 Rerun management and validation workflows
- 📱 Mobile-optimized dark mode UI
- 🎛️ Admin dashboard for hardware monitoring

## Contributing

See `docs/` for detailed system architecture and data models.

## License

See LICENSE file.

---

**Questions?** Check the stack traces in browser DevTools or backend logs for detailed error information. API is fully documented at `http://localhost:8000/docs` when running locally.