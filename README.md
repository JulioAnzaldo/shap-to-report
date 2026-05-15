# shap-to-report

A RAG LLM pipeline that turns spacecraft anomaly detection output into structured diagnostic reports. Given a SHAP attribution result from an onboard anomaly detector, the pipeline retrieves relevant regulatory and historical context, generates a natural language situational report grounded in that context, validates the output for safety and quality, and returns a structured SituationalReport, or a typed refusal if confidence is too low.

---

## What it does

- **Input:** a spacecraft anomaly event (SHAP feature attributions + telemetry metadata) and a user-selected set of regulatory source bodies
- **Retrieval:** semantic search over a curated corpus (EU AI Act, NASA NPR 8715.3E, NASA NPR 8705.4A, NASA Lessons Learned) stored in a local ChromaDB instance
- **Generation:** gpt-4o-mini at temperature=0 with structured JSON output and a 11-rule system prompt enforcing observational language, citation grounding, and subsystem-aware anomaly classification
- **Validation:** OutputValidator rejects prescriptive action verbs, checks severity/confidence consistency, and verifies citation grounding
- **Output:** SituationalReport JSON rendered in a React UI, or a degraded_mode refusal card if retrieval or validation fails

---

## Requirements

- Python 3.11+
- Node.js 20+
- An OpenAI API key (gpt-4o-mini + text-embedding-3-small)

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/JulioAnzaldo/shap-to-report.git
cd shap-to-report

# 2. Create and activate a Python virtual environment
python3.12 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up your API key
cp .env.example .env
# Open .env and set:  OPENAI_API_KEY=sk-...
```

The ChromaDB vector store is pre populated and committed at backend/chroma_db/.

If you want to re-ingest the corpus from scratch (optional):
```bash
python -m backend.rag.ingest
```

---

## Run

### 1. Start the backend

```bash
python3 -m uvicorn backend.api.app:app --reload
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 2. Start the frontend

In a separate terminal (with the venv still active or from the project root):

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` (or 5174 if 5173 is in use).

Open the URL in your browser. You should see the event list in the left sidebar.

---

## Using the app

1. **Select an event** from the left sidebar (10 real SMAP anomaly events)
2. **Select source bodies:** toggle EU AI Act, NASA NPR, and/or NASA Lessons Learned
3. **Choose backend** — `mock` (instant, no API cost) or openai
4. **Click Generate Report**
5. The report appears with SHAP attribution bars, subsystem context, explanation, operator decision frame, and clickable source chunks
6. Click any source in the Sources section to read the full retrieved chunk in the right panel

Reports generated with the openai backend are cached to .report_cache/: repeat requests return instantly at no cost. Click **Regenerate** to bypass the cache.

---

## Run the eval harness

```bash
# Mock backend
python eval/run.py --backend mock --run-id mock_test

# OpenAI backend
python eval/run.py --backend openai --run-id v4_final
```

Results are written to `eval/results/<run-id>/`:
- `results.csv` — per-event scores
- `summary.txt` — aggregate metrics
- `evt_NNN_report.json` — full generated report per event

---

## Run tests

```bash
pytest backend/tests/ -v
```

---

## Project structure

```
shap-to-report/
├── backend/
│   ├── api/            # FastAPI app (app.py: /explain, /events, /health)
│   ├── backends/       # LLMBackend ABC, MockBackend, OpenAIBackend
│   ├── chroma_db/      # Pre-populated ChromaDB vector store
│   ├── rag/            # corpus.json, ingest.py, retriever.py
│   ├── schema/         # SituationalReport Pydantic model, strict schema util
│   ├── validator/      # OutputValidator
│   ├── cache.py        # Disk-based report cache
│   └── tests/          # pytest unit tests
├── eval/
│   ├── run.py          # Eval harness (--backend mock|openai)
│   ├── test_cases/     # 10 labeled SMAP anomaly events (JSON)
│   └── results/        # Eval run outputs
├── frontend/           # React + Vite + Tailwind UI
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       └── components/ # EventPicker, ReportPanel, ShapPanel, GlossaryPanel, ...
├── .env.example        # OPENAI_API_KEY= (only key needed)
├── requirements.txt    # Pinned Python dependencies
├── REPORT.md           # Iterations, code walkthrough, AI disclosure
└── README.md
```

---

## Example API call

```bash
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_001",
    "source_bodies": ["EU_AI_Act", "NASA_NPR", "NASA_Lessons_Learned"],
    "backend": "openai"
  }'
```