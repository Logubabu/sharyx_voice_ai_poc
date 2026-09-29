# Voice AI WebCall POC

Real-time Voice AI WebCall Proof of Concept using **Pipecat** (Python), **React + Vite + TypeScript**, and **WebRTC**.

## Objective

Build a simple, working, real-time browser voice conversation pipeline:
`Browser → WebRTC → Pipecat → STT → LLM → TTS → WebRTC → Browser`

---

## 1. Features

- 🎙 **Microphone Streaming**: Capture and stream user microphone audio over WebRTC.
- ⚡ **Real-Time Pipeline**: Streaming STT, LLM generation, and TTS audio synthesis.
- 🛑 **Interruption / Barge-in**: Basic interruption handling when user speaks over AI.
- 🔄 **Multi-Call Support**: Start and End calls repeatedly without browser refresh.
- 🎨 **Modern Minimal UI**: Glassmorphic dark design with live connection indicators.

---

## 2. Prerequisites

- **Python**: 3.11+
- **Node.js**: 20+
- **Browser**: Chrome, Edge, Safari, or Firefox with microphone access enabled.

---

## 3. Installation & Run

### Backend

```bash
cd backend
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run FastAPI server
python -m app.main
```
Backend runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```
Frontend runs on `http://localhost:5173`.

---

## 4. Docker Usage

```bash
docker-compose up --build
```

---

## 5. Architecture Documentation

Detailed architecture specifications can be found in [`docs/architecture.md`](docs/architecture.md).
