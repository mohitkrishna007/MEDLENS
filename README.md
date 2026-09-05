# MedLens — Clinical Information Intelligence & Traceable Patient Record

> **"Turn fragmented medical information into a structured, traceable patient story."**

MedLens is an evidence-backed clinical information intelligence platform built for hackathons and production healthcare workflows. It collects patient intake data and processes medical reports (PDFs, laboratory tests, prescriptions) to transform scattered medical documents into a structured, reviewable, and longitudinal patient record.

---

## 🌟 Core Differentiating Features (Hackathon Wow Factor)

1. **Strict Source Reference Range Rule**: MedLens **never invents reference ranges**. If a document provides a reference range (e.g. `12.0 - 15.5 g/dL`), values are classified as `LOW`, `NORMAL`, or `HIGH`. If no range is present, it is explicitly marked **"Not provided in source"** and status set to **"Unable to determine from source"**.
2. **Side-by-Side Source & Provenance Traceability**: Click any extracted result to launch a dual-pane view: the original document snippet on the left and the extracted structured card on the right.
3. **Human-in-the-Loop Verification**: Review, edit, or mark extracted lab fields as verified. Tracks states: `AI Extracted`, `User Verified`, and `User Edited`.
4. **Conflict Radar**: Automatically flags inconsistencies across records (demographics like age differences, duplicate test value conflicts on the same date, and medication dosage mismatches) without auto-deciding winners.
5. **Longitudinal Report Trend Comparison**: Compare laboratory test values across multiple dates with neutral, non-diagnostic trend phrasing.
6. **Fact-Based Safe AI Summary**: Fact-only summary engine with medical disclaimers prohibiting diagnoses or treatment decisions.
7. **1-Click Live Hackathon Demo Mode**: Instantly pre-seeds a multi-report synthetic patient record ("Jane Doe") with longitudinal lab trends and active conflicts for immediate 3–5 minute judge evaluation.
8. **PDF Report Export**: One-click structured clinical summary PDF download.

---

## 🏗 System Architecture

```
[ Upload PDF / Image / Intake ]
             │
             ▼
    [ PDF / Text Extraction ]
             │
             ▼
   [ AI Structured Extractor ] ── (Gemini API / Rule-Engine Fallback)
             │
             ▼
  [ Reference Range Engine ]  ── (NEVER invents ranges; LOW/NORMAL/HIGH/UNKNOWN)
             │
             ▼
  [ Conflict Radar Engine ]   ── (Flags age, duplicate test, medication mismatches)
             │
             ▼
   [ Relational Database ]    ── (SQLite / PostgreSQL with SQLAlchemy)
             │
             ▼
   [ Interactive Web SPA ]    ── (HTML5 + Tailwind CSS + Lucide Icons + Chart.js)
```

---

## 🚀 Quick Start Guide (Local Setup)

### 1. Prerequisites
- Python 3.10+ installed

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/mohitkrishna007/Lex-intelligence.git
cd Lex-intelligence

# Install Python dependencies
python -m pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Key environment variables:
- `PORT`: Server port (default `8000`)
- `DATABASE_URL`: Database connection string (`sqlite:///./medlens.db`)
- `GEMINI_API_KEY`: (Optional) Google Gemini API key for LLM extractions. If omitted, MedLens automatically falls back to its robust medical regex NLP engine.

### 4. Running the Application
Start the FastAPI server:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## ☁️ Deployment Instructions (Google Cloud Run / Docker)

MedLens is fully containerized and production-ready for Google Cloud Run or Docker hosting.

### Building & Running with Docker
```bash
# Build Docker image
docker build -t medlens-app .

# Run container locally
docker run -p 8000:8000 -e PORT=8000 medlens-app
```

### Deploying to Google Cloud Run
```bash
# 1. Build and push to Google Container Registry / Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/medlens-app

# 2. Deploy to Cloud Run
gcloud run deploy medlens-app \
  --image gcr.io/YOUR_PROJECT_ID/medlens-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="your_api_key_here"
```

---

## 🧪 Running Unit Tests

Execute the automated test suite:
```bash
# Run range classifier tests
python -m unittest tests/test_range_classifier.py

# Run conflict detector tests
python -m unittest tests/test_conflict_detector.py
```

---

## 📝 Medical Safety & Responsible AI Disclaimers

MedLens strictly complies with responsible AI guidelines:
- **No Diagnosis or Treatment Advice**: The application organizes and summarizes provided medical information. It does not diagnose conditions, prescribe treatment, or replace professional medical advice.
- **Reference Range Integrity**: If a reference range is absent from the source document, MedLens labels it **"Not provided in source"** and status **"Unable to determine from source"**. It never invents ranges.
- **Provenance Preservation**: All extracted fields link directly to their source document and snippet text.

---

## 📄 License
MIT License. Built for hackathon presentation.
