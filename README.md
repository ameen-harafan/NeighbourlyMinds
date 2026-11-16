# NeighbourlyMinds 🏡

> **Environmental Cognitive Accessibility & Independence Platform for Older Victorians**  
> *Monash University — Faculty of Information Technology (FIT5120 Industry Experience Capstone)*

---

## 📖 Project Overview

**NeighbourlyMinds** is an assistive environmental cognitive accessibility platform designed for older Victorians experiencing early-stage progressive memory changes (dementia), exemplified by our primary persona, **Margaret Kelly**. 

Traditional tools often clinicalise cognitive decline, creating anxiety and stigma. NeighbourlyMinds shifts the paradigm: **the built environment is the source of wayfinding and spatial struggle, not the person's mind.** By identifying and adapting subtle environmental barriers—such as white-on-white surfaces, low-contrast door architraves, specular floor glare, and disorienting crowded routes—the platform empowers older adults to maintain independent living, spatial confidence, and active civic participation.

---

## 🏛️ System Architecture

NeighbourlyMinds is architected across four decoupled tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Vue 3 + TypeScript Client                       │
│     (Vite · Pinia Store · Driver.js Walkthroughs · Accessible UI)      │
│                         http://localhost:5173                          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTP / REST
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Node.js / Express 5 API                         │
│       (Helmet · Rate Limiting · Multer Staging · PDFKit Export)        │
│                         http://localhost:3000                          │
└──────────────┬──────────────────────────────────────────┬──────────────┘
               │ Internal Reverse Proxy                   │ SQL / PostGIS
               ▼                                          ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│   FastAPI AI Vision Microservice     │  │   PostgreSQL 16 + PostGIS    │
│  (PyTorch · Florence-2-base · CLIP)  │  │  (pgRouting · Spatial DB)    │
│         http://localhost:8000        │  │      localhost:5432          │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## 🌟 Key Modules (6 Backlog Epics)

1. **Gateway Dashboard & Normalisation Hub (Epic 1)**
   - Welcomes users with high-contrast, large-font typography and non-stigmatising problem framing.
   - Dynamic Victorian municipal council selector (79 LGAs) querying precalculated dementia prevalence estimates (ABS 2025 & AIHW Table S2.1).
   - Unified single-scroll onboarding and diagrammatic accessibility grid.

2. **Interactive Room Guides — Visual Explorer (Epic 2)**
   - Flat 2D vector room templates (Bathroom & Kitchen) avoiding disorienting 3D perspectives or rendering latency.
   - Real-time Light Reflectance Value (LRV) calculation engine evaluating wall-to-frame contrast.
   - Specular floor glare demonstrators and persistent visual caution hotspots.

3. **Universal Indoor Environment Auditor & Transformation Simulator (Epic 3)**
   - Upload room photos to detect 21 environmental dementia hazards (camouflage, visual confusion, perceived black-hole rugs, shiny floor glare).
   - Powered by **Microsoft Florence-2-base** (dense captioning, referring segmentation, OCR) and **OpenAI CLIP** (indoor classification & zero-shot semantic categorization).
   - Asynchronous job queue with real-time countdown progress and rotating dementia-friendly design tips.

4. **Daytime Sensory Schedule Predictor (Epic 4)**
   - Analyzes City of Melbourne open sensor streams (Microclimate Noise & Pedestrian Foot Traffic).
   - Strict **9:00 AM – 5:00 PM** daytime window constraint to avoid disorienting late-night outings.
   - Recommends quietest departure hours and syncs directly with activity preparation.

5. **Landmark-Anchored Route Planner & Folding Pocket Card (Epic 5)**
   - Turn-penalized Dijkstra routing over a PostGIS `turn_graph` to prioritize straight-line paths.
   - Sequential landmark cue extraction from municipal CLUE datasets (e.g. *"Turn right at the State Library"*).
   - LiDAR tree canopy shade density and park bench interval calculations.
   - Printable 4-quadrant **Folding Pocket Independence Card** featuring non-verbal communication badges and emergency contact info.

6. **Community Accessibility Feedback Hub (Epic 6)**
   - Civic advocacy tool empowering older adults to report public corridor barriers (AS 1428.1 compliance).
   - Spatial point-in-polygon geocoder matching photo GPS coordinates to Victorian Local Government Area email directories.
   - Generates polite, non-confrontational municipal feedback emails with permanent submission tracking.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Vue 3.5, TypeScript 6.0, Vite 8, Pinia, Driver.js |
| **Backend API** | Node.js (v22/v24), Express 5.2, Helmet, Multer, PDFKit, pg |
| **Computer Vision Microservice** | Python 3.11, FastAPI, PyTorch, Transformers, Florence-2-base, CLIP-ViT-B/32, OpenCV |
| **Spatial Database** | PostgreSQL 16, PostGIS 3.4, pgRouting 3.6 |
| **Geospatial & Public Data** | City of Melbourne Open Data, DataVic LiDAR Canopies, ABS 2025, AIHW Dementia Baselines |

---

## ⚡ Service Port Allocation

| Service | Port | Description |
| :--- | :--- | :--- |
| **Vite Frontend Client** | `5173` | Accessible web application interface |
| **Node.js Express Server** | `3000` | Core API, routing engine & PDF compiler |
| **Python FastAPI Microservice**| `8000` | Florence-2 & CLIP computer vision inference |
| **PostgreSQL / PostGIS** | `5432` | Spatial network topology & municipal datasets |

---

## 🚀 Getting Started

### Prerequisites

1. **Node.js**: `v22.18.0` or `>= v24.12.0`
2. **Python**: `3.11+`
3. **Git & Git LFS**: Ensure Git Large File Storage is installed:
   ```bash
   git lfs install
   ```
4. **PostgreSQL**: Version 15+ with `postgis` and `pgrouting` extensions installed.

---

### Step 1: Clone the Repository

Clone the repository with Git LFS enabled:
```bash
git clone https://github.com/<your-username>/neighborlyminds.git
cd neighborlyminds
git lfs pull
```

---

### Step 2: Environment Configuration

Copy the example environment configuration:
```bash
cp .env.example .env
```

Open `.env` and fill in your local credentials:
```env
# Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=neighborlyminds
DB_USER=postgres
DB_PASSWORD=your_password_here

# Frontend Keys
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Security
SITE_ACCESS_PASSWORD=your_local_site_password
ADMIN_API_TOKEN=your_random_admin_token
ALLOWED_ORIGINS=http://localhost:5173
```

---

### Step 3: Database Automated Setup

Ensure PostgreSQL is running locally, then execute the master database migration script:
```bash
npm install
npm run db:setup
```
*This command automatically:*
- Creates the `neighborlyminds` database if not present.
- Activates `postgis` and `pgrouting` extensions.
- Ingests all ABS, AIHW, and municipal boundary datasets.
- Imports spatial GeoJSON polygons (pedestrian network, landmarks, tree canopies).
- Builds the turn-penalized routing topology graph.
- Registers all custom spatial SQL calculation functions.

Then import Victorian council contact directories:
```bash
npm run db:contacts
```

---

### Step 4: Start the AI Computer Vision Microservice

In a separate terminal:
```bash
cd cv_service

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server on port 8000
python main.py
```
*(On initial launch, PyTorch will download the Florence-2-base and CLIP model weights).*

---

### Step 5: Start the Node.js API Server

In a separate terminal:
```bash
npm run server
```
Server will start listening at `http://localhost:3000`.

---

### Step 6: Start the Frontend Application

In a separate terminal:
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Quality Assurance

```bash
# Type check TypeScript definitions
npm run type-check

# Compile production build
npm run build
```

---

## 📋 Agile Specifications Compliance

This repository conforms 100% to **Monash LeanKit Agile Specifications (v13.0)**:
- **6 Epics** (Crimson / Red `#CC0000`)
- **22 User Stories** (Steel Blue `#2F5496`) centered on persona **Margaret Kelly**
- **66 Acceptance Criteria** (Forest Green `#27AE60`) in strict Given/When/Then format with zero technical jargon
- **330 Technical Subtasks** strictly estimated at **3–4 hour units** (330 $\times$ 3.5h $\approx$ 1,155 engineering hours)
- **66 Explicit Data Cleaning Subtasks** (`T1` in every Acceptance Criteria)

---

## 📄 License

This project is licensed under the [MIT License](file:///c:/Users/Ameen%20Harafan/Documents/FIT5120/neighborlyminds/LICENSE).
